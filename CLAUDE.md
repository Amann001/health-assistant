# Personal Health Assistant — Project Brief

## What this project is

A personal-use web app that combines two things into one assistant:

1. **AI Form-Correction Coach** — watches you exercise through a webcam,
   counts reps, and gives real-time feedback (on-screen and spoken) on your
   form.
2. **AI Nutrition Scanner** — you photograph a meal, it identifies the food
   and estimates calories/macros, and you can query your daily totals by
   voice.

Both modules share one dashboard, one user profile, and (eventually) one
voice interface — the goal is that it feels like a single coherent
assistant, not two separate tools bolted together. Think "a home gym
trainer + nutritionist that lives in your browser."

This is a solo BTech CSE student's major project. Priorities, in order:
**1) it actually works end-to-end, 2) it's genuinely impressive in a live
demo, 3) the student understands every part of the code, not just that it
runs.** Favor explaining what you're doing over silently doing it —
this person wants to learn from this build, not just receive it.

## Current state — start here, don't rebuild it

A working skeleton already exists in this repo:

```
health-assistant/
  backend/
    main.py            FastAPI app, CORS configured for the Vite dev server
    requirements.txt
  frontend/
    src/
      pages/
        Workout.jsx     Webcam feed + "Analyze Frame" button, posts to backend
        Nutrition.jsx   Webcam feed + "Scan Meal" button, posts to backend
      components/
        WebcamFeed.jsx  Shared getUserMedia webcam component
        NavBar.jsx
      App.jsx           React Router wiring the two pages
      main.jsx
      index.css
    package.json
    vite.config.js
    index.html
  README.md
```

The backend has two endpoints already stubbed out:
- `POST /api/form/analyze` — receives a JPEG frame, currently returns a
  hardcoded stub response. Real pose-analysis logic goes here.
- `POST /api/nutrition/analyze` — receives a JPEG meal photo, currently
  returns a hardcoded stub response. Real food-classification logic goes
  here.
- `GET /health` — confirms the backend is running.

Both `analyze_form` and `analyze_food` in `backend/main.py` have `TODO`
comments describing one valid path for real logic — read those first. For
`analyze_food`, that path holds: the frontend's single-click capture and
`multipart/form-data` POST is exactly right for a one-shot meal photo, and
you shouldn't need to touch that plumbing. For `analyze_form`, treat the
TODO comment as a starting sketch, not a final spec — it assumes
server-side pose estimation and one frame per request, and "Known
technical gotchas" below explains why both of those need a decision before
you build on top of them.

Verify the skeleton runs (`backend`: `uvicorn main:app --reload --port
8000`; `frontend`: `npm install && npm run dev`) before building on top of
it, so you know your starting point is solid.

## Full feature set

### Module 1: AI Form-Correction Coach
- Real-time webcam pose tracking during a workout session
- Exercise selection: start with squat, push-up, bicep curl (structure the
  code so adding a new exercise means adding a new angle-rule config, not
  rewriting the pipeline)
- Per-exercise joint-angle rules to judge correctness (e.g. knee angle and
  hip angle for squat depth, elbow angle for curls, back-angle for
  push-ups)
- Rep counting via a state machine (e.g. "up" → "down" → "up" = 1 rep)
- Live on-screen feedback: skeleton overlay on the video feed + text
  feedback
