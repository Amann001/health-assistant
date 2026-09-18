import { useRef, useState } from 'react'
import axios from 'axios'
import WebcamFeed from '../components/WebcamFeed.jsx'

function Nutrition() {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  async function captureAndAnalyze() {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob(async (blob) => {
      const formData = new FormData()
      formData.append('image', blob, 'meal.jpg')

      setLoading(true)
      try {
        const res = await axios.post('http://localhost:8000/api/nutrition/analyze', formData)
        setResult(res.data)
      } catch (err) {
        console.error(err)
        setResult(null)
      } finally {
        setLoading(false)
      }
    }, 'image/jpeg')
  }

  return (
    <section className="page">
      <h2>Meal Scanner</h2>
      <p className="page-subtitle">
        This will identify food and estimate macros in Phase 4. For now it just proves the
        camera and backend can talk to each other.
      </p>
      <WebcamFeed videoRef={videoRef} />
      <canvas ref={canvasRef} style={{ display: 'none' }} />
      <button onClick={captureAndAnalyze} disabled={loading}>
        {loading ? 'Scanning…' : 'Scan Meal'}
      </button>

      {result && (
        <dl className="result-card">
          <div>
            <dt>Food</dt>
            <dd>{result.food_name}</dd>
          </div>
          <div>
            <dt>Calories</dt>
            <dd>{result.calories}</dd>
          </div>
          <div>
            <dt>Protein</dt>
            <dd>{result.protein_g} g</dd>
          </div>
          <div>
            <dt>Carbs</dt>
            <dd>{result.carbs_g} g</dd>
          </div>
          <div>
            <dt>Fat</dt>
            <dd>{result.fat_g} g</dd>
          </div>
        </dl>
      )}
    </section>
  )
}

export default Nutrition
