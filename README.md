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

## Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Visit the URL Vite prints (usually http://localhost:5173). Allow camera access when prompted.

## Try it

1. Open the Workout page, allow the camera, click **Start Session**.
2. Do a few squats in view of the camera — rep count and feedback update live,
   roughly every 300ms. Click **Stop Session** to end and see a short summary.
3. The Nutrition page is still Phase 4 territory — "Scan Meal" just proves the
   camera/backend plumbing for now.

## Status / next steps

See the "Build roadmap" section of [CLAUDE.md](CLAUDE.md). Currently mid-Phase 3:
squat detection (angle math + rep-counting state machine) is implemented and
unit-verified, skeleton overlay and TTS cues are next, then push-up/curl.
