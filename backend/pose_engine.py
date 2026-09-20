"""
Pose estimation and exercise-form analysis.

MediaPipe's PoseLandmarker model is loaded once, at import time, and reused
for every request — creating it fresh per request would reload the model
file from disk on every single webcam frame, which is far too slow for
anything close to real-time.

Landmark indices below follow MediaPipe's fixed 33-point body model:
https://ai.google.dev/mediapipe/solutions/vision/pose_landmarker#pose_landmarker_model
"""

import math
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

_MODEL_PATH = Path(__file__).parent / "models" / "pose_landmarker_lite.task"

_landmarker = PoseLandmarker.create_from_options(
    PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(_MODEL_PATH)),
        running_mode=RunningMode.IMAGE,
        num_poses=1,
    )
)

# (left_index, right_index) for each joint we use. MediaPipe always returns
# landmarks for both sides of the body, even the side turned away from the
# camera — but its confidence for the occluded side is low and unreliable.
JOINT_LANDMARKS = {
    "shoulder": (11, 12),
    "hip": (23, 24),
    "knee": (25, 26),
    "ankle": (27, 28),
}


def _angle(a, b, c) -> float:
    """Angle at vertex b formed by rays b->a and b->c, in degrees (0-180).

    Uses the dot-product formula cos(theta) = (BA . BC) / (|BA| |BC|).
    Only x/y are used (z from MediaPipe is a rough depth estimate, noisy
    enough from a single webcam that it does more harm than good here).
    """
    a, b, c = np.array(a[:2]), np.array(b[:2]), np.array(c[:2])
    ba = a - b
    bc = c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-9)
    return math.degrees(math.acos(np.clip(cosine, -1.0, 1.0)))


def _pick_visible_side(landmarks) -> str:
    """Decide whether to read angles from the left or right side of the body.

    A webcam usually only gets a clean side-on or 3/4 view, so one side of
    the body is often partially hidden from the camera. MediaPipe still
    reports a guessed position for the hidden side, but flags it with low
    `visibility`. Comparing average visibility across hip/knee/ankle picks
    whichever side the camera can actually see well.
    """
    left_visibility = sum(
        landmarks[JOINT_LANDMARKS[joint][0]].visibility for joint in ("hip", "knee", "ankle")
    )
    right_visibility = sum(
        landmarks[JOINT_LANDMARKS[joint][1]].visibility for joint in ("hip", "knee", "ankle")
    )
    return "left" if left_visibility >= right_visibility else "right"


def _joint_point(landmarks, joint: str, side: str):
    idx = JOINT_LANDMARKS[joint][0 if side == "left" else 1]
    lm = landmarks[idx]
    return (lm.x, lm.y)


def _joint_visibility(landmarks, joint: str, side: str) -> float:
    idx = JOINT_LANDMARKS[joint][0 if side == "left" else 1]
    return landmarks[idx].visibility


def _side_angle(landmarks, joints, side: str) -> float:
    points = [_joint_point(landmarks, j, side) for j in joints]
    return _angle(*points)


# Below this visibility, we don't trust that side's landmarks enough to use
# them for the bilateral (both-legs-moving) check — a tight side-profile
# view can genuinely hide the far leg, and we'd rather fall back to
# single-leg counting than let occlusion noise block real reps.
_MIN_VISIBILITY_FOR_BILATERAL_CHECK = 0.5


# --- Exercise configuration -------------------------------------------
# Each exercise names the three joints that define its primary angle (the
# one the up/down rep state machine watches) and, optionally, a secondary
# angle used only to grade the *quality* of a completed rep. Adding a new
# exercise means adding an entry here — nothing else in this file changes.
#
# Thresholds below are reasonable starting points, not measured values —
# they need live tuning against your own body/camera angle once you can
# actually test with the webcam (see CLAUDE.md: "angle thresholds can be
# finicky").
EXERCISES = {
    "squat": {
        "primary_joints": ("hip", "knee", "ankle"),       # knee angle: depth
        "secondary_joints": ("shoulder", "hip", "knee"),  # hip angle: back posture
        # These three must stay in this order (up > down > good_depth_max) or
        # the depth check becomes unreachable: any motion big enough to be
        # recognized as a squat attempt would already count as "deep enough".
        "up_threshold": 160,      # knee angle above this = standing up straight -> rep complete
        "down_threshold": 140,    # knee angle below this = started descending -> now tracking a rep attempt
        "good_depth_max": 100,    # rep's lowest knee angle must reach <= this to count as deep enough
        "good_back_min": 55,      # hip angle at the deepest point must stay >= this (not leaning too far forward)
        # A real squat bends BOTH knees together. A single-leg motion (a
        # knee raise, a high-knee march, a kick) bends only the tracked
        # side's knee through this same angle range and would otherwise be
        # indistinguishable from a squat rep. This is how far the *other*
        # leg is allowed to lag behind down_threshold and still count as
        # "also bending" — generous enough for real asymmetry/lag between
        # legs, but nowhere near a leg that's staying straight.
        "bilateral_tolerance": 15,
    },
}


