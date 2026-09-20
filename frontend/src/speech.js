// Thin wrapper around the Web Speech API's speech-synthesis (TTS) half.
// Unlike its speech-*recognition* half, TTS runs genuinely locally in the
// browser and is broadly supported — see CLAUDE.md "Known technical
// gotchas" for why that distinction matters.

export function speak(text) {
  if (!text || !('speechSynthesis' in window)) return
  // Cancel whatever's still playing so cues don't queue up behind a stale
  // one — by the time a new cue arrives, the old one is no longer relevant.
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text))
}

export function stopSpeaking() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}
