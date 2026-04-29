import { useEffect, useState } from 'react';
import { officers as officersApi } from '../services/api';
import type { Officer, Station } from '../types';

export default function Officers() {
  const [list, setList] = useState<Officer[]>([]);
  const [stations, setStations] = useState<Station[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    password: '',
    badge_number: '',
    station_id: '',
    rank: '',
    department: '',
  });

  async function refresh() {
    try {
      const [o, s] = await Promise.all([officersApi.list(), officersApi.stations()]);
      setList(o);
      setStations(s);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to load');
    }
  }

  useEffect(() => { refresh(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      await officersApi.create({
        ...form,
        station_id: form.station_id ? Number(form.station_id) : undefined,
      });
      setShowForm(false);
      setForm({ full_name: '', email: '', phone: '', password: '', badge_number: '', station_id: '', rank: '', department: '' });
      refresh();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Create failed');
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Officers</h2>
        <button onClick={() => setShowForm((s) => !s)}>
          {showForm ? 'Close' : 'Add officer'}
        </button>
      </div>

      {showForm && (
        <form className="card" onSubmit={submit} style={{ marginBottom: 16 }}>
          <div className="detail-grid">
            <div>
              <div className="field"><label>Full name</label><input required value={form.full_name} onChange={(e) => setForm({...form, full_name: e.target.value})} /></div>
              <div className="field"><label>Email</label><input type="email" required value={form.email} onChange={(e) => setForm({...form, email: e.target.value})} /></div>
              <div className="field"><label>Phone</label><input value={form.phone} onChange={(e) => setForm({...form, phone: e.target.value})} /></div>
              <div className="field"><label>Password</label><input type="password" required minLength={8} value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} /></div>
            </div>
            <div>
              <div className="field"><label>Badge number</label><input required value={form.badge_number} onChange={(e) => setForm({...form, badge_number: e.target.value})} /></div>
              <div className="field">
                <label>Station</label>
                <select value={form.station_id} onChange={(e) => setForm({...form, station_id: e.target.value})}>
                  <option value="">—</option>
                  {stations.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div className="field"><label>Rank</label><input value={form.rank} onChange={(e) => setForm({...form, rank: e.target.value})} /></div>
              <div className="field"><label>Department</label><input value={form.department} onChange={(e) => setForm({...form, department: e.target.value})} /></div>
            </div>
          </div>
          <button type="submit">Create officer</button>
          {error && <div className="error">{error}</div>}
        </form>
      )}

      <div className="card">
        <table className="table">
          <thead>
            <tr><th>ID</th><th>Badge</th><th>Station</th><th>Rank</th><th>Department</th></tr>
          </thead>
          <tbody>
            {list.map((o) => (
              <tr key={o.id}>
                <td>#{o.id}</td>
                <td>{o.badge_number}</td>
                <td>{stations.find((s) => s.id === o.station_id)?.name ?? '—'}</td>
                <td>{o.rank ?? '—'}</td>
                <td>{o.department ?? '—'}</td>
              </tr>
            ))}
            {list.length === 0 && <tr><td colSpan={5} style={{ color: 'var(--muted)' }}>No officers.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
