/**
 * Real-time WebSocket client for the dashboard.
 *
 * Auto-reconnects with exponential backoff. Pushes parsed events into per-stream
 * subscriber lists. Token is read fresh on every (re)connect so refreshed tokens
 * are picked up automatically.
 */

const TOKEN_KEY = 'aira_access_token';

const WS_BASE_URL =
  (import.meta.env.VITE_WS_BASE_URL as string | undefined) ?? deriveWsBase();

function deriveWsBase(): string {
  const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1';
  if (apiBase.startsWith('http://') || apiBase.startsWith('https://')) {
    const u = new URL(apiBase);
    const proto = u.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${u.host}/ws`;
  }
  // Same-origin
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/ws`;
}

export interface RealtimeEvent<T = unknown> {
  event: string;
  topic: string;
  data: T;
}

type Listener = (e: RealtimeEvent) => void;

interface Stream {
  url: () => string;
  ws: WebSocket | null;
  listeners: Set<Listener>;
  retry: number;
  closed: boolean;
}

const streams: Record<string, Stream> = {};

function buildUrl(path: string): string {
  const token = localStorage.getItem(TOKEN_KEY) ?? '';
  return `${WS_BASE_URL}${path}?token=${encodeURIComponent(token)}`;
}

function ensureStream(key: string, path: string): Stream {
  if (streams[key]) return streams[key];
  const stream: Stream = {
    url: () => buildUrl(path),
    ws: null,
    listeners: new Set(),
    retry: 0,
    closed: false,
  };
  streams[key] = stream;
  connect(key);
  return stream;
}

function connect(key: string) {
  const stream = streams[key];
  if (!stream || stream.closed) return;

  try {
    const ws = new WebSocket(stream.url());
    stream.ws = ws;

    ws.onopen = () => {
      stream.retry = 0;
    };
    ws.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(ev.data) as RealtimeEvent;
        stream.listeners.forEach((l) => {
          try {
            l(parsed);
          } catch (err) {
            console.error('realtime listener threw', err);
          }
        });
      } catch {
        // ignore malformed
      }
    };
    ws.onclose = () => {
      stream.ws = null;
      if (stream.closed) return;
      const delay = Math.min(30_000, 500 * 2 ** stream.retry);
      stream.retry = Math.min(stream.retry + 1, 6);
      setTimeout(() => connect(key), delay);
    };
    ws.onerror = () => {
      // onclose will fire next; nothing to do here
    };
  } catch (err) {
    console.error('WS connect failed', err);
  }
}

export const realtime = {
  subscribeStaff(listener: Listener): () => void {
    const stream = ensureStream('staff', '/staff');
    stream.listeners.add(listener);
    return () => stream.listeners.delete(listener);
  },

  subscribeIncident(incidentId: number, listener: Listener): () => void {
    const key = `incident:${incidentId}`;
    const stream = ensureStream(key, `/incidents/${incidentId}`);
    stream.listeners.add(listener);
    return () => {
      stream.listeners.delete(listener);
      // If no listeners left, close the per-incident stream.
      if (stream.listeners.size === 0) {
        stream.closed = true;
        stream.ws?.close();
        delete streams[key];
      }
    };
  },

  disconnectAll() {
    for (const key of Object.keys(streams)) {
      const s = streams[key];
      s.closed = true;
      s.ws?.close();
      delete streams[key];
    }
  },
};
