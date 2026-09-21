"""End-to-end tests for the FastAPI endpoints, exercising the real request/
response cycle (routing, Pydantic validation, upload limits) rather than
calling pose_engine functions directly. Runs in-process via TestClient --
no server needs to be running."""

import cv2
import numpy as np
from fastapi.testclient import TestClient

from main import MAX_UPLOAD_BYTES, app

client = TestClient(app)


def make_jpeg_bytes(width=320, height=240):
    """A real, decodable JPEG with nothing recognizable in it -- enough to
    exercise the "no person detected" path without needing an actual photo
    of a person."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", frame)
    assert ok
    return encoded.tobytes()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


class TestFormStart:
    def test_returns_coaching_intro_generated_from_real_thresholds(self):
        resp = client.post("/api/form/start", data={"exercise": "squat"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["exercise"] == "squat"
        assert body["status"] == "reset"
        assert "squat" in body["coaching_intro"].lower()

    def test_unknown_exercise_falls_back_to_squat(self):
        resp = client.post("/api/form/start", data={"exercise": "lunge"})
        assert resp.status_code == 200
        assert resp.json()["exercise"] == "squat"


class TestFormAnalyze:
    def test_blank_frame_reports_no_person_detected(self):
        client.post("/api/form/start", data={"exercise": "squat"})
        resp = client.post(
            "/api/form/analyze",
            data={"exercise": "squat"},
            files={"frame": ("frame.jpg", make_jpeg_bytes(), "image/jpeg")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["landmarks"] is None
        assert body["rep_count"] == 0
        assert "no person" in body["feedback"].lower()

    def test_garbage_bytes_reports_decode_failure_not_a_crash(self):
        resp = client.post(
            "/api/form/analyze",
            data={"exercise": "squat"},
            files={"frame": ("frame.jpg", b"not a real jpeg", "image/jpeg")},
        )
        assert resp.status_code == 200
        assert "decode" in resp.json()["feedback"].lower()

    def test_oversized_upload_is_rejected(self):
        oversized = b"0" * (MAX_UPLOAD_BYTES + 1)
        resp = client.post(
            "/api/form/analyze",
            data={"exercise": "squat"},
            files={"frame": ("frame.jpg", oversized, "image/jpeg")},
        )
        assert resp.status_code == 413