@dataclass
class RepCounter:
    """Tracks rep count and form quality for one exercise across a session.

    One instance is kept alive server-side for as long as a workout session
    is running, and fed one frame's angles at a time via `update()`.
    """

    stage: str = "up"
    rep_count: int = 0
    good_form_reps: int = 0
    _min_primary_this_rep: float = 180.0
    _secondary_at_min: float = 180.0

    def reset(self):
        self.stage = "up"
        self.rep_count = 0
        self.good_form_reps = 0
        self._min_primary_this_rep = 180.0
        self._secondary_at_min = 180.0

    def update(
        self,
        exercise: str,
        primary_angle: float,
        secondary_angle: float,
        other_side_primary_angle: float | None = None,
    ) -> str:
        """Feed in this frame's angles, return a short feedback string.

        State machine: "up" -> "down" happens as soon as the primary angle
        drops past down_threshold (started descending). While "down", we
        keep the *lowest* primary angle and the secondary angle measured at
        that lowest point, because that's the deepest part of the rep — the
        moment that actually determines whether the rep was deep enough and
        whether the back stayed upright. "down" -> "up" (a completed rep)
        happens once the primary angle rises back past up_threshold; only
        then do we grade the rep using the deepest-point values we tracked.

        `other_side_primary_angle` is the same angle measured on the *other*
        leg, when the camera can see it well enough to trust (None if not —
        see analyze_frame). Entering "down" requires that leg to also be
        bending, which is what stops a single-leg motion from being read as
        a squat rep (see EXERCISES["squat"]["bilateral_tolerance"]).
        """
        cfg = EXERCISES[exercise]
        feedback = ""

        other_leg_also_bending = (
            other_side_primary_angle is None
            or other_side_primary_angle < cfg["down_threshold"] + cfg.get("bilateral_tolerance", 0)
        )

        if self.stage == "up" and primary_angle < cfg["down_threshold"] and other_leg_also_bending:
            self.stage = "down"
            self._min_primary_this_rep = primary_angle
            self._secondary_at_min = secondary_angle

        elif self.stage == "down":
            if primary_angle < self._min_primary_this_rep:
                self._min_primary_this_rep = primary_angle
                self._secondary_at_min = secondary_angle

            if primary_angle > cfg["up_threshold"]:
                self.stage = "up"
                self.rep_count += 1
                deep_enough = self._min_primary_this_rep <= cfg["good_depth_max"]
                back_ok = self._secondary_at_min >= cfg["good_back_min"]

                if deep_enough and back_ok:
                    self.good_form_reps += 1
                    feedback = f"Good rep! ({self.rep_count} total)"
                elif not deep_enough:
                    feedback = f"Rep {self.rep_count} counted — go a bit lower next time."
                else:
                    feedback = f"Rep {self.rep_count} counted — keep your back straighter."

        if not feedback:
            feedback = "Good — going down, keep it controlled" if self.stage == "down" else "Ready — squat down"

        return feedback


def analyze_frame(image_bytes: bytes, exercise: str, counter: RepCounter) -> dict:
    """Run pose estimation + form analysis on one JPEG frame.

    Returns a dict matching FormAnalysisResponse's fields.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame_bgr is None:
        return {
            "exercise": exercise,
            "rep_count": counter.rep_count,
            "good_form_reps": counter.good_form_reps,
            "feedback": "Could not decode frame.",
        }

    # MediaPipe expects RGB; OpenCV decodes to BGR by default.
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

    result = _landmarker.detect(mp_image)
    if not result.pose_landmarks:
        return {
            "exercise": exercise,
            "rep_count": counter.rep_count,
            "good_form_reps": counter.good_form_reps,
            "feedback": "No person detected — step into frame.",
        }

    landmarks = result.pose_landmarks[0]  # first (only) detected person
    side = _pick_visible_side(landmarks)
    other_side = "right" if side == "left" else "left"

    cfg = EXERCISES[exercise]
    primary_angle = _side_angle(landmarks, cfg["primary_joints"], side)
    secondary_angle = _side_angle(landmarks, cfg["secondary_joints"], side)

    other_leg_visible = (
        _joint_visibility(landmarks, "knee", other_side) >= _MIN_VISIBILITY_FOR_BILATERAL_CHECK
    )
    other_side_primary_angle = (
        _side_angle(landmarks, cfg["primary_joints"], other_side) if other_leg_visible else None
    )

    feedback = counter.update(exercise, primary_angle, secondary_angle, other_side_primary_angle)

    return {
        "exercise": exercise,
        "rep_count": counter.rep_count,
        "good_form_reps": counter.good_form_reps,
        "feedback": feedback,
    }
