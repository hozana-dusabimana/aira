import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>AIRA — RNP</h1>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/incidents">Incidents</NavLink>
          <NavLink to="/map">Map</NavLink>
          <NavLink to="/analytics">Analytics</NavLink>
          {user?.role === 'admin' && <NavLink to="/officers">Officers</NavLink>}
          <NavLink to="/settings">Settings</NavLink>
        </nav>
        <div className="footer">
          AI Incident Reporting<br/>v1.0.0
        </div>
      </aside>
      <main className="main">
        <div className="navbar">
          <h2>Police Operations</h2>
          <div className="user-info">
            <span>{user?.full_name} <span style={{ color: 'var(--muted)' }}>({user?.role})</span></span>
            <button className="ghost" onClick={logout}>Logout</button>
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
