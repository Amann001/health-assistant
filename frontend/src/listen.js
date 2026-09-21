// Push-to-talk speech-to-text via the Web Speech API's SpeechRecognition.
//
// Unlike speech.js's TTS half, this is NOT purely local — Chrome and Edge
// both route recognition through their cloud speech service, and Firefox/
// Safari don't support it at all. That's a known, accepted tradeoff (see
// CLAUDE.md's "Known technical gotchas"), not a hidden cost — audio is only
// sent while the talk button is actually held down.

const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition

export function isListeningSupported() {
  return !!SpeechRecognitionImpl
}

/**
 * Starts one push-to-talk listening turn. Call `.stop()` on the returned
 * controller when the user releases the talk button — recognition also
 * ends on its own after a pause in speech, via the browser's built-in
 * silence detection.
 *
 * `onResult` fires with the transcribed text (lowercased, trimmed) once
 * recognition finishes successfully. `onDone` always fires exactly once,
 * whether recognition succeeded, failed, or heard nothing — the caller
 * uses it to leave "listening" UI state regardless of outcome.
 */
export function startListening({ onResult, onDone }) {
  if (!SpeechRecognitionImpl) {
    onDone?.()
    return { stop: () => {} }
  }

  const recognition = new SpeechRecognitionImpl()
  recognition.lang = 'en-US'
  recognition.interimResults = false
  recognition.maxAlternatives = 1

  let done = false
  function finish() {
    if (done) return
    done = true
    onDone?.()
  }

  recognition.onresult = (event) => {
    const text = event.results[0]?.[0]?.transcript?.trim().toLowerCase()
    if (text) onResult(text)
  }
  recognition.onerror = finish
  recognition.onend = finish

  recognition.start()
  return { stop: () => recognition.stop() }
}
