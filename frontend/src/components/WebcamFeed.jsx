import { useEffect, useRef } from 'react'

/**
 * Turns on the device camera and streams it into a <video> element.
 *
 * Pass in a `videoRef` from the parent component so the parent can grab
 * still frames off the live feed later (e.g. to send to the backend
 * for pose analysis or food recognition).
 */
function WebcamFeed({ videoRef }) {
  const fallbackRef = useRef(null)
  const ref = videoRef || fallbackRef

  useEffect(() => {
    let stream

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true })
        if (ref.current) {
          ref.current.srcObject = stream
        }
      } catch (err) {
        console.error('Could not access camera:', err)
      }
    }

    startCamera()

    // Turn the camera light off when we leave the page.
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [ref])

  return <video ref={ref} autoPlay playsInline muted className="webcam-feed" />
}

export default WebcamFeed
