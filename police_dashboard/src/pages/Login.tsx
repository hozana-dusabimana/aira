import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('officer1@rnp.gov.rw');
  const [password, setPassword] = useState('Officer@1');
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
      setError(err?.response?.data?.detail ?? 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit}>
        <h1>AIRA — RNP Dashboard</h1>
        <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 24 }}>
          Sign in with your officer account.
        </p>
        <div className="field">
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="field">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button disabled={loading} type="submit" style={{ width: '100%' }}>
          {loading ? 'Signing in...' : 'Sign in'}
        </button>
        {error && <div className="error">{error}</div>}
      </form>
    </div>
  );
}
