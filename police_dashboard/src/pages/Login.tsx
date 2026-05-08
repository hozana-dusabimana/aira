import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('officer1@rnp.gov.rw');
  const [password, setPassword] = useState('Officer@1');
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-shell">
        <aside className="auth-side">
          <Link to="/" className="brand brand-light">
            <div className="brand-mark">A</div>
            <div className="brand-text">
              <strong>AIRA</strong>
              <span>Rwanda National Police</span>
            </div>
          </Link>
          <div className="auth-side-content">
            <h2>Operations dashboard</h2>
            <p>
              Secure access for Rwanda National Police officers. Triage incidents,
              dispatch units and resolve cases in real time.
            </p>
            <ul className="auth-side-list">
              <li>Real-time incident feed and alerts</li>
              <li>AI-verified evidence and severity</li>
              <li>Live map and officer dispatch</li>
              <li>End-to-end audit trail</li>
            </ul>
          </div>
          <div className="auth-side-footer">
            <span>© {new Date().getFullYear()} AIRA</span>
            <span>v1.0.0</span>
          </div>
        </aside>

        <main className="auth-main">
          <div className="auth-top">
            <Link to="/" className="auth-back">← Back to home</Link>
          </div>
          <div className="auth-form-wrap">
            <div className="brand brand-mobile">
              <div className="brand-mark">A</div>
              <div className="brand-text">
                <strong>AIRA</strong>
                <span>Rwanda National Police</span>
              </div>
            </div>
            <h1>Officer sign in</h1>
            <p className="auth-sub">
              Welcome back. Please enter your credentials to access the dashboard.
            </p>

            <form className="auth-form" onSubmit={onSubmit}>
              <div className="field">
                <label htmlFor="email">Email address</label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="officer@rnp.gov.rw"
                  required
                />
              </div>

              <div className="field">
                <div className="field-label-row">
                  <label htmlFor="password">Password</label>
                  <a href="#" onClick={(e) => e.preventDefault()} className="link-muted">Forgot password?</a>
                </div>
                <div className="password-input">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword((s) => !s)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                />
                <span>Keep me signed in on this device</span>
              </label>

              {error && <div className="alert alert-error">{error}</div>}

              <button disabled={loading} type="submit" className="btn-primary btn-block">
                {loading ? 'Signing in...' : 'Sign in to dashboard'}
              </button>

              <p className="auth-help">
                Trouble signing in? Contact your station administrator or the
                AIRA support desk.
              </p>
            </form>
          </div>
        </main>
      </div>
    </div>
  );
}
