import { useEffect, useState } from 'react';
import { officers as officersApi } from '../services/api';
import type { Officer } from '../types';

const EMPTY = {
  full_name: '',
  email: '',
  phone: '',
  password: '',
  badge_number: '',
  station_id: '',
  rank: '',
  department: '',
};

export default function Officers() {
  const [list, setList] = useState<Officer[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ ...EMPTY });

  const isEditing = editingId !== null;

  async function refresh() {
    try {
      setList(await officersApi.list());
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to load');
    }
  }

  useEffect(() => { refresh(); }, []);

  function startCreate() {
    setEditingId(null);
    setForm({ ...EMPTY });
    setError('');
    setShowForm(true);
  }

  function startEdit(o: Officer) {
    setEditingId(o.id);
    setForm({
      full_name: o.full_name ?? '',
      email: o.email ?? '',
      phone: o.phone ?? '',
      password: '',
      badge_number: o.badge_number,
      station_id: o.station_id ? String(o.station_id) : '',
      rank: o.rank ?? '',
      department: o.department ?? '',
    });
    setError('');
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm({ ...EMPTY });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      if (isEditing) {
        await officersApi.update(editingId!, {
          full_name: form.full_name,
          email: form.email,
          phone: form.phone || undefined,
          badge_number: form.badge_number,
          rank: form.rank || undefined,
          department: form.department || undefined,
          station_id: form.station_id ? Number(form.station_id) : undefined,
          // Only send a password when the admin typed a new one.
          ...(form.password ? { password: form.password } : {}),
        });
      } else {
        await officersApi.create({
          ...form,
          station_id: form.station_id ? Number(form.station_id) : undefined,
        });
      }
      closeForm();
      refresh();
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? (isEditing ? 'Update failed' : 'Create failed'));
    }
  }

  async function remove(o: Officer) {
    if (!window.confirm(`Permanently delete officer ${o.full_name ?? o.badge_number}? Their login is revoked and any incidents assigned to them are unassigned. This cannot be undone.`)) {
      return;
    }
    setBusyId(o.id);
    setError('');
    try {
      await officersApi.remove(o.id);
      setList((prev) => prev.filter((x) => x.id !== o.id));
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Delete failed');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Officers</h2>
        <button onClick={() => (showForm ? closeForm() : startCreate())}>
          {showForm ? 'Close' : 'Add officer'}
        </button>
      </div>

      {showForm && (
        <form className="card officer-form" onSubmit={submit} style={{ marginBottom: 16 }}>
          <div className="officer-form-head">
            <h3>{isEditing ? 'Edit officer' : 'New officer'}</h3>
            <p className="card-sub">
              {isEditing
                ? 'Update this officer’s details. Leave password blank to keep the current one.'
                : 'Create a police officer account. Fields marked * are required.'}
            </p>
          </div>

          <fieldset className="form-section">
            <legend>Account</legend>
            <div className="form-grid">
              <div className="field"><label>Full name *</label><input required value={form.full_name} onChange={(e) => setForm({...form, full_name: e.target.value})} placeholder="e.g. Jean Habimana" /></div>
              <div className="field"><label>Email *</label><input type="email" required value={form.email} onChange={(e) => setForm({...form, email: e.target.value})} placeholder="officer@police.gov.rw" /></div>
              <div className="field"><label>Phone</label><input value={form.phone} onChange={(e) => setForm({...form, phone: e.target.value})} placeholder="+250 7xx xxx xxx" /></div>
              <div className="field"><label>{isEditing ? 'New password' : 'Password *'}</label><input type="password" required={!isEditing} minLength={8} value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} placeholder={isEditing ? 'Leave blank to keep current' : 'At least 8 characters'} /></div>
            </div>
          </fieldset>

          <fieldset className="form-section">
            <legend>Assignment</legend>
            <div className="form-grid">
              <div className="field"><label>Badge number *</label><input required value={form.badge_number} onChange={(e) => setForm({...form, badge_number: e.target.value})} placeholder="e.g. RNP-00231" /></div>
              {/* Station selector hidden by request — station_id is nullable in the DB, so it is left unset (NULL) and can be assigned later. */}
              <div className="field"><label>Rank</label><input value={form.rank} onChange={(e) => setForm({...form, rank: e.target.value})} placeholder="e.g. Sergeant" /></div>
              <div className="field"><label>Department</label><input value={form.department} onChange={(e) => setForm({...form, department: e.target.value})} placeholder="e.g. Traffic" /></div>
            </div>
          </fieldset>

          {error && <div className="alert alert-error" style={{ marginTop: 4 }}>{error}</div>}

          <div className="form-actions">
            <button type="button" className="btn-ghost" onClick={closeForm}>Cancel</button>
            <button type="submit">{isEditing ? 'Save changes' : 'Create officer'}</button>
          </div>
        </form>
      )}

      {!showForm && error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="card">
        <table className="table">
          <thead>
            {/* Station column hidden by request */}
            <tr>
              <th>ID</th><th>Name</th><th>Email</th><th>Badge</th><th>Rank</th><th>Department</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {list.map((o) => (
              <tr key={o.id}>
                <td>#{o.id}</td>
                <td>{o.full_name ?? '—'}</td>
                <td>{o.email ?? '—'}</td>
                <td>{o.badge_number}</td>
                <td>{o.rank ?? '—'}</td>
                <td>{o.department ?? '—'}</td>
                <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                  <button className="ghost" onClick={() => startEdit(o)} disabled={busyId === o.id}>
                    Edit
                  </button>
                  <button className="ghost" style={{ marginLeft: 8 }} onClick={() => remove(o)} disabled={busyId === o.id}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {list.length === 0 && <tr><td colSpan={7} style={{ color: 'var(--muted)' }}>No officers.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
