import { useState } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useShowFlagged } from '../hooks/useShowFlagged';
import { APK_URL } from '../config';

export default function Settings() {
  const { user } = useAuth();
  const [showFlagged, setShowFlagged] = useShowFlagged();
  const [current, setCurrent] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null); setErr(null);
    try {
      await api.post('/users/me/change-password', {
        current_password: current,
        new_password: newPwd,
      });
      setMsg('Password updated successfully');
      setCurrent(''); setNewPwd('');
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? 'Could not update password');
    }
  }

  return (
    <div>
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Profile</h3>
        <table className="table">
          <tbody>
            <tr><th>Name</th><td>{user?.full_name}</td></tr>
            <tr><th>Email</th><td>{user?.email}</td></tr>
            <tr><th>Phone</th><td>{user?.phone ?? '—'}</td></tr>
            <tr><th>Role</th><td>{user?.role}</td></tr>
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Mobile app</h3>
        <p style={{ color: 'var(--muted)', marginTop: 0 }}>
          Download the AIRA Android app to report and review incidents on the go.
        </p>
        <a href={APK_URL} className="btn-primary btn-download" download>
          <span aria-hidden="true">⬇</span> Download Android app (APK)
        </a>
        <p style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 0 }}>
          Android only · enable “install from unknown sources” to complete setup.
        </p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>Duplicate reports</h3>
        <p style={{ color: 'var(--muted)', marginTop: 0, marginBottom: 0 }}>
          Review duplicate reports of accidents already reported nearby, plus any older
          rejected reports you import.
        </p>
        <div className="setting-row">
          <div className="setting-row-text">
            <span className="setting-row-title">Show duplicates</span>
            <span className="setting-row-hint">Display the “Flagged” section in the sidebar.</span>
          </div>
          <label className="toggle">
            <input
              type="checkbox"
              checked={showFlagged}
              onChange={(e) => setShowFlagged(e.target.checked)}
            />
            <span className="toggle-track" aria-hidden="true" />
          </label>
        </div>
      </div>

      <form className="card" onSubmit={changePassword}>
        <h3 style={{ marginTop: 0 }}>Change password</h3>
        <div className="field">
          <label>Current password</label>
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
        </div>
        <div className="field">
          <label>New password</label>
          <input type="password" minLength={8} value={newPwd} onChange={(e) => setNewPwd(e.target.value)} required />
        </div>
        <button type="submit">Update password</button>
        {msg && <div style={{ color: 'var(--green)', marginTop: 12 }}>{msg}</div>}
        {err && <div className="error">{err}</div>}
      </form>
    </div>
  );
}
