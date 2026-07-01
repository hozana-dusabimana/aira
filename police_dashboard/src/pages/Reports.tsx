import { useRef, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import { reports } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { IncidentStatus, ReportSummary } from '../types';

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#f97316'];
const SEVERITY_COLORS: Record<string, string> = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#f97316',
  critical: '#ef4444',
};

type PresetKey = 'week' | 'month' | 'resolved' | 'pending' | 'custom';

interface Preset {
  key: PresetKey;
  label: string;
  /** days back from today; null means "use custom range inputs" */
  days: number | null;
  status?: IncidentStatus;
}

const PRESETS: Preset[] = [
  { key: 'week', label: 'Incidents — last 7 days', days: 7 },
  { key: 'month', label: 'Incidents — last 30 days', days: 30 },
  { key: 'resolved', label: 'Resolved incidents (30 days)', days: 30, status: 'resolved' },
  { key: 'pending', label: 'Pending incidents (30 days)', days: 30, status: 'pending' },
  { key: 'custom', label: 'Custom range…', days: null },
];

function isoDay(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n + 1);
  return isoDay(d);
}

function fmtDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

const STATUS_OPTIONS: IncidentStatus[] = [
  'pending', 'analyzing', 'verified', 'assigned', 'in_progress', 'resolved', 'rejected',
];

