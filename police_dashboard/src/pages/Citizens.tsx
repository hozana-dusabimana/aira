import { useEffect, useMemo, useState } from 'react';
import { citizens as citizensApi } from '../services/api';
import type { User } from '../types';

export default function Citizens() {
  const [list, setList] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      setList(await citizensApi.list());
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to load citizens');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter((u) =>
      [u.full_name, u.email, u.phone, u.national_id]
        .filter(Boolean)
        .some((v) => v!.toLowerCase().includes(q)),
    );
  }, [list, query]);

  async function toggleActive(u: User) {
    setBusyId(u.id);
    setError('');
    try {
      const updated = await citizensApi.update(u.id, { is_active: !u.is_active });
      setList((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Update failed');
    } finally {
      setBusyId(null);
    }
  }

  async function remove(u: User) {
    if (!window.confirm(`Permanently delete ${u.full_name}? Their account and all reports they submitted will be removed. This cannot be undone.`)) {
      return;
    }
    setBusyId(u.id);
    setError('');
    try {
      await citizensApi.remove(u.id);
      setList((prev) => prev.filter((x) => x.id !== u.id));
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Delete failed');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <strong>Registered citizens</strong>
            <div style={{ color: 'var(--muted)', fontSize: 13 }}>
              {list.length} citizen account{list.length === 1 ? '' : 's'}. Deactivate to block
              login, or delete to remove an account and all its reports.
            </div>
          </div>
          <input
            placeholder="Search name, email, phone…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ marginLeft: 'auto', maxWidth: 280 }}
          />
          <button className="ghost" onClick={load} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
        {error && <div className="alert alert-error" style={{ marginTop: 12 }}>{error}</div>}
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>National ID</th>
              <th>Status</th><th>Registered</th><th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((u) => (
              <tr key={u.id}>
                <td>#{u.id}</td>
                <td>{u.full_name}</td>
                <td>{u.email ?? '—'}</td>
                <td>{u.phone ?? '—'}</td>
                <td>{u.national_id ?? '—'}</td>
                <td>
                  <span className={`badge ${u.is_active ? 'verified' : 'rejected'}`}>
                    {u.is_active ? 'Active' : 'Disabled'}
                  </span>
                </td>
                <td>{new Date(u.created_at).toLocaleDateString()}</td>
                <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                  <button className="ghost" onClick={() => toggleActive(u)} disabled={busyId === u.id}>
                    {u.is_active ? 'Disable' : 'Enable'}
                  </button>
                  <button className="ghost" style={{ marginLeft: 8 }} onClick={() => remove(u)} disabled={busyId === u.id}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} style={{ color: 'var(--muted)' }}>
                  {loading ? 'Loading...' : query ? 'No matching citizens.' : 'No citizens registered.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
