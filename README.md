# Personal Health Assistant

A personal-use web app combining two AI-powered modules behind one dashboard:

1. **Form-Correction Coach** — webcam-based rep counting and live form feedback
   for squat, push-up, and bicep curl (squat first).
2. **Nutrition Scanner** — photograph a meal, get identified food + calories/macros.

Full project brief, roadmap, and design decisions live in [CLAUDE.md](CLAUDE.md).

## What's here (Phase 3 in progress)

```
health-assistant/
  backend/
    main.py            FastAPI app: /health, /api/form/*, /api/nutrition/analyze
    pose_engine.py      MediaPipe pose estimation + squat angle/rep-counting logic
    models/            MediaPipe .task model file (downloaded, not checked in — see below)
    tests/             pytest suite — see "Run the tests" below
    requirements.txt
  frontend/
    src/
      pages/
        Workout.jsx     Webcam feed + Start/Stop session, live rep count + feedback
        Nutrition.jsx   Webcam feed + "Scan Meal" button (still a stub — Phase 4)
      components/
        WebcamFeed.jsx  Shared getUserMedia webcam component
        NavBar.jsx
      api.js            Shared axios helpers for the form endpoints
      speech.js          Web Speech API (TTS) wrapper — spoken coaching cues
      listen.js           Web Speech API (STT) wrapper — push-to-talk voice input
      voiceCommands.js    Matches transcribed speech to in-session commands
      skeleton.js         Draws the pose skeleton over the video feed
      App.jsx            React Router wiring
      main.jsx
      index.css
    package.json
    vite.config.js
    index.html
```

## Prerequisites

- Python 3.10+ (tested on 3.13)
- Node.js 18+

## Run the backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # on Windows (bash); on cmd/PowerShell: .venv\Scripts\activate
pip install -r requirements.txt
mkdir -p models
curl -L -o models/pose_landmarker_lite.task "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
uvicorn main:app --reload --port 8000
```

Visit http://localhost:8000/health — you should see `{"status": "ok"}`.

## Run the tests

```bash
cd backend
source .venv/Scripts/activate
pytest -v
```

Covers the rep-counting state machine (including regression tests for the
two false-positive bugs live testing caught), the angle/depth-progress
math, and the API endpoints — all without needing a camera, since it feeds
the same kind of angle data `analyze_frame` would have computed straight
into the functions under test.

## Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Visit the URL Vite prints (usually http://localhost:5173). Allow camera access when prompted.

## Try it

1. Open the Workout page, allow the camera, click **Start Session** — the
   coach explains what counts as good form for this exercise first
   (generated from the real angle thresholds, spoken + shown on screen).
2. Do a few squats in view of the camera — rep count and feedback update live,
   roughly every 300ms, with a skeleton drawn over your body, a live depth
   gauge filling as you descend, and each new cue spoken aloud. String
   together good-form reps for a streak badge (🔥 at 5+, at 10+ it goes
   legendary).
3. Tap **Tap to Talk** and ask the coach a question — "how many reps have
   I done," "how's my form," "what's my streak," or say "stop" to end the
   session by voice; it stops listening on its own once you stop talking.
   It only answers from the current session (no history yet — see below).
4. Click **Stop Session** to end and see a short summary.
5. The Nutrition page is still Phase 4 territory — "Scan Meal" just proves the
   camera/backend plumbing for now.

## Status / next steps

See the "Build roadmap" section of [CLAUDE.md](CLAUDE.md). Currently mid-Phase 3:

- Done: continuous frame capture, squat angle/rep-counting logic, a skeleton
  overlay, spoken (TTS) coaching cues, a live depth gauge, good-form streak
  tracking, a config-driven pre-session exercise intro, and a tap-to-talk
  voice command layer (STT) that answers simple questions from the live
  session state.
- Two real false-positive bugs were found and fixed through live testing —
  a single-leg motion being mistaken for a squat rep, and a seated
  torso-bow being mistaken for one — see the git history in `pose_engine.py`
  for what each fix actually checks and why.
- A permanent `pytest` suite (`backend/tests/`) now covers the rep-counter
  state machine, both false-positive regressions above, the angle/depth
  math, and the API endpoints — 29 tests, all passing.
- **Not yet done: a full live squat-verification pass** — the fixes above
  are test-verified but not yet confirmed against a real body/camera.
  The angle thresholds in `EXERCISES["squat"]` are starting guesses and will
  likely need retuning once that happens.
- The voice command layer only answers from the *current* session (rep
  count, form, streak) — CLAUDE.md's full Module 4 vision (grounded
  Q&A over *logged history*, e.g. "how was my form this week") needs the
  SQLite database from Phase 5, which hasn't been built yet.
- After live verification: push-up and bicep curl (same `pose_engine.py`
  pattern), then Phase 4 (nutrition scanner).
