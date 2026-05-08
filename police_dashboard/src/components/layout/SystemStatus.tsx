import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { analytics, incidents as incidentsApi, system } from '../../services/api';
import { realtime } from '../../services/realtime';

type ApiState = 'checking' | 'ok' | 'down';
type WsState = 'connecting' | 'open' | 'closed';

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function SystemStatus() {
  const [apiState, setApiState] = useState<ApiState>('checking');
  const [wsState, setWsState] = useState<WsState>('connecting');
  const [pending, setPending] = useState<number | null>(null);
  const [lastIncidentAt, setLastIncidentAt] = useState<string | null>(null);
  const [, setTick] = useState(0);

  async function probe() {
    try {
      await system.health();
      setApiState('ok');
    } catch {
      setApiState('down');
    }
  }

  async function loadStats() {
    try {
      const [overview, latest] = await Promise.all([
        analytics.overview().catch(() => null),
        incidentsApi.list({ limit: 1 }).catch(() => []),
      ]);
      if (overview) setPending(overview.pending);
      if (latest.length > 0) setLastIncidentAt(latest[0].created_at);
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    probe();
    loadStats();
    const probeT = setInterval(probe, 30_000);
    const statsT = setInterval(loadStats, 60_000);
    const tickT = setInterval(() => setTick((t) => t + 1), 30_000);
    return () => {
      clearInterval(probeT);
      clearInterval(statsT);
      clearInterval(tickT);
    };
  }, []);

  useEffect(() => {
    return realtime.subscribeStaffState((s) => setWsState(s));
  }, []);

  // Refresh stats when a new staff event arrives
  useEffect(() => {
    return realtime.subscribeStaff(() => loadStats());
  }, []);

  // Aggregate state: red if API down; yellow if API ok but WS not open; green if both up.
  const overall: 'green' | 'yellow' | 'red' =
    apiState === 'down'
      ? 'red'
      : wsState === 'open'
        ? 'green'
        : apiState === 'ok'
          ? 'yellow'
          : 'yellow';

  const headline =
    overall === 'green'
      ? 'All systems online'
      : overall === 'yellow'
        ? apiState === 'ok'
          ? 'Live feed reconnecting'
          : 'Checking services...'
        : 'Backend unreachable';

  const subline = (() => {
    if (overall === 'red') return 'Retrying connection...';
    const parts: string[] = [];
    if (pending !== null) parts.push(`${pending} pending`);
    if (lastIncidentAt) parts.push(`last ${timeAgo(lastIncidentAt)}`);
    return parts.length > 0 ? parts.join(' · ') : 'Awaiting first report';
  })();

  return (
    <Link
      to="/status"
      className={`sys-status sys-${overall}`}
      title={`API: ${apiState} · Live feed: ${wsState} · Click for details`}
    >
      <span className="sys-dot" />
      <div className="sys-body">
        <strong>{headline}</strong>
        <span>{subline}</span>
      </div>
      <span className="sys-arrow" aria-hidden>→</span>
    </Link>
  );
}
