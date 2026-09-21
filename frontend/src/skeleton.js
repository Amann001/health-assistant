// Draws the pose skeleton MediaPipe detects on top of the webcam video.
// Kept separate from Workout.jsx so the "how do normalized landmark
// coordinates become pixels on screen" math doesn't clutter the
// session-control logic.

// MediaPipe's 33-point pose model uses fixed landmark indices
// (https://ai.google.dev/mediapipe/solutions/vision/pose_landmarker) --
// these match the ones backend/pose_engine.py's JOINT_LANDMARKS uses for
// angle math. We only connect the joints relevant to exercise form --
// shoulders, arms, hips, legs, plus a rough head indicator -- skipping the
// face/finger detail MediaPipe also reports, since a clean stick figure
// reads far more clearly during a live workout than a full face mesh
// would. Arms (elbow/wrist) aren't used by squat's angle math yet, but are
// included now so this same overlay works unchanged once push-up/curl are
// added.
const POSE_CONNECTIONS = [
  [11, 12], // shoulder to shoulder
  [11, 13], [13, 15], // left arm: shoulder -> elbow -> wrist
  [12, 14], [14, 16], // right arm
  [11, 23], [12, 24], // torso sides: shoulder -> hip
  [23, 24], // hip to hip
  [23, 25], [25, 27], // left leg: hip -> knee -> ankle
  [24, 26], [26, 28], // right leg
  [0, 11], [0, 12], // nose to shoulders, a rough head/neck indicator
]

// Below this, MediaPipe itself isn't confident the landmark is real --
// drawing it would show a wobbly, distracting guess rather than useful
// feedback. Matches the visibility-gate philosophy pose_engine.py uses
// server-side for the same reason.
const MIN_DRAW_VISIBILITY = 0.5

/**
 * Converts a normalized (0-1) landmark coordinate into a pixel position on
 * the overlay canvas, replicating the video element's `object-fit: cover`
 * (see index.css's .webcam-feed) so the skeleton lines up with what's
 * actually visible on screen instead of the raw, possibly-cropped camera
 * frame. `object-fit: cover` scales the video up until it fully fills the
 * box, then centers and crops the overflow off two opposite edges — this
 * redoes that exact transform for each point.
 */
function projectPoint(nx, ny, videoWidth, videoHeight, canvasWidth, canvasHeight) {
  const videoAspect = videoWidth / videoHeight
  const boxAspect = canvasWidth / canvasHeight
  let scale
  let cropX = 0
  let cropY = 0

  if (videoAspect > boxAspect) {
    // Video is relatively wider than the box -> left/right edges are what
    // get cropped off.
    scale = canvasHeight / videoHeight
    cropX = (videoWidth * scale - canvasWidth) / 2
  } else {
    // Video is relatively taller than the box -> top/bottom get cropped.
    scale = canvasWidth / videoWidth
    cropY = (videoHeight * scale - canvasHeight) / 2
  }

  return {
    x: nx * videoWidth * scale - cropX,
    y: ny * videoHeight * scale - cropY,
  }
}

/**
 * Clears and redraws the skeleton overlay for one frame's worth of
 * landmarks. `video` supplies the camera's native resolution (needed for
 * the object-fit math above); `canvas` is the transparent overlay sitting
 * on top of the <video> element. Passing `landmarks: null` just clears it.
 */
export function drawSkeleton(canvas, video, landmarks) {
  const width = canvas.clientWidth
  const height = canvas.clientHeight
  // Resizing the backing buffer to match the CSS size keeps lines crisp
  // and, as a side effect, clears whatever was drawn last frame.
  canvas.width = width
  canvas.height = height

  if (!landmarks || !video.videoWidth || !width || !height) return

  const points = landmarks.map((lm) =>
    lm.visibility >= MIN_DRAW_VISIBILITY
      ? projectPoint(lm.x, lm.y, video.videoWidth, video.videoHeight, width, height)
      : null
  )

  const ctx = canvas.getContext('2d')

  ctx.strokeStyle = '#34c7ab'
  ctx.lineWidth = 3
  ctx.lineCap = 'round'
  for (const [a, b] of POSE_CONNECTIONS) {
    const pointA = points[a]
    const pointB = points[b]
    if (!pointA || !pointB) continue
    ctx.beginPath()
    ctx.moveTo(pointA.x, pointA.y)
    ctx.lineTo(pointB.x, pointB.y)
    ctx.stroke()
  }

  ctx.fillStyle = '#e7e5de'
  for (const point of points) {
    if (!point) continue
    ctx.beginPath()
    ctx.arc(point.x, point.y, 4, 0, Math.PI * 2)
    ctx.fill()
  }
}
