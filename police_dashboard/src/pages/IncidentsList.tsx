import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Pagination from '../components/common/Pagination';
import { SeverityBadge, StatusBadge } from '../components/incidents/StatusBadge';
import { incidents as incidentsApi } from '../services/api';
import { realtime } from '../services/realtime';
import type { Incident, IncidentStatus } from '../types';
import { incidentTypeLabel } from '../utils/incident';

// 'rejected' reports are spam and live on the dedicated Spam page, not here.
const STATUSES: (IncidentStatus | '')[] = [
  '', 'pending', 'analyzing', 'verified', 'assigned', 'in_progress', 'resolved',
];

const PAGE_SIZE = 15;

export default function IncidentsList() {
  const navigate = useNavigate();
  const [list, setList] = useState<Incident[]>([]);
  const [statusFilter, setStatusFilter] = useState<IncidentStatus | ''>('');
  const [loading, setLoading] = useState(false);
  const [liveBadge, setLiveBadge] = useState<string | null>(null);
  const [page, setPage] = useState(1);

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
    setPage(1);
  }, [statusFilter]);

  const pageItems = list.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  useEffect(() => {
    const unsub = realtime.subscribeStaff((evt) => {
      const data = evt.data as Partial<Incident> & { id: number };
      setList((prev) => {
        if (evt.event === 'incident.created') {
          if (statusFilter && data.status && data.status !== statusFilter) return prev;
          if (prev.some((i) => i.id === data.id)) return prev;
          return [data as Incident, ...prev];
        }
        if (
          evt.event === 'incident.status_changed' ||
          evt.event === 'incident.analyzed' ||
          evt.event === 'incident.assigned'
        ) {
          return prev.map((i) =>
            i.id === data.id ? { ...i, ...(data as Partial<Incident>) } : i,
          );
        }
        return prev;
      });
      setLiveBadge(`live: ${evt.event} #${data.id}`);
      window.setTimeout(() => setLiveBadge(null), 2500);
    });
    return unsub;
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
          {liveBadge && (
            <span style={{ marginLeft: 'auto', color: '#22c55e', fontSize: 12 }}>
              ● {liveBadge}
            </span>
          )}
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
            {pageItems.map((i) => (
              <tr key={i.id} onClick={() => navigate(`/incidents/${i.id}`)}>
                <td>#{i.id}</td>
                <td>{incidentTypeLabel(i.incident_type)}</td>
                <td><SeverityBadge severity={i.severity_level} /></td>
                <td><StatusBadge status={i.status} /></td>
                <td>{i.reporter?.full_name ?? `#${i.reporter_id}`}</td>
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
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={list.length}
          onPageChange={setPage}
          label="incidents"
        />
      </div>
    </div>
  );
}
