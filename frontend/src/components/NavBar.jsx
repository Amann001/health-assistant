import { NavLink } from 'react-router-dom'

function NavBar() {
  return (
    <header className="navbar">
      <span className="brand">Health Assistant</span>
      <nav className="nav-links">
        <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
          Workout
        </NavLink>
        <NavLink to="/nutrition" className={({ isActive }) => (isActive ? 'active' : '')}>
          Nutrition
        </NavLink>
      </nav>
    </header>
  )
}

export default NavBar
