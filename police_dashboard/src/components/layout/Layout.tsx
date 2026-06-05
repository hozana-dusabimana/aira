import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import GlobalSearch from './GlobalSearch';
import NotificationsBell from './NotificationsBell';
import SystemStatus from './SystemStatus';
import UserMenu from './UserMenu';

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/incidents': 'Incidents',
  '/spam': 'Spam',
  '/map': 'Live operations map',
  '/analytics': 'Analytics',
  '/officers': 'Officers',
  '/status': 'System status',
  '/settings': 'Settings',
};

function pageTitle(pathname: string): string {
  if (pathname.startsWith('/incidents/') && pathname !== '/incidents') return 'Incident details';
  return PAGE_TITLES[pathname] ?? 'Police Operations';
}

export default function Layout() {
  const { user } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.body.style.overflow = sidebarOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [sidebarOpen]);

  return (
    <div className={`layout ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">A</div>
          <div className="brand-text">
            <strong>AIRA</strong>
            <span>RNP Dashboard</span>
          </div>
        </div>

        <div className="sidebar-section-label">Operations</div>
        <nav>
          <NavLink to="/" end>
            <span className="nav-icon" aria-hidden>📊</span> Dashboard
          </NavLink>
          <NavLink to="/incidents">
            <span className="nav-icon" aria-hidden>🚨</span> Incidents
          </NavLink>
          <NavLink to="/spam">
            <span className="nav-icon" aria-hidden>🛑</span> Spam
          </NavLink>
          <NavLink to="/map">
            <span className="nav-icon" aria-hidden>🗺️</span> Live Map
          </NavLink>
          <NavLink to="/analytics">
            <span className="nav-icon" aria-hidden>📈</span> Analytics
          </NavLink>
        </nav>

        {user?.role === 'admin' && (
          <>
            <div className="sidebar-section-label">Administration</div>
            <nav>
              <NavLink to="/officers">
                <span className="nav-icon" aria-hidden>👮</span> Officers
              </NavLink>
            </nav>
          </>
        )}

        <div className="sidebar-section-label">Account</div>
        <nav>
          <NavLink to="/status">
            <span className="nav-icon" aria-hidden>🩺</span> System Status
          </NavLink>
          <NavLink to="/settings">
            <span className="nav-icon" aria-hidden>⚙️</span> Settings
          </NavLink>
        </nav>

        <SystemStatus />

        <div className="footer">
          AI Incident Reporting<br />v1.0.0
        </div>
      </aside>

      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <main className="main">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="menu-toggle"
              aria-label="Toggle navigation"
              onClick={() => setSidebarOpen((s) => !s)}
            >
              <span />
              <span />
              <span />
            </button>
            <div className="topbar-title">
              <h2>{pageTitle(location.pathname)}</h2>
              <span className="topbar-sub">Welcome back, {user?.full_name?.split(' ')[0]}</span>
            </div>
          </div>
          <div className="topbar-mid">
            <GlobalSearch />
          </div>
          <div className="topbar-right">
            <NotificationsBell />
            <UserMenu />
          </div>
        </header>
        <div className="content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