- Spoken coaching cues via text-to-speech ("straighten your back", "go
  lower", "good rep")
- End-of-session summary: total reps, good-form vs bad-form rep count,
  session duration
- Persisted workout history (so trends are possible later)
- *Stretch:* fatigue detection — flag when form quality drops over the
  course of a set, which usually signals fatigue

### Module 2: AI Nutrition Scanner
- Meal photo capture from webcam or phone browser camera
- Food identification via an image classification model
- Portion-size handling — simple heuristic or a quick user confirmation
  step ("is this a small/medium/large portion?") is fine for the MVP;
  don't over-engineer computer-vision portion estimation
- Calorie/macro lookup via a nutrition database (USDA FoodData Central API
  is free and has no auth beyond an API key)
- Daily/weekly nutrient totals
- Meal history log, with manual override if the model misidentifies the
  food
- Goal-based tracking: user sets daily calorie/protein/carb/fat targets,
  dashboard shows actual vs. target

### Module 3: Unified Dashboard & Profile
- One home dashboard: today's workout summary + today's nutrition summary,
  side by side
- User profile: fitness goal (bulk/cut/maintain), target macros, weekly
  workout plan
- Trend charts over time: workout volume, form-quality trend, macro trend
- Optional cross-metric insight (e.g. surfacing "protein intake was low on
  a leg day")

### Module 4: Voice Layer
- Push-to-talk (simpler, build this first) or wake-word activation
  (stretch)
- Speech-to-text for voice queries
- Natural-language Q&A grounded in the user's own logged data — e.g. "how
  much protein have I had today," "how was my squat form this week"
- Text-to-speech for spoken responses
- *Stretch:* proactive check-ins ("you trained legs hard yesterday, how's
  the soreness?")

### Supporting infrastructure
- REST API connecting the frontend and backend (already scaffolded — see
  "API contract" below for the full endpoint list as it grows)
- A local database persisting workouts, meals, profile, and goals (SQLite)
- Camera access working reliably on the laptop (both modules must work
  here — this is the fallback that guarantees the demo works no matter
  what). Phone-browser camera access for the Nutrition module is the
  intended design (see the original idea: "point your phone at a meal")
  but has a real technical blocker described in "Known technical
  gotchas" below — confirm with the user how much effort to spend on it
  (see "Questions to ask")
- The only network calls leaving the machine are the USDA FoodData
  Central lookup and, if using the default Web Speech API, Chrome's
  cloud speech-recognition service (see "Known technical gotchas") —
  pose estimation and food classification both run locally either way

## Recommended tech stack

These are strong defaults, not commandments — see "Questions to ask before
big decisions" below for the calls you should confirm with the user rather
than assume.

- **Backend:** Python + FastAPI (already scaffolded)
- **Pose estimation:** MediaPipe — runs locally either way, no API cost.
  Whether it runs server-side (Python, in the existing FastAPI backend) or
  client-side (JavaScript, via `@mediapipe/tasks-vision`) is an open call
  with real trade-offs — see "Known technical gotchas" and "Questions to
  ask" before committing. The skeleton's current `analyze_form` stub
  assumes server-side, but that isn't locked in.
- **Food recognition:** a pretrained food-classification model (e.g. a
  Food-101-based model from Hugging Face) run locally to start; only reach
  for a paid external API if local accuracy turns out to be too poor to
  demo. This one is fine to keep server-side regardless — a single photo
  per meal has no real-time latency requirement.
- **Nutrition data:** USDA FoodData Central API (free, requires a free API
  key)
- **Database:** SQLite for the whole build — this is a single-user app, no
  need for Postgres/hosted DB overhead
- **Frontend:** React + Vite (already scaffolded), React Router, Axios
- **Voice:** Web Speech API (STT + TTS) to start — free, no extra backend
  work, and TTS is genuinely local. But its STT half relies on Chrome's
  cloud speech service and has poor cross-browser support (see "Known
  technical gotchas") — develop and demo in Chrome, and move to Whisper +
  a dedicated TTS engine only if that becomes a real limitation. Wake-word
  activation (if pursued) needs a separate library (Porcupine), not
  something Web Speech API provides.
- **Deployment:** local only (localhost) for now, on the laptop. Phone
  access to the Nutrition module needs an HTTPS tunnel (`ngrok`) or local
  HTTPS setup — see "Known technical gotchas" — this is not automatic.

## Known technical gotchas

These are real constraints, not hypothetical edge cases — read this before
starting Phase 3.

- **Phone camera requires HTTPS.** Mobile browsers (and modern desktop
  browsers) block `getUserMedia` (camera access) on any origin that isn't
  `localhost` or served over HTTPS. A phone on the same WiFi network
  hitting your laptop's LAN IP over plain HTTP will have its camera
  request silently blocked. To actually demo the Nutrition scanner from a
  phone, you need either a tunnel tool (`ngrok`, `localtunnel`) or a local
  HTTPS setup (`mkcert`). Until that's set up, verify the Nutrition module
  works from the laptop's own browser too — don't assume phone access
  "just works" the way `localhost:5173` does on the laptop.
- **CORS is currently hardcoded to one origin.** `backend/main.py`'s
  `CORSMiddleware` only allows `http://localhost:5173`. If the frontend is
  ever reached from a different host/port (e.g. a phone hitting a LAN IP,
  or a tunnel URL), the backend will reject its requests until that origin
  is added. This is a common silent-failure point — if requests from a
  phone mysteriously don't reach the backend, check CORS first.
- **The current skeleton is not real-time yet, by design.** `Workout.jsx`
  currently sends exactly one frame per manual "Analyze Frame" click. That
  was intentional for Phase 2 (prove the plumbing works), but real-time
  rep counting needs continuous capture — the frontend has to grab and
  send frames on an interval (e.g. every 200–300ms) automatically while a
  session is "active," not wait for a click. This is a required change in
  Phase 3, not an optional polish item — see the updated roadmap below.
- **Where pose estimation runs is an open architecture choice, not a
  foregone conclusion.** MediaPipe ships both as a Python library (usable
  server-side, in the existing FastAPI backend) and as a JavaScript
  library (`@mediapipe/tasks-vision`, usable client-side in the browser).
  Server-side keeps all the ML logic in Python, which may be easier for
  the student to reason about, and is genuinely fine for a demo since
  everything runs on one laptop (localhost round-trips are ~1–5ms, not a
  real bottleneck). Client-side avoids the round-trip entirely and can
  make the skeleton overlay feel snappier, at the cost of writing the
  angle/rep-counting logic in JavaScript instead of Python. Either is a
  reasonable choice — see "Questions to ask."
- **Web Speech API isn't fully "local."** Its speech-recognition (STT)
  half depends on Chrome's own cloud speech service under the hood, and
  has weak or missing support in Safari and Firefox. Its speech-synthesis
  (TTS) half is genuinely local and broadly supported. Practically: build
  and demo in Chrome, and treat the STT dependency as a real (if minor)
  network dependency, not an offline feature.
- **Wake-word detection needs a separate tool.** Web Speech API has no
  wake-word ("Hey [name]") capability on its own — that's push-to-talk or
  nothing. If wake-word activation (the Module 4 stretch goal) is worth
  pursuing, it needs a dedicated library such as Porcupine, which requires
  a free Picovoice account and access key. Don't assume it falls out of
  the Web Speech API setup for free.
- **This is a single-user app — don't build multi-user auth.** The `User`
  row in the data model below is a stand-in for "the one profile," not the
  start of a login system. No authentication/signup flow is needed.

## Rough data model

Sketch — refine field names/types as you implement:

- `User`: id, name, goal (bulk/cut/maintain), daily_calorie_target,
  daily_protein_target, daily_carb_target, daily_fat_target
- `Exercise`: id, name, angle_rules (JSON: which joints/angles define good
  form for this exercise)
- `WorkoutSession`: id, user_id, exercise_id, started_at, ended_at,
  total_reps, good_form_reps
- `Rep`: id, session_id, timestamp, was_good_form (bool), notes
- `FoodEntry`: id, user_id, timestamp, food_name, calories, protein_g,
  carbs_g, fat_g, photo_path (optional)

## API contract

Existing (already implemented as stubs):
- `GET /health`
- `POST /api/form/analyze` — multipart `frame` (JPEG) → `{exercise,
  rep_count, feedback}`
- `POST /api/nutrition/analyze` — multipart `image` (JPEG) → `{food_name,
  calories, protein_g, carbs_g, fat_g}`

To be added as you build:
- `GET/POST /api/workouts` — list/create workout sessions
- `GET/POST /api/meals` — list/create food entries
- `GET/POST /api/profile` — read/update user goals
- `GET /api/dashboard/today` — combined summary for the home screen
- `POST /api/voice/query` — accepts a transcribed question, returns a
  natural-language answer grounded in the user's logged data

## Build roadmap

1. ~~Lock MVP scope~~ — done (squat/push-up/curl + general food photo flow)
2. ~~Project skeleton~~ — done (this repo)
3. **Build the form-correction engine** ← start here
   - Decide server-side vs. client-side pose estimation first (see "Known
     technical gotchas") — this changes where the rest of this phase's
     code lives, so confirm it with the user before writing angle logic
   - Replace the single-click "Analyze Frame" flow with continuous frame
     capture (an interval-based loop while a session is "active," with a
     start/stop control) — the current click-once flow cannot produce
     real-time feedback no matter what pose logic sits behind it
   - Implement angle calculation and the rep-counting state machine for
     one exercise first (squat), get it fully working end-to-end
     (camera → pose → angle check → rep count → on-screen feedback), then
     add push-up and bicep curl
   - Add the skeleton overlay on the frontend video feed
   - Add TTS voice cues once the core loop is reliable
4. **Build the nutrition scanner**
   - Integrate a food classification model into `analyze_food`
   - Wire up the USDA FoodData Central lookup
   - Add manual-correction UI for misidentified food
5. **Unify into one assistant**
   - Add the database (SQLite) and the workout/meal/profile endpoints
   - Build the combined dashboard page
6. **Add the voice layer**
   - Push-to-talk query flow using Web Speech API
   - `/api/voice/query` endpoint that answers from logged data
7. **Polish & stretch features**
   - Trend charts, fatigue detection, personalized suggestions

Work through these in order. Don't start Phase 4 work while Phase 3 is
half-finished — get one exercise fully working end-to-end (camera → pose →
angle check → rep count → voice feedback) before moving on.

## Coding conventions

- Backend: type-hint everything, use Pydantic models for request/response
  shapes (following the pattern already in `main.py`), keep ML logic in
  its own module (e.g. `backend/pose_engine.py`, `backend/food_engine.py`)
  rather than inline in the route handlers, so it stays testable and
  swappable
- Frontend: functional components with hooks, one component per file
  (matching the existing structure), keep API calls in a small shared
  helper rather than repeating `axios.post` boilerplate in every page
  once there are more than two or three endpoints
- Write a short docstring/comment explaining *why*, not just *what*, for
  any non-obvious logic (angle-threshold choices, state-machine
  transitions) — the user is learning from this code
- Prefer getting one exercise or one flow fully working over building
  wide-but-shallow across everything at once

## Questions to ask the user before big decisions

Don't silently assume these — ask:
- Whether pose estimation should run server-side (Python, in the existing
  backend) or client-side (JavaScript, via MediaPipe Tasks Vision) — see
  "Known technical gotchas" for the trade-off
- Whether it's worth setting up an HTTPS tunnel (`ngrok`) to actually
  demo the Nutrition scanner from a phone, or whether using the laptop's
  own camera for both modules is good enough for the demo — this is a
  real time/setup cost, not just a preference
- Which exercise to get working first if squat turns out harder than
  expected to tune (angle thresholds can be finicky)
- Whether to fine-tune a custom food-classification model vs. use an
  off-the-shelf pretrained one (fine-tuning is more impressive for a
  major project but takes longer and needs a labeled dataset)
- Whether wake-word activation is worth the extra Porcupine setup, or
  whether push-to-talk is good enough for the demo
- Any deadline that should shape how much of the "stretch" list is
  realistic to attempt

## Working style

Explain each significant piece of logic as you write it — this student
wants to understand pose-angle math, state machines, and model integration,
not just end up with working code they can't explain in a viva. Build and
verify one small piece at a time rather than generating large amounts of
code in one pass. If something in this brief is ambiguous or you think a
different technical choice would serve the project better, ask before
proceeding rather than guessing.
