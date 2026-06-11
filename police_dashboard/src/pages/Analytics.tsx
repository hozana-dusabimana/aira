import { useEffect, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Label, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { analytics } from '../services/api';
import type { CountByLabel, OverviewMetrics, TimelinePoint } from '../types';

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#f97316'];

function formatDuration(minutes: number): string {
  if (minutes < 1) return '<1m';
  if (minutes < 60) return `${Math.round(minutes)}m`;
  const hours = minutes / 60;
  if (hours < 24) return `${Math.round(hours * 10) / 10}h`;
  const days = hours / 24;
  if (days < 30) return `${Math.round(days * 10) / 10}d`;
  const months = days / 30;
  if (months < 12) return `${Math.round(months * 10) / 10}mo`;
  return `${Math.round((months / 12) * 10) / 10}y`;
}

export default function Analytics() {
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [byType, setByType] = useState<CountByLabel[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);

  useEffect(() => {
    analytics.overview().then(setMetrics);
    analytics.byType().then(setByType);
    analytics.timeline(30).then(setTimeline);
  }, []);

  return (
    <div>
      <div className="grid-cards">
        <div className="card">
          <div className="metric-label">Total reports</div>
          <div className="metric">{metrics?.total_reports ?? '—'}</div>
        </div>
        <div className="card">
          <div className="metric-label">Avg response time</div>
          <div className="metric">{metrics?.average_response_minutes != null ? formatDuration(metrics.average_response_minutes) : '—'}</div>
        </div>
        <div className="card">
          <div className="metric-label">Pending</div>
          <div className="metric" style={{ color: 'var(--yellow)' }}>{metrics?.pending ?? 0}</div>
        </div>
        <div className="card">
          <div className="metric-label">Resolved</div>
          <div className="metric" style={{ color: 'var(--green)' }}>{metrics?.resolved ?? 0}</div>
        </div>
      </div>

      <div className="detail-grid" style={{ marginBottom: 24 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Distribution by type</h3>
          {byType.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>No data.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={byType} dataKey="count" nameKey="label" outerRadius={90}>
                  {byType.map((_, idx) => (
                    <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Counts by type</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={byType} margin={{ top: 8, right: 16, bottom: 40, left: 28 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="label" stroke="#94a3b8">
                <Label value="Incident type" position="insideBottom" offset={-16} fill="#94a3b8" />
              </XAxis>
              <YAxis stroke="#94a3b8" allowDecimals={false}>
                <Label value="Number of reports" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} fill="#94a3b8" />
              </YAxis>
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
              <Bar dataKey="count" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Reports — last 30 days</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={timeline} margin={{ top: 8, right: 16, bottom: 40, left: 28 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" stroke="#94a3b8">
              <Label value="Date" position="insideBottom" offset={-16} fill="#94a3b8" />
            </XAxis>
            <YAxis stroke="#94a3b8" allowDecimals={false}>
              <Label value="Number of reports" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} fill="#94a3b8" />
            </YAxis>
            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
            <Line type="monotone" dataKey="count" stroke="#10b981" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
