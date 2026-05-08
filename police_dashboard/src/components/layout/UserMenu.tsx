import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

function initials(name?: string): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?';
}

export default function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  return (
    <div className="user-wrap" ref={wrapRef}>
      <button
        type="button"
        className="user-trigger"
        onClick={() => setOpen((s) => !s)}
        aria-label="User menu"
      >
        <span className="user-avatar">{initials(user?.full_name)}</span>
        <span className="user-meta">
          <strong>{user?.full_name}</strong>
          <span className="user-role">{user?.role}</span>
        </span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>

      {open && (
        <div className="user-panel">
          <div className="user-panel-head">
            <div className="user-avatar lg">{initials(user?.full_name)}</div>
            <div>
              <strong>{user?.full_name}</strong>
              <div className="user-panel-email">{user?.email}</div>
            </div>
          </div>
          <div className="user-panel-list">
            <Link to="/settings" onClick={() => setOpen(false)}>
              <span>⚙️</span> Settings
            </Link>
            <Link to="/analytics" onClick={() => setOpen(false)}>
              <span>📈</span> Analytics
            </Link>
          </div>
          <div className="user-panel-foot">
            <button className="ghost btn-block" onClick={logout}>
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
