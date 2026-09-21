"""Tests for pose_engine's geometry and config-derived helper functions --
the pieces RepCounter's state machine relies on but doesn't itself test."""

import pytest

from pose_engine import EXERCISES, _angle, _depth_progress, _pick_visible_side, exercise_intro


class FakeLandmark:
    """Stand-in for MediaPipe's landmark object -- just needs .x/.y/.visibility,
    which is all these helpers read."""

    def __init__(self, x, y, visibility=1.0):
        self.x = x
        self.y = y
        self.visibility = visibility


def make_landmarks(overrides):
    """33 default landmarks (MediaPipe's fixed pose model size) at a
    neutral point with full visibility, with specific indices overridden --
    e.g. make_landmarks({23: FakeLandmark(0.4, 0.5, 0.9)})."""
    landmarks = [FakeLandmark(0.5, 0.5, 1.0) for _ in range(33)]
    for idx, lm in overrides.items():
        landmarks[idx] = lm
    return landmarks


class TestAngle:
    def test_right_angle(self):
        # b at the origin, a straight up, c straight right -> 90 degrees.
        assert _angle((0, -1), (0, 0), (1, 0)) == pytest.approx(90, abs=0.01)

    def test_straight_line(self):
        # a and c on opposite sides of b along the same line -> 180 degrees
        # (a fully straightened joint).
        assert _angle((-1, 0), (0, 0), (1, 0)) == pytest.approx(180, abs=0.01)

    def test_zero_angle(self):
        # a and c on the same side of b -> 0 degrees (a fully folded joint).
        assert _angle((1, 0), (0, 0), (1, 0)) == pytest.approx(0, abs=0.01)


class TestDepthProgress:
    cfg = EXERCISES["squat"]

    def test_zero_at_standing(self):
        assert _depth_progress(self.cfg["up_threshold"], self.cfg) == 0.0

    def test_one_at_good_depth(self):
        assert _depth_progress(self.cfg["good_depth_max"], self.cfg) == 1.0

    def test_clamped_beyond_good_depth(self):
        # Deeper than good_depth_max should still read as 1.0, not overshoot.
        assert _depth_progress(50, self.cfg) == 1.0

    def test_clamped_above_standing(self):
        # A knee angle above up_threshold (e.g. hyperextension noise)
        # should still read as 0.0, not go negative.
        assert _depth_progress(180, self.cfg) == 0.0

    def test_roughly_halfway(self):
        mid = (self.cfg["up_threshold"] + self.cfg["good_depth_max"]) / 2
        assert _depth_progress(mid, self.cfg) == pytest.approx(0.5, abs=0.01)


class TestPickVisibleSide:
    def test_picks_more_visible_side(self):
        landmarks = make_landmarks({
            23: FakeLandmark(0.4, 0.5, 0.9), 24: FakeLandmark(0.6, 0.5, 0.2),  # hips
            25: FakeLandmark(0.4, 0.7, 0.9), 26: FakeLandmark(0.6, 0.7, 0.2),  # knees
            27: FakeLandmark(0.4, 0.9, 0.9), 28: FakeLandmark(0.6, 0.9, 0.2),  # ankles
        })
        assert _pick_visible_side(landmarks) == "left"

    def test_ties_default_to_left(self):
        landmarks = make_landmarks({})  # both sides at the default 1.0 visibility
        assert _pick_visible_side(landmarks) == "left"


class TestExerciseIntro:
    def test_mentions_the_real_depth_threshold(self):
        # Generated FROM the config, not a separately hand-written string --
        # this is what actually guarantees the two can't drift apart.
        intro = exercise_intro("squat")
        assert str(EXERCISES["squat"]["good_depth_max"]) in intro

    def test_unknown_exercise_degrades_gracefully(self):
        # No EXERCISES entry exists for "lunge" yet -- must fall back to a
        # generic line instead of raising KeyError (regression test: this
        # used to crash because EXERCISES[exercise] was indexed before the
        # "is it squat" check).
        intro = exercise_intro("lunge")
        assert "lunge" in intro.lower()
