import axios from 'axios'

const BASE_URL = 'http://localhost:8000'

/** Resets the server-side rep counter for `exercise`. Call once when a workout session starts. */
export function startFormSession(exercise) {
  const formData = new FormData()
  formData.append('exercise', exercise)
  return axios.post(`${BASE_URL}/api/form/start`, formData).then((res) => res.data)
}

/** Sends one webcam frame (JPEG blob) for pose analysis. Returns { exercise, rep_count, good_form_reps, feedback }. */
export function analyzeFormFrame(exercise, blob) {
  const formData = new FormData()
  formData.append('frame', blob, 'frame.jpg')
  formData.append('exercise', exercise)
  return axios.post(`${BASE_URL}/api/form/analyze`, formData).then((res) => res.data)
}
