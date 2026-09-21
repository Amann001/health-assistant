"""
Tests for pose_engine.RepCounter's state machine and rep-quality gating.

These feed hand-crafted (primary_angle, secondary_angle, other_side_angle,
hip_y, torso_length) sequences straight into RepCounter.update() -- the
same synthetic-testing approach used, ad hoc, to catch every real bug found
in this file over the course of building it (see git log for pose_engine.py:
the threshold-ordering bug, the single-leg false positive, and the seated
torso-bow false positive were all caught this way before or after live
testing). This suite makes that verification permanent instead of a
scratch script that gets deleted after each fix.

No camera or MediaPipe inference is needed here -- these numbers are
exactly what analyze_frame would have computed from real landmarks and
handed to RepCounter.update(); testing at this level keeps the state
machine's logic decoupled from (and testable without) the ML pipeline.
"""

import pytest

from pose_engine import RepCounter


def feed(counter, frames):
    """Feed a list of (primary, secondary, other, hip_y, torso_length)
    tuples through RepCounter.update() in order, returning the last
    feedback string."""
    feedback = ""
    for primary, secondary, other, hip_y, torso_length in frames:
        feedback = counter.update("squat", primary, secondary, other, hip_y, torso_length)
    return feedback


# A real, symmetric, deep squat: both legs bend together, hips travel well
# past min_hip_drop_ratio, the knee reaches good_depth_max, and the back
# stays above good_back_min throughout. The "textbook rep" baseline reused
# across several tests below.
GOOD_SQUAT_FRAMES = [
    (170, 170, 170, 0.40, 0.25), (150, 160, 148, 0.44, 0.25), (120, 130, 118, 0.50, 0.25),
    (90, 80, 92, 0.56, 0.25), (120, 130, 118, 0.50, 0.25), (150, 160, 148, 0.44, 0.25),
    (170, 170, 170, 0.40, 0.25),
]


@pytest.fixture
def counter():
    return RepCounter()


class TestRealSquat:
    def test_counts_as_one_rep(self, counter):
        feed(counter, GOOD_SQUAT_FRAMES)
        assert counter.rep_count == 1

    def test_grades_as_good_form(self, counter):
        feed(counter, GOOD_SQUAT_FRAMES)
        assert counter.good_form_reps == 1

    def test_three_in_a_row_builds_streak(self, counter):
        for _ in range(3):
            feed(counter, GOOD_SQUAT_FRAMES)
        assert counter.good_form_streak == 3

    def test_streak_milestone_phrase_at_three(self, counter):
        for _ in range(2):
            feed(counter, GOOD_SQUAT_FRAMES)
        feedback = feed(counter, GOOD_SQUAT_FRAMES)
        assert "three in a row" in feedback.lower()


class TestFalsePositiveRejection:
    """Regression tests for the two real false-positive bugs a live user
    test caught -- a single-leg motion and a seated torso-bow both used to
    get miscounted as genuine squat reps. If either of these ever starts
    failing, one of the two gates in RepCounter.update() has regressed."""

    def test_single_leg_raise_not_counted(self, counter):
        # The tracked leg swings through the full squat angle range, but
        # the other leg (clearly visible, not occluded) stays essentially
        # straight throughout -- see EXERCISES["squat"]["bilateral_tolerance"].
        frames = [
            (170, 170, 178, 0.40, 0.25), (150, 160, 176, 0.40, 0.25), (120, 130, 175, 0.40, 0.25),
            (90, 80, 174, 0.40, 0.25), (120, 130, 175, 0.40, 0.25), (150, 160, 176, 0.40, 0.25),
            (170, 170, 178, 0.40, 0.25),
        ]
        feed(counter, frames)
        assert counter.rep_count == 0

    def test_seated_bow_not_counted(self, counter):
        # Knee angle numerically swings through the full range (simulating
        # noisy/hallucinated landmark drift while seated), but hip_y barely
        # moves, since the hips never actually descend toward the floor --
        # see EXERCISES["squat"]["min_hip_drop_ratio"].
        frames = [
            (170, 170, 170, 0.60, 0.20), (150, 160, 148, 0.605, 0.20), (120, 130, 118, 0.61, 0.20),
            (90, 80, 92, 0.615, 0.20), (120, 130, 118, 0.61, 0.20), (150, 160, 148, 0.605, 0.20),
            (170, 170, 170, 0.60, 0.20),
        ]
        feed(counter, frames)
        assert counter.rep_count == 0

    def test_real_squat_still_counts_when_other_leg_occluded(self, counter):
        # other_side_primary_angle is None throughout -- simulates a tight
        # side-profile view where the far leg's visibility was too low to
        # trust (see analyze_frame's _MIN_VISIBILITY_FOR_BILATERAL_CHECK).
        # Must fall back to single-leg counting rather than blocking a real
        # rep just because the far leg couldn't be verified.
        frames = [
            (170, 170, None, 0.40, 0.25), (150, 160, None, 0.44, 0.25), (120, 130, None, 0.50, 0.25),
            (90, 80, None, 0.56, 0.25), (120, 130, None, 0.50, 0.25), (150, 160, None, 0.44, 0.25),
            (170, 170, None, 0.40, 0.25),
        ]
        feed(counter, frames)
        assert counter.rep_count == 1


class TestFormGrading:
    def test_shallow_rep_counted_but_not_good_form(self, counter):
        # Knee only reaches 130 (never hits good_depth_max=100), but hip
        # still clearly travels -- exercises the depth check specifically,
        # not the hip-drop gate.
        frames = [
            (170, 170, 170, 0.40, 0.25), (135, 130, 128, 0.44, 0.25), (130, 130, 128, 0.55, 0.25),
            (135, 130, 128, 0.44, 0.25), (170, 170, 170, 0.40, 0.25),
        ]
        feedback = feed(counter, frames)
        assert counter.rep_count == 1
        assert counter.good_form_reps == 0
        assert "lower" in feedback.lower()

    def test_bad_back_counted_but_not_good_form(self, counter):
        # Deep enough at the knee (reaches 90), but the back angle
        # (secondary) drops to 40 at the deepest point -- below
        # good_back_min=55, i.e. leaning too far forward.
        frames = [
            (170, 170, 170, 0.40, 0.25), (150, 100, 148, 0.44, 0.25), (120, 60, 118, 0.50, 0.25),
            (90, 40, 92, 0.56, 0.25), (120, 60, 118, 0.50, 0.25), (150, 100, 148, 0.44, 0.25),
            (170, 170, 170, 0.40, 0.25),
        ]
        feedback = feed(counter, frames)
        assert counter.rep_count == 1
        assert counter.good_form_reps == 0
        assert "back" in feedback.lower()

    def test_shallow_rep_resets_streak(self, counter):
        feed(counter, GOOD_SQUAT_FRAMES)
        feed(counter, GOOD_SQUAT_FRAMES)
        assert counter.good_form_streak == 2

        shallow_frames = [
            (170, 170, 170, 0.40, 0.25), (135, 130, 128, 0.44, 0.25), (130, 130, 128, 0.55, 0.25),
            (135, 130, 128, 0.44, 0.25), (170, 170, 170, 0.40, 0.25),
        ]
        feed(counter, shallow_frames)
        assert counter.good_form_streak == 0


class TestReset:
    def test_reset_clears_all_counters(self, counter):
        feed(counter, GOOD_SQUAT_FRAMES)
        counter.reset()
        assert counter.rep_count == 0
        assert counter.good_form_reps == 0
        assert counter.good_form_streak == 0
        assert counter.stage == "up"