export default function Reports() {
  const { user } = useAuth();
  const [preset, setPreset] = useState<PresetKey>('week');
  const [start, setStart] = useState(daysAgo(7));
  const [end, setEnd] = useState(isoDay(new Date()));
  const [customStatus, setCustomStatus] = useState<IncidentStatus | ''>('');
  const [data, setData] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const paperRef = useRef<HTMLDivElement>(null);

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const def = PRESETS.find((p) => p.key === preset)!;
      const params =
        preset === 'custom'
          ? { start_date: start, end_date: end, status: customStatus || undefined }
          : { start_date: daysAgo(def.days!), end_date: isoDay(new Date()), status: def.status };
      const result = await reports.summary(params);
      setData(result);
    } catch (e) {
      setError('Could not generate the report. Please try again.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  async function exportPdf() {
    if (!paperRef.current || !data) return;
    setExporting(true);
    try {
      const canvas = await html2canvas(paperRef.current, {
        scale: 2,
        backgroundColor: '#ffffff',
        useCORS: true,
      });
      const img = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pageW = pdf.internal.pageSize.getWidth();
      const pageH = pdf.internal.pageSize.getHeight();
      const imgH = (canvas.height * pageW) / canvas.width;
      let heightLeft = imgH;
      let position = 0;
      pdf.addImage(img, 'PNG', 0, position, pageW, imgH);
      heightLeft -= pageH;
      while (heightLeft > 0) {
        position -= pageH;
        pdf.addPage();
        pdf.addImage(img, 'PNG', 0, position, pageW, imgH);
        heightLeft -= pageH;
      }
      pdf.save(`aira-report-${data.start_date}_to_${data.end_date}.pdf`);
    } finally {
      setExporting(false);
    }
  }

  const kpis = data
    ? [
        { label: 'Total incidents', value: data.total, color: '#0f172a' },
        { label: 'Resolved', value: data.resolved, color: '#10b981' },
        { label: 'Pending', value: data.pending, color: '#f59e0b' },
        { label: 'In progress', value: data.in_progress, color: '#2563eb' },
        { label: 'Resolution rate', value: `${data.resolution_rate}%`, color: '#8b5cf6' },
        {
          label: 'Avg response',
          value: data.average_response_minutes != null ? `${data.average_response_minutes} min` : '—',
          color: '#ef4444',
        },
      ]
    : [];

  return (
    <div>
      {/* ---- Controls ---- */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ marginTop: 0 }}>Generate report</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 220 }}>
            <span className="metric-label">Report type</span>
            <select value={preset} onChange={(e) => setPreset(e.target.value as PresetKey)}>
              {PRESETS.map((p) => (
                <option key={p.key} value={p.key}>{p.label}</option>
              ))}
            </select>
          </label>

          {preset === 'custom' && (
            <>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span className="metric-label">From</span>
                <input type="date" value={start} max={end} onChange={(e) => setStart(e.target.value)} />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span className="metric-label">To</span>
                <input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 160 }}>
                <span className="metric-label">Status</span>
                <select
                  value={customStatus}
                  onChange={(e) => setCustomStatus(e.target.value as IncidentStatus | '')}
                >
                  <option value="">All statuses</option>
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>{s.replace('_', ' ')}</option>
                  ))}
                </select>
              </label>
            </>
          )}

          <button className="btn-primary" onClick={generate} disabled={loading}>
            {loading ? 'Generating…' : 'Generate'}
          </button>
          {data && (
            <button className="ghost" onClick={exportPdf} disabled={exporting}>
              {exporting ? 'Exporting…' : '⬇ Export PDF'}
            </button>
          )}
        </div>
        {error && <p style={{ color: 'var(--red)', marginBottom: 0 }}>{error}</p>}
      </div>

      {!data && !loading && (
        <div className="card" style={{ color: 'var(--muted)' }}>
          Choose a report type and click <strong>Generate</strong> to build a report. You can then
          export it as a PDF.
        </div>
      )}

      {/* ---- Report document (also the PDF capture target) ---- */}
      {data && (
        <div className="report-paper" ref={paperRef}>
          <div className="report-head">
            <div>
              <div className="report-brand">AIRA · Rwanda National Police</div>
              <h1>{data.title}</h1>
              <p className="report-meta">
                Generated {fmtDateTime(data.generated_at)} by {user?.full_name ?? 'officer'}
                {data.status_filter ? ` · status: ${data.status_filter.replace('_', ' ')}` : ''}
              </p>
            </div>
            <div className="report-logo">A</div>
          </div>

          <div className="report-kpis">
            {kpis.map((k) => (
              <div key={k.label} className="report-kpi">
                <div className="report-kpi-value" style={{ color: k.color }}>{k.value}</div>
                <div className="report-kpi-label">{k.label}</div>
              </div>
            ))}
          </div>

          <div className="report-charts">
            <div className="report-chart">
              <h3>Incidents by type</h3>
              {data.by_type.length === 0 ? (
                <p className="report-empty">No data in this range.</p>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={data.by_type} dataKey="count" nameKey="label" outerRadius={80} label>
                      {data.by_type.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="report-chart">
              <h3>Incidents by severity</h3>
              {data.by_severity.length === 0 ? (
                <p className="report-empty">No data in this range.</p>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={data.by_severity} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="label" stroke="#64748b" />
                    <YAxis stroke="#64748b" allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count">
                      {data.by_severity.map((s, i) => (
                        <Cell key={i} fill={SEVERITY_COLORS[s.label] ?? '#2563eb'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className="report-chart" style={{ marginBottom: 20 }}>
            <h3>Daily volume</h3>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data.timeline} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" stroke="#64748b" />
                <YAxis stroke="#64748b" allowDecimals={false} />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#2563eb" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <h3 className="report-table-title">Incident details ({data.rows.length})</h3>
          {data.rows.length === 0 ? (
            <p className="report-empty">No incidents matched this report.</p>
          ) : (
            <table className="report-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Reported</th>
                  <th>Type</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Response</th>
                  <th>Location</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{fmtDateTime(row.created_at)}</td>
                    <td>{row.incident_type ?? '—'}</td>
                    <td>{row.severity}</td>
                    <td>{row.status.replace('_', ' ')}</td>
                    <td>{row.response_minutes != null ? `${row.response_minutes} min` : '—'}</td>
                    <td>{row.location ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div className="report-footer">
            AIRA — AI-Powered Road Accident Reporting Assistant · Confidential · Generated for internal police use.
          </div>
        </div>
      )}
    </div>
  );
}
