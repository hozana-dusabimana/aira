import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { StatusBadge, SeverityBadge } from '../components/incidents/StatusBadge';
import { analytics, incidents as incidentsApi } from '../services/api';
import type { CountByLabel, Incident, OverviewMetrics, TimelinePoint } from '../types';

export default function Dashboard() {
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [latest, setLatest] = useState<Incident[]>([]);
  const [byType, setByType] = useState<CountByLabel[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);

  useEffect(() => {
    analytics.overview().then(setMetrics).catch(() => {});
    incidentsApi.list({ limit: 8 }).then(setLatest).catch(() => {});
    analytics.byType().then(setByType).catch(() => {});
    analytics.timeline(14).then(setTimeline).catch(() => {});
  }, []);

  return (
    <div>
      <div className="grid-cards">
        <div className="card">
          <div className="metric-label">Total reports</div>
          <div className="metric">{metrics?.total_reports ?? '—'}</div>
        </div>
        <div className="card">
          <div className="metric-label">Pending</div>
          <div className="metric" style={{ color: 'var(--yellow)' }}>{metrics?.pending ?? '—'}</div>
        </div>
        <div className="card">
          <div className="metric-label">In progress</div>
          <div className="metric" style={{ color: 'var(--orange)' }}>{metrics?.in_progress ?? '—'}</div>
        </div>
        <div className="card">
          <div className="metric-label">Resolved</div>
          <div className="metric" style={{ color: 'var(--green)' }}>{metrics?.resolved ?? '—'}</div>
        </div>
        <div className="card">
          <div className="metric-label">Avg response (min)</div>
          <div className="metric">{metrics?.average_response_minutes ?? '—'}</div>
        </div>
      </div>

      <div className="detail-grid" style={{ marginBottom: 24 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Incidents by type</h3>
          {byType.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>No data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={byType}>
                <XAxis dataKey="label" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                <Bar dataKey="count" fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Last 14 days</h3>
          {timeline.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>No data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={timeline}>
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                <Bar dataKey="count" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Latest reports</h3>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th><th>Type</th><th>Severity</th><th>Status</th><th>Reported</th>
            </tr>
          </thead>
          <tbody>
            {latest.map((i) => (
              <tr
                key={i.id}
                onClick={() => (window.location.href = `/incidents/${i.id}`)}
              >
                <td>#{i.id}</td>
                <td>{i.incident_type ?? '—'}</td>
                <td><SeverityBadge severity={i.severity_level} /></td>
                <td><StatusBadge status={i.status} /></td>
                <td>{new Date(i.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {latest.length === 0 && (
              <tr><td colSpan={5} style={{ color: 'var(--muted)' }}>No incidents yet.</td></tr>
            )}
          </tbody>
        </table>
        <Link to="/incidents" style={{ display: 'inline-block', marginTop: 12 }}>
          View all incidents →
        </Link>
      </div>
    </div>
  );
}
