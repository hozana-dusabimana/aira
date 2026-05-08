import { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { analytics, incidents as incidentsApi, system } from '../services/api';
import type { ComponentHealth, ComponentStatus, HealthResponse } from '../services/api';
import { realtime } from '../services/realtime';

type WsState = 'connecting' | 'open' | 'closed';

interface ProbePoint {
  t: number;
  latency: number | null;
  status: ComponentStatus;
}

const HISTORY_MAX = 30;

const COMPONENT_META: Record<string, { label: string; icon: string; description: string }> = {
  database: {
    label: 'MySQL Database',
    icon: '🗄️',
    description: 'Primary data store for users, incidents and audit log',
  },
  redis: {
    label: 'Redis Cache & Broker',
    icon: '⚡',
    description: 'Rate-limit store and Celery broker / result backend',
  },
  celery: {
    label: 'Background Workers',
    icon: '⚙️',
    description: 'Celery workers for AI analysis, push, email',
  },
  websocket: {
    label: 'Realtime Broadcaster',
    icon: '📡',
    description: 'WebSocket fan-out for staff, citizens and incident threads',
  },
  storage: {
    label: 'Upload Storage',
    icon: '🗂️',
    description: 'Volume backing image and evidence uploads',
  },
};

function statusLabel(s: ComponentStatus): string {
  switch (s) {
    case 'ok':
      return 'Operational';
    case 'degraded':
      return 'Degraded';
    case 'down':
      return 'Outage';
    default:
      return 'Unknown';
  }
}

function formatUptime(seconds: number): string {
  if (!seconds || seconds < 0) return '—';
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const mins = Math.floor((seconds % 3_600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

function timeAgo(iso: string | null): string {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function SystemStatusPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [history, setHistory] = useState<ProbePoint[]>([]);
  const [wsState, setWsState] = useState<WsState>('connecting');
  const [pending, setPending] = useState<number | null>(null);
  const [activeIncidents, setActiveIncidents] = useState<number | null>(null);
  const [lastIncidentAt, setLastIncidentAt] = useState<string | null>(null);
  const [, setTick] = useState(0);

  async function probe() {
    setRefreshing(true);
    const startedAt = performance.now();
    try {
      const data = await system.healthDetailed();
      const elapsed = performance.now() - startedAt;
      setHealth(data);
      setError(null);
      setHistory((prev) => {
        const next: ProbePoint = {
          t: Date.now(),
          latency: Math.round(elapsed),
          status: data.status === 'ok' ? 'ok' : (data.status as ComponentStatus),
        };
        return [...prev, next].slice(-HISTORY_MAX);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Health check failed');
      setHealth(null);
      setHistory((prev) => {
        const next: ProbePoint = { t: Date.now(), latency: null, status: 'down' };
        return [...prev, next].slice(-HISTORY_MAX);
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function loadStats() {
    try {
      const [overview, latest] = await Promise.all([
        analytics.overview().catch(() => null),
        incidentsApi.list({ limit: 1 }).catch(() => []),
      ]);
      if (overview) {
        setPending(overview.pending);
        setActiveIncidents(overview.pending + overview.in_progress);
      }
      if (latest.length > 0) setLastIncidentAt(latest[0].created_at);
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    probe();
    loadStats();
    const probeT = setInterval(probe, 15_000);
    const statsT = setInterval(loadStats, 60_000);
    const tickT = setInterval(() => setTick((t) => t + 1), 30_000);
    return () => {
      clearInterval(probeT);
      clearInterval(statsT);
      clearInterval(tickT);
    };
  }, []);

  useEffect(() => realtime.subscribeStaffState((s) => setWsState(s)), []);
  useEffect(() => realtime.subscribeStaff(() => loadStats()), []);

  const components = health?.components ?? {};
  const overall: ComponentStatus = error
    ? 'down'
    : health?.status === 'ok'
      ? 'ok'
      : 'degraded';

  const uptime = formatUptime(health?.uptime_seconds ?? 0);
  const avgLatency = useMemo(() => {
    const valid = history.map((h) => h.latency).filter((n): n is number => n !== null);
    if (valid.length === 0) return null;
    return Math.round(valid.reduce((a, b) => a + b, 0) / valid.length);
  }, [history]);

  const successRate = useMemo(() => {
    if (history.length === 0) return null;
    const ok = history.filter((h) => h.status === 'ok').length;
    return Math.round((ok / history.length) * 100);
  }, [history]);

  return (
    <div className="status-page">
      <div className={`status-banner status-${overall}`}>
        <div className="status-banner-icon">
          {overall === 'ok' ? '✓' : overall === 'degraded' ? '!' : '×'}
        </div>
        <div className="status-banner-text">
          <strong>
            {overall === 'ok'
              ? 'All systems operational'
              : overall === 'degraded'
                ? 'Some services are degraded'
                : 'Backend unreachable'}
          </strong>
          <span>
            {error
              ? error
              : `Last checked ${health?.checked_at ? timeAgo(health.checked_at) : 'just now'} · auto-refresh every 15s`}
          </span>
        </div>
        <button className="ghost" onClick={probe} disabled={refreshing}>
          {refreshing ? 'Probing...' : 'Probe now'}
        </button>
      </div>

      <div className="status-summary-grid">
        <SummaryStat label="Backend uptime" value={uptime} hint={health?.started_at ? `since ${new Date(health.started_at).toLocaleString()}` : ''} />
        <SummaryStat
          label="Avg probe latency"
          value={avgLatency != null ? `${avgLatency}ms` : '—'}
          hint={`${history.length} probe${history.length === 1 ? '' : 's'} in window`}
        />
        <SummaryStat
          label="Success rate"
          value={successRate != null ? `${successRate}%` : '—'}
          hint="Recent probe history"
        />
        <SummaryStat
          label="Active incidents"
          value={activeIncidents != null ? String(activeIncidents) : '—'}
          hint={pending != null ? `${pending} pending` : ''}
        />
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h3>Probe latency</h3>
            <span className="card-sub">Round-trip time of /health (last {HISTORY_MAX} samples)</span>
          </div>
        </div>
        {history.length === 0 ? (
          <div className="empty-chart">
            <span>Collecting samples...</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart
              data={history.map((h) => ({
                time: new Date(h.t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
                latency: h.latency,
              }))}
              margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
            >
              <defs>
                <linearGradient id="latencyFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#94a3b8' }}
                formatter={(v) => [`${v} ms`, 'Latency']}
              />
              <Area type="monotone" dataKey="latency" stroke="#10b981" strokeWidth={2} fill="url(#latencyFill)" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="services-grid">
        <ServiceCard
          name="API Server"
          icon="🌐"
          description="FastAPI HTTP gateway serving /api/v1"
          status={error ? 'down' : 'ok'}
          metrics={[
            health?.version ? { label: 'Version', value: health.version } : null,
            health?.env ? { label: 'Environment', value: health.env } : null,
            avgLatency != null ? { label: 'Latency', value: `${avgLatency}ms` } : null,
          ].filter(Boolean) as { label: string; value: string }[]}
        />

        <ServiceCard
          name="Live Feed (WebSocket)"
          icon="📡"
          description="Browser ↔ server realtime channel for this dashboard"
          status={wsState === 'open' ? 'ok' : wsState === 'connecting' ? 'degraded' : 'down'}
          metrics={[
            { label: 'State', value: wsState },
            components.websocket?.connections != null
              ? { label: 'Active sockets', value: String(components.websocket.connections) }
              : null,
            components.websocket?.topics != null
              ? { label: 'Topics', value: String(components.websocket.topics) }
              : null,
          ].filter(Boolean) as { label: string; value: string }[]}
        />

        {Object.entries(components).map(([key, c]) => {
          if (key === 'websocket') return null; // shown above with WS client state
          const meta = COMPONENT_META[key] ?? { label: key, icon: '🔧', description: '' };
          return (
            <ServiceCard
              key={key}
              name={meta.label}
              icon={meta.icon}
              description={meta.description}
              status={c.status}
              error={c.error}
              metrics={metricsFor(c)}
            />
          );
        })}

        {/* Incident pipeline summary */}
        <ServiceCard
          name="Incident Pipeline"
          icon="🚨"
          description="End-to-end flow from citizen report to officer resolution"
          status={pending !== null ? 'ok' : 'unknown'}
          metrics={[
            pending != null ? { label: 'Pending triage', value: String(pending) } : null,
            activeIncidents != null ? { label: 'Active', value: String(activeIncidents) } : null,
            lastIncidentAt ? { label: 'Last report', value: timeAgo(lastIncidentAt) } : null,
          ].filter(Boolean) as { label: string; value: string }[]}
        />
      </div>

      {loading && (
        <p style={{ color: 'var(--muted)', fontSize: 13, textAlign: 'center' }}>
          Running first probe...
        </p>
      )}
    </div>
  );
}

function metricsFor(c: ComponentHealth): { label: string; value: string }[] {
  const out: { label: string; value: string }[] = [];
  if (c.latency_ms != null) out.push({ label: 'Latency', value: `${c.latency_ms}ms` });
  if (c.workers != null) out.push({ label: 'Workers', value: String(c.workers) });
  if (c.files != null) out.push({ label: 'Files', value: String(c.files) });
  return out;
}

function SummaryStat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="summary-stat">
      <span className="summary-stat-label">{label}</span>
      <strong>{value}</strong>
      {hint && <span className="summary-stat-hint">{hint}</span>}
    </div>
  );
}

function ServiceCard({
  name,
  icon,
  description,
  status,
  metrics,
  error,
}: {
  name: string;
  icon: string;
  description: string;
  status: ComponentStatus;
  metrics: { label: string; value: string }[];
  error?: string;
}) {
  return (
    <div className={`service-card service-${status}`}>
      <div className="service-card-head">
        <span className="service-icon">{icon}</span>
        <div className="service-title">
          <strong>{name}</strong>
          <span>{description}</span>
        </div>
        <span className={`service-pill service-pill-${status}`}>{statusLabel(status)}</span>
      </div>
      {metrics.length > 0 && (
        <div className="service-metrics">
          {metrics.map((m) => (
            <div key={m.label}>
              <span>{m.label}</span>
              <strong>{m.value}</strong>
            </div>
          ))}
        </div>
      )}
      {error && <div className="alert alert-error" style={{ marginTop: 12 }}>{error}</div>}
    </div>
  );
}
