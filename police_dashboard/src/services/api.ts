import axios from 'axios';
import type {
  AuthResponse,
  CountByLabel,
  Incident,
  IncidentMessage,
  IncidentStatus,
  Notification,
  Officer,
  OverviewMetrics,
  SpamReport,
  Station,
  TimelinePoint,
  User,
} from '../types';

const TOKEN_KEY = 'aira_access_token';
const REFRESH_KEY = 'aira_refresh_token';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const rt = localStorage.getItem(REFRESH_KEY);
  if (!rt) return null;
  try {
    const r = await axios.post<AuthResponse>(`${API_BASE_URL}/auth/refresh`, { refresh_token: rt });
    localStorage.setItem(TOKEN_KEY, r.data.access_token);
    localStorage.setItem(REFRESH_KEY, r.data.refresh_token);
    return r.data.access_token;
  } catch {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      refreshing = refreshing ?? refreshAccessToken();
      const newToken = await refreshing;
      refreshing = null;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  },
);

// --- Auth ----------------------------------------------------
export const auth = {
  login: (email: string, password: string) =>
    api.post<AuthResponse>('/auth/officer/login', { email, password }).then((r) => r.data),
  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
  saveTokens: (a: AuthResponse) => {
    localStorage.setItem(TOKEN_KEY, a.access_token);
    localStorage.setItem(REFRESH_KEY, a.refresh_token);
  },
  me: () => api.get<User>('/users/me').then((r) => r.data),
};

// --- Incidents -----------------------------------------------
export const incidents = {
  list: (params?: { status?: IncidentStatus; incident_type?: string; limit?: number; offset?: number }) =>
    api.get<Incident[]>('/incidents/', { params }).then((r) => r.data),
  get: (id: number) => api.get<Incident>(`/incidents/${id}`).then((r) => r.data),
  updateStatus: (id: number, status: IncidentStatus, note?: string) =>
    api.put<Incident>(`/incidents/${id}/status`, { status, note }).then((r) => r.data),
  assign: (id: number, officer_id: number) =>
    api.post<Incident>(`/incidents/${id}/assign`, { officer_id }).then((r) => r.data),
  remove: (id: number) => api.delete(`/incidents/${id}`).then((r) => r.data),
  messages: (id: number) =>
    api.get<IncidentMessage[]>(`/incidents/${id}/messages`).then((r) => r.data),
  postMessage: (id: number, message: string) =>
    api.post<IncidentMessage>(`/incidents/${id}/messages`, { message }).then((r) => r.data),
};

// --- Spam (rejected reports) ---------------------------------
export const spam = {
  list: (params?: { limit?: number; offset?: number }) =>
    api.get<SpamReport[]>('/spam/', { params }).then((r) => r.data),
  notSpam: (id: number) =>
    api.post<Incident>(`/spam/${id}/not-spam`).then((r) => r.data),
  remove: (id: number) => api.delete(`/spam/${id}`).then((r) => r.data),
  backfill: () =>
    api
      .post<{ created: number; total_rejected: number }>('/spam/backfill')
      .then((r) => r.data),
};

// --- Officers / Stations -------------------------------------
export const officers = {
  list: () => api.get<Officer[]>('/officers/').then((r) => r.data),
  create: (payload: {
    full_name: string;
    email: string;
    phone?: string;
    password: string;
    badge_number: string;
    station_id?: number;
    rank?: string;
    department?: string;
  }) => api.post<Officer>('/officers/', payload).then((r) => r.data),
  stations: () => api.get<Station[]>('/officers/stations').then((r) => r.data),
};

// --- Notifications -------------------------------------------
export const notifications = {
  list: () => api.get<Notification[]>('/notifications/').then((r) => r.data),
  markRead: (id: number) => api.put<Notification>(`/notifications/${id}/read`).then((r) => r.data),
  markAllRead: async () => {
    const all = await api.get<Notification[]>('/notifications/').then((r) => r.data);
    const unread = all.filter((n) => !n.is_read);
    await Promise.all(unread.map((n) => api.put(`/notifications/${n.id}/read`)));
    return unread.length;
  },
};


// --- System health -------------------------------------------
const ROOT_URL = API_BASE_URL.replace(/\/api\/v1\/?$/, '') || '';

/** Resolve a server-relative upload path (e.g. /uploads/...) to a full URL. */
export const mediaUrl = (path?: string): string => (path ? `${ROOT_URL}${path}` : '');

export type ComponentStatus = 'ok' | 'degraded' | 'down' | 'unknown';

export interface ComponentHealth {
  status: ComponentStatus;
  latency_ms?: number;
  workers?: number;
  connections?: number;
  topics?: number;
  files?: number;
  error?: string;
}

export interface HealthResponse {
  status: string;
  app?: string;
  env?: string;
  version?: string;
  uptime_seconds?: number;
  started_at?: string;
  checked_at?: string;
  components?: Record<string, ComponentHealth>;
}

export const system = {
  health: () => axios.get<HealthResponse>(`${ROOT_URL}/health`, { timeout: 5000 }).then((r) => r.data),
  healthDetailed: () =>
    axios.get<HealthResponse>(`${ROOT_URL}/health`, { params: { detailed: true }, timeout: 8000 }).then((r) => r.data),
};

// --- Analytics -----------------------------------------------
export const analytics = {
  overview: () => api.get<OverviewMetrics>('/analytics/overview').then((r) => r.data),
  byType: () => api.get<CountByLabel[]>('/analytics/incidents-by-type').then((r) => r.data),
  byLocation: () =>
    api
      .get<{ latitude: number; longitude: number; count: number }[]>(
        '/analytics/incidents-by-location',
      )
      .then((r) => r.data),
  timeline: (days = 30) =>
    api.get<TimelinePoint[]>('/analytics/incidents-timeline', { params: { days } }).then((r) => r.data),
};
