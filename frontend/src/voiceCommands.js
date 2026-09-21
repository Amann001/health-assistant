// Matches a transcribed push-to-talk utterance to one of a small set of
// in-session voice commands.
//
// This is deliberately simple pattern matching, not an NLU model or an LLM
// call — and it deliberately only answers from the CURRENT session's live
// state (rep count, current feedback), never from history. CLAUDE.md's full
// Module 4 vision ("how much protein have I had today," "how was my squat
// form this week") needs a database of logged sessions that Phase 5 hasn't
// built yet — this is a smaller, honestly-scoped piece of it: a real,
// working two-way voice channel for the session you're in right now.
export function interpretCommand(text, { repCount, goodFormReps, goodFormStreak, feedback }) {
  if (!text) {
    return { reply: "Sorry, I didn't catch that. Try asking how many reps, or how's my form." }
  }

  if (/(good|proper|correct).*(rep|form)/.test(text) || /(rep|form).*(good|proper|correct)/.test(text)) {
    return { reply: `${goodFormReps} good-form reps out of ${repCount} total.` }
  }

  if (/streak|combo/.test(text)) {
    return {
      reply: goodFormStreak > 0
        ? `You're on a ${goodFormStreak}-rep good-form streak.`
        : "No active streak yet — your next good rep starts one.",
    }
  }

  if (/how (many|much)/.test(text) && /rep/.test(text)) {
    return { reply: `You're at ${repCount} reps.` }
  }

  if (/form|doing/.test(text)) {
    return { reply: feedback || 'Looking steady — keep going.' }
  }

  if (/stop|end|that'?s (enough|it)|i'?m done|i am done|finish|no more/.test(text)) {
    return { reply: 'Ending your session — nice work.', action: 'stop' }
  }

  return { reply: "I can tell you your rep count, your form, or your streak — or say stop to end the session." }
}
