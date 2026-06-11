import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Label,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { SeverityBadge, StatusBadge } from '../components/incidents/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { analytics, incidents as incidentsApi } from '../services/api';
import { realtime } from '../services/realtime';
import type { CountByLabel, Incident, OverviewMetrics, TimelinePoint } from '../types';

const PIE_COLORS = ['#2563eb', '#10b981', '#f59e0b', '#f97316', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'];

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

function formatTime(iso: string): string {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const min = Math.floor(diff / 60_000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  return d.toLocaleDateString();
}

export default function Dashboard() {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [latest, setLatest] = useState<Incident[]>([]);
  const [byType, setByType] = useState<CountByLabel[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  async function loadAll() {
    setRefreshing(true);
    try {
      const [m, l, t, tl] = await Promise.all([
        analytics.overview().catch(() => null),
        incidentsApi.list({ limit: 8 }).catch(() => []),
        analytics.byType().catch(() => []),
        analytics.timeline(14).catch(() => []),
      ]);
      if (m) setMetrics(m);
      setLatest(l);
      setByType(t);
      setTimeline(tl);
      setLastUpdated(new Date());
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  // Live refresh via WebSocket
  useEffect(() => {
    const unsub = realtime.subscribeStaff(() => loadAll());
    return unsub;
  }, []);

  const severityCounts = useMemo(() => {
    const counts = { low: 0, medium: 0, high: 0, critical: 0 };
    latest.forEach((i) => {
      counts[i.severity_level] = (counts[i.severity_level] ?? 0) + 1;
    });
    return counts;
  }, [latest]);

  const totalActive = (metrics?.pending ?? 0) + (metrics?.in_progress ?? 0);
  const resolutionRate =
    metrics && metrics.total_reports > 0
      ? Math.round((metrics.resolved / metrics.total_reports) * 100)
      : 0;

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 18) return 'Good afternoon';
    return 'Good evening';
  })();

  return (
    <div className="dashboard">
      <div className="dashboard-hero">
        <div>
          <h1>
            {greeting}, {user?.full_name?.split(' ')[0] ?? 'Officer'}.
          </h1>
          <p>
            {totalActive > 0
              ? `${totalActive} active incident${totalActive === 1 ? '' : 's'} need attention.`
              : 'No active incidents right now. Stay safe.'}
          </p>
        </div>
        <div className="dashboard-hero-actions">
          <span className="updated-label">
            Updated {formatTime(lastUpdated.toISOString())}
          </span>
          <button className="ghost" onClick={loadAll} disabled={refreshing}>
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <Link to="/incidents" className="btn-primary">
            View incidents
          </Link>
        </div>
      </div>

      <div className="kpi-grid">
        <KPI
          label="Total reports"
          value={metrics?.total_reports ?? '—'}
          icon="📊"
          tone="blue"
          hint="All-time"
        />
        <KPI
          label="Pending"
          value={metrics?.pending ?? '—'}
          icon="⏳"
          tone="yellow"
          hint="Awaiting triage"
        />
        <KPI
          label="In progress"
          value={metrics?.in_progress ?? '—'}
          icon="🚓"
          tone="orange"
          hint="Officers responding"
        />
        <KPI
          label="Resolved"
          value={metrics?.resolved ?? '—'}
          icon="✅"
          tone="green"
          hint={`${resolutionRate}% resolution rate`}
        />
        <KPI
          label="Avg response"
          value={metrics?.average_response_minutes != null ? formatDuration(metrics.average_response_minutes) : '—'}
          icon="⚡"
          tone="purple"
          hint="Time to first action"
        />
      </div>

      <div className="dashboard-grid">
        <div className="card chart-card">
          <div className="card-head">
            <div>
              <h3>Reports trend</h3>
              <span className="card-sub">Last 14 days</span>
            </div>
          </div>
          {timeline.length === 0 ? (
            <EmptyChart label="No data yet." />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={timeline} margin={{ top: 10, right: 10, left: 4, bottom: 20 }}>
                <defs>
                  <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563eb" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2a3d" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={12}>
                  <Label value="Date" position="insideBottom" offset={-12} fill="#64748b" fontSize={12} />
                </XAxis>
                <YAxis stroke="#64748b" fontSize={12} allowDecimals={false}>
                  <Label value="Number of reports" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} fill="#64748b" fontSize={12} />
                </YAxis>
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fill="url(#trendFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card chart-card">
          <div className="card-head">
            <div>
              <h3>By incident type</h3>
              <span className="card-sub">Distribution</span>
            </div>
          </div>
          {byType.length === 0 ? (
            <EmptyChart label="No data yet." />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={byType}
                  dataKey="count"
                  nameKey="label"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {byType.map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card severity-card">
          <div className="card-head">
            <div>
              <h3>Severity snapshot</h3>
              <span className="card-sub">Latest 8 incidents</span>
            </div>
          </div>
          <div className="severity-bars">
            {(['critical', 'high', 'medium', 'low'] as const).map((sev) => {
              const count = severityCounts[sev];
              const max = Math.max(...Object.values(severityCounts), 1);
              const pct = (count / max) * 100;
              return (
                <div key={sev} className="severity-row">
                  <SeverityBadge severity={sev} />
                  <div className="severity-track">
                    <div className={`severity-fill ${sev}`} style={{ width: `${pct}%` }} />
                  </div>
                  <span className="severity-count">{count}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="card quick-card">
          <div className="card-head">
            <div>
              <h3>Quick actions</h3>
              <span className="card-sub">Jump to common tasks</span>
            </div>
          </div>
          <div className="quick-grid">
            <Link to="/incidents?status=pending" className="quick-action">
              <span className="quick-icon yellow">⏳</span>
              <div>
                <strong>Triage pending</strong>
                <span>Review unassigned reports</span>
              </div>
            </Link>
            <Link to="/map" className="quick-action">
              <span className="quick-icon blue">🗺️</span>
              <div>
                <strong>Live map</strong>
                <span>See incidents on the map</span>
              </div>
            </Link>
            <Link to="/analytics" className="quick-action">
              <span className="quick-icon green">📈</span>
              <div>
                <strong>Analytics</strong>
                <span>Trends & insights</span>
              </div>
            </Link>
            {user?.role === 'admin' && (
              <Link to="/officers" className="quick-action">
                <span className="quick-icon purple">👮</span>
                <div>
                  <strong>Manage officers</strong>
                  <span>Add or update accounts</span>
                </div>
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h3>Latest reports</h3>
            <span className="card-sub">Live feed of the most recent incidents</span>
          </div>
          <Link to="/incidents" className="link-cta">View all →</Link>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Reported</th>
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
                  <td>{formatTime(i.created_at)}</td>
                </tr>
              ))}
              {latest.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ color: 'var(--muted)', textAlign: 'center', padding: 32 }}>
                    No incidents yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function KPI({
  label,
  value,
  icon,
  tone,
  hint,
}: {
  label: string;
  value: number | string;
  icon: string;
  tone: 'blue' | 'yellow' | 'orange' | 'green' | 'purple';
  hint?: string;
}) {
  return (
    <div className={`kpi-card kpi-${tone}`}>
      <div className="kpi-icon">{icon}</div>
      <div className="kpi-body">
        <div className="kpi-label">{label}</div>
        <div className="kpi-value">{value}</div>
        {hint && <div className="kpi-hint">{hint}</div>}
      </div>
    </div>
  );
}

function EmptyChart({ label }: { label: string }) {
  return (
    <div className="empty-chart">
      <span>{label}</span>
    </div>
  );
}
