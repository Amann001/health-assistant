import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar.jsx'
import Workout from './pages/Workout.jsx'
import Nutrition from './pages/Nutrition.jsx'

function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <main className="page-container">
        <Routes>
          <Route path="/" element={<Workout />} />
          <Route path="/nutrition" element={<Nutrition />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App
