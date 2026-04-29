import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SeverityBadge, StatusBadge } from '../components/incidents/StatusBadge';
import { incidents as incidentsApi } from '../services/api';
import type { Incident, IncidentStatus } from '../types';

const STATUSES: (IncidentStatus | '')[] = [
  '', 'pending', 'analyzing', 'verified', 'assigned', 'in_progress', 'resolved', 'rejected',
];

export default function IncidentsList() {
  const navigate = useNavigate();
  const [list, setList] = useState<Incident[]>([]);
  const [statusFilter, setStatusFilter] = useState<IncidentStatus | ''>('');
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await incidentsApi.list({
        status: statusFilter || undefined,
        limit: 100,
      });
      setList(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [statusFilter]);

  return (
    <div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <strong>Filter:</strong>
          <select
            style={{ width: 220 }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as IncidentStatus | '')}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s ? s.replace('_', ' ') : 'All statuses'}</option>
            ))}
          </select>
          <button className="ghost" onClick={load} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th><th>Type</th><th>Severity</th><th>Status</th>
              <th>Reporter</th><th>Location</th><th>Created</th>
            </tr>
          </thead>
          <tbody>
            {list.map((i) => (
              <tr key={i.id} onClick={() => navigate(`/incidents/${i.id}`)}>
                <td>#{i.id}</td>
                <td>{i.incident_type ?? '—'}</td>
                <td><SeverityBadge severity={i.severity_level} /></td>
                <td><StatusBadge status={i.status} /></td>
                <td>#{i.reporter_id}</td>
                <td>
                  {i.latitude && i.longitude
                    ? `${Number(i.latitude).toFixed(4)}, ${Number(i.longitude).toFixed(4)}`
                    : '—'}
                </td>
                <td>{new Date(i.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {list.length === 0 && (
              <tr>
                <td colSpan={7} style={{ color: 'var(--muted)' }}>No incidents.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
