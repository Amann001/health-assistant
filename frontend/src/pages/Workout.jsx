import { useEffect, useRef, useState } from 'react'
import WebcamFeed from '../components/WebcamFeed.jsx'
import { startFormSession, analyzeFormFrame } from '../api.js'
import { speak, stopSpeaking } from '../speech.js'
import { drawSkeleton } from '../skeleton.js'

// Only squat is implemented server-side so far (see backend/pose_engine.py).
// This becomes a dropdown once push-up/curl are added.
const EXERCISE = 'squat'

// How often we grab a frame and send it to the backend while a session is
// active. Real-time feedback needs continuous capture, not a single click —
// 300ms is frequent enough to feel responsive without flooding the backend
// (each request round-trips through JPEG decode + pose estimation).
const CAPTURE_INTERVAL_MS = 300

function Workout() {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const overlayCanvasRef = useRef(null)
  const intervalRef = useRef(null)
  // Guards against overlapping requests: if a frame is still being analyzed
  // when the next interval tick fires, skip that tick rather than firing a
  // second request on top of it.
  const busyRef = useRef(false)
  // Web Speech API generally needs its first call to happen from a user
  // gesture (the Start Session click) — this also keeps us from reading
  // the placeholder text out loud on page load, before anyone's clicked
  // anything.
  const hasStartedRef = useRef(false)
  const lastSpokenRef = useRef(null)

  const [sessionActive, setSessionActive] = useState(false)
  const [feedback, setFeedback] = useState('Press "Start Session" to begin.')
  const [repCount, setRepCount] = useState(0)
  const [goodFormReps, setGoodFormReps] = useState(0)

  // Speak each new feedback message once, as it arrives — not every 300ms
  // tick, since most ticks repeat the same cue while nothing's changed.
  useEffect(() => {
    if (!hasStartedRef.current) return
    if (feedback && feedback !== lastSpokenRef.current) {
      lastSpokenRef.current = feedback
      speak(feedback)
    }
  }, [feedback])

  // Stop the capture loop if the user navigates away mid-session.
  useEffect(() => {
    return () => {
      clearInterval(intervalRef.current)
      stopSpeaking()
    }
  }, [])

  function captureFrame() {
    return new Promise((resolve) => {
      const video = videoRef.current
      const canvas = canvasRef.current
      if (!video || !canvas || video.videoWidth === 0) {
        resolve(null)
        return
      }
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
      canvas.toBlob(resolve, 'image/jpeg')
    })
  }

  async function analyzeOnce() {
    if (busyRef.current) return
    busyRef.current = true
    try {
      const blob = await captureFrame()
      if (!blob) return
      const data = await analyzeFormFrame(EXERCISE, blob)
      setFeedback(data.feedback)
      setRepCount(data.rep_count)
      setGoodFormReps(data.good_form_reps)
      if (overlayCanvasRef.current && videoRef.current) {
        drawSkeleton(overlayCanvasRef.current, videoRef.current, data.landmarks)
      }
    } catch (err) {
      console.error(err)
      setFeedback('Lost connection to the backend — is it still running?')
    } finally {
      busyRef.current = false
    }
  }

  async function startSession() {
    try {
      await startFormSession(EXERCISE)
    } catch (err) {
      console.error(err)
      setFeedback('Could not reach the backend. Is it running on port 8000?')
      return
    }
    hasStartedRef.current = true
    lastSpokenRef.current = null
    setRepCount(0)
    setGoodFormReps(0)
    setFeedback('Session started — get in position.')
    setSessionActive(true)
    intervalRef.current = setInterval(analyzeOnce, CAPTURE_INTERVAL_MS)
  }

  function stopSession() {
    clearInterval(intervalRef.current)
    intervalRef.current = null
    stopSpeaking()
    if (overlayCanvasRef.current && videoRef.current) {
      drawSkeleton(overlayCanvasRef.current, videoRef.current, null)
    }
    setSessionActive(false)
    setFeedback(`Session ended — ${repCount} reps, ${goodFormReps} good form.`)
  }

  return (
    <section className="page">
      <h2>Form Check — Squat</h2>
      <p className="page-subtitle">
        Start a session, then squat in view of the camera. While active, a frame is captured
        and analyzed automatically every {CAPTURE_INTERVAL_MS}ms — no need to click anything
        per rep.
      </p>
      <div className="webcam-container">
        <WebcamFeed videoRef={videoRef} />
        <canvas ref={overlayCanvasRef} className="skeleton-overlay" />
      </div>
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {sessionActive ? (
        <button onClick={stopSession}>Stop Session</button>
      ) : (
        <button onClick={startSession}>Start Session</button>
      )}

      <div className="workout-stats">
        <span>Reps: {repCount}</span>
        <span>Good form: {goodFormReps}</span>
      </div>

      <p className="feedback">{feedback}</p>
    </section>
  )
}

export default Workout
