import { useEffect, useRef, useState } from 'react'
import WebcamFeed from '../components/WebcamFeed.jsx'
import { startFormSession, analyzeFormFrame } from '../api.js'
import { speak, stopSpeaking } from '../speech.js'
import { drawSkeleton } from '../skeleton.js'
import { startListening, isListeningSupported } from '../listen.js'
import { interpretCommand } from '../voiceCommands.js'

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
  // While a push-to-talk turn is in progress, the auto-speak effect below
  // stays quiet — otherwise a coaching cue could start talking over the
  // user's own command mid-utterance, or bleed into the mic as crosstalk.
  const listeningRef = useRef(false)
  const listenControllerRef = useRef(null)

  const [sessionActive, setSessionActive] = useState(false)
  const [feedback, setFeedback] = useState('Press "Start Session" to begin.')
  const [repCount, setRepCount] = useState(0)
  const [goodFormReps, setGoodFormReps] = useState(0)
  const [goodFormStreak, setGoodFormStreak] = useState(0)
  const [depthProgress, setDepthProgress] = useState(0)
  const [isListening, setIsListening] = useState(false)
  const [voiceReply, setVoiceReply] = useState('')

  // Speak each new feedback message once, as it arrives — not every 300ms
  // tick, since most ticks repeat the same cue while nothing's changed.
  useEffect(() => {
    if (!hasStartedRef.current || listeningRef.current) return
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
      setGoodFormStreak(data.good_form_streak)
      setDepthProgress(data.depth_progress ?? 0)
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
    let data
    try {
      data = await startFormSession(EXERCISE)
    } catch (err) {
      console.error(err)
      setFeedback('Could not reach the backend. Is it running on port 8000?')
      return
    }
    hasStartedRef.current = true
    lastSpokenRef.current = null
    setRepCount(0)
    setGoodFormReps(0)
    setGoodFormStreak(0)
    setDepthProgress(0)
    setVoiceReply('')
    // The backend generates this from the real angle thresholds (see
    // pose_engine.exercise_intro), so what you're told to expect can never
    // drift out of sync with what's actually being checked. Reusing the
    // ordinary feedback state/auto-speak effect means it's just spoken and
    // shown like any other cue — no separate UI or speak() call needed.
    setFeedback(data.coaching_intro || 'Session started — get in position.')
    setSessionActive(true)
    intervalRef.current = setInterval(analyzeOnce, CAPTURE_INTERVAL_MS)
  }

  // `interruptSpeech` is false when a voice command triggered the stop, so
  // the spoken confirmation (built in handleVoiceResult, which already
  // covers the same summary) gets to finish instead of being cut off by
  // this function's own routine "Session ended" cue.
  function stopSession(interruptSpeech = true) {
    clearInterval(intervalRef.current)
    intervalRef.current = null
    if (interruptSpeech) stopSpeaking()
    if (overlayCanvasRef.current && videoRef.current) {
      drawSkeleton(overlayCanvasRef.current, videoRef.current, null)
    }
    setSessionActive(false)
    setFeedback(`Session ended — ${repCount} reps, ${goodFormReps} good form.`)
  }

  function handleVoiceResult(text) {
    const { reply, action } = interpretCommand(text, { repCount, goodFormReps, goodFormStreak, feedback })
    setVoiceReply(reply)

    if (action === 'stop') {
      // Pre-mark the "Session ended" text stopSession() is about to set as
      // already spoken, so the auto-speak effect doesn't cut off this
      // combined reply by trying to announce it a second time.
      lastSpokenRef.current = `Session ended — ${repCount} reps, ${goodFormReps} good form.`
      speak(`${reply} That's ${repCount} reps, ${goodFormReps} good form.`)
      stopSession(false)
    } else {
      speak(reply)
    }
  }

  function startTalking() {
    if (!sessionActive || isListening) return
    listeningRef.current = true
    setIsListening(true)
    setVoiceReply('')
    stopSpeaking() // don't let a coaching cue bleed into the mic as crosstalk
    listenControllerRef.current = startListening({
      onResult: handleVoiceResult,
      onDone: () => {
        listeningRef.current = false
        setIsListening(false)
      },
    })
  }

  function stopTalking() {
    listenControllerRef.current?.stop()
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

      {sessionActive && (
        <div className="depth-gauge" aria-label="Squat depth this rep">
          <div className="depth-gauge-fill" style={{ width: `${depthProgress * 100}%` }} />
        </div>
      )}

      <div className="session-controls">
        {sessionActive ? (
          <button onClick={() => stopSession(true)}>Stop Session</button>
        ) : (
          <button onClick={startSession}>Start Session</button>
        )}

        {sessionActive && isListeningSupported() && (
          // Tap, not hold: recognition already stops itself the moment you
          // stop talking (the browser's own silence detection), so making
          // someone physically hold a button through a squat was never
          // necessary — just adding friction to exactly the moment
          // (mid-exercise) when a free hand is hardest to spare.
          <button
            className={`talk-button${isListening ? ' listening' : ''}`}
            onClick={isListening ? stopTalking : startTalking}
          >
            {isListening ? 'Listening… (tap to stop)' : 'Tap to Talk'}
          </button>
        )}
      </div>

      <div className="workout-stats">
        <span>Reps: {repCount}</span>
        <span>Good form: {goodFormReps}</span>
        {goodFormStreak >= 2 && (
          <span className={`streak-badge${goodFormStreak >= 10 ? ' legendary' : goodFormStreak >= 5 ? ' fire' : ''}`}>
            {goodFormStreak}🔥 streak
          </span>
        )}
      </div>

      <p className="feedback">{feedback}</p>
      {voiceReply && <p className="voice-reply">🎙️ {voiceReply}</p>}
    </section>
  )
}

export default Workout
