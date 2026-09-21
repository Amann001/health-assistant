"""
Personal Health Assistant — Backend

Form-correction (Phase 3) is wired up to real pose analysis in
pose_engine.py. Nutrition (Phase 4) still returns a hardcoded stub —
that's next.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pose_engine

app = FastAPI(title="Personal Health Assistant API")

# A single webcam-frame JPEG is normally well under 1MB. This caps uploads
# generously above that so a misbehaving client (or, later, anyone hitting
# an exposed tunnel URL) can't hand us an arbitrarily large body and eat
# memory decoding it.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8MB


async def _read_limited(upload: UploadFile) -> bytes:
    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file is too large.")
    return data

# Single-user, single-session app: one RepCounter per exercise, kept in
# memory for the lifetime of the backend process. /api/form/start resets
# the relevant counter when a new session begins.
_rep_counters: dict[str, pose_engine.RepCounter] = {
    name: pose_engine.RepCounter() for name in pose_engine.EXERCISES
}

# Lets the React dev server (running on a different port) call this API.
# 5173 is Vite's default dev server port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Hit this from the browser to confirm the backend is alive:
    http://localhost:8000/health
    """
    return {"status": "ok"}


class Landmark(BaseModel):
    x: float
    y: float
    visibility: float


class FormAnalysisResponse(BaseModel):
    exercise: str
    rep_count: int
    good_form_reps: int
    feedback: str
    # None when no person is detected in the frame at all; present (but
    # possibly showing a shaky/incomplete pose) whenever MediaPipe found
    # someone, even if pose_engine decided not to trust it for rep-counting.
    landmarks: list[Landmark] | None = None


class FormStartResponse(BaseModel):
    exercise: str
    status: str


@app.post("/api/form/start", response_model=FormStartResponse)
def start_form_session(exercise: str = Form("squat")):
    """Resets the rep counter for `exercise`. Call this once when a workout
    session begins, before the frontend starts streaming frames."""
    if exercise not in _rep_counters:
        exercise = "squat"
    _rep_counters[exercise].reset()
    return FormStartResponse(exercise=exercise, status="reset")


@app.post("/api/form/analyze", response_model=FormAnalysisResponse)
async def analyze_form(frame: UploadFile = File(...), exercise: str = Form("squat")):
    """
    Receives one webcam frame (as a JPEG) from the Workout page and runs
    real pose analysis: MediaPipe landmarks -> joint angles -> rep-counting
    state machine (see pose_engine.py for the actual logic).
    """
    if exercise not in _rep_counters:
        exercise = "squat"

    image_bytes = await _read_limited(frame)
    result = pose_engine.analyze_frame(image_bytes, exercise, _rep_counters[exercise])

    return FormAnalysisResponse(**result)


class NutritionAnalysisResponse(BaseModel):
    food_name: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


@app.post("/api/nutrition/analyze", response_model=NutritionAnalysisResponse)
async def analyze_food(image: UploadFile = File(...)):
    """
    Receives one meal photo from the Nutrition page.

    TODO (Phase 4):
      1. Decode the image.
      2. Run a food-classification model to identify the dish.
      3. Look up macros for that food (e.g. via USDA FoodData Central API).
      4. Return the real calorie/macro numbers instead of the stub below.
    """
    _ = await _read_limited(image)  # image bytes are available here once you need them

    return NutritionAnalysisResponse(
        food_name="unknown",
        calories=0,
        protein_g=0,
        carbs_g=0,
        fat_g=0,
    )
