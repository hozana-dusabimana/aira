import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { SeverityBadge, StatusBadge } from '../components/incidents/StatusBadge';
import { incidents as incidentsApi } from '../services/api';
import { realtime } from '../services/realtime';
import type { Incident, IncidentMessage, IncidentStatus } from '../types';

const NEXT_STATUSES: IncidentStatus[] = [
  'verified', 'assigned', 'in_progress', 'resolved', 'rejected',
];

export default function IncidentDetails() {
  const { id } = useParams();
  const incidentId = Number(id);
  const [incident, setIncident] = useState<Incident | null>(null);
  const [messages, setMessages] = useState<IncidentMessage[]>([]);
  const [reply, setReply] = useState('');
  const [note, setNote] = useState('');

  async function refresh() {
    const data = await incidentsApi.get(incidentId);
    setIncident(data);
    const msgs = await incidentsApi.messages(incidentId);
    setMessages(msgs);
  }

  useEffect(() => {
    if (!isNaN(incidentId)) refresh();
  }, [incidentId]);

  useEffect(() => {
    if (isNaN(incidentId)) return;
    const unsub = realtime.subscribeIncident(incidentId, (evt) => {
      if (evt.event === 'incident.message') {
        setMessages((prev) => {
          const m = evt.data as IncidentMessage;
          if (prev.some((x) => x.id === m.id)) return prev;
          return [...prev, m];
        });
      } else if (
        evt.event === 'incident.status_changed' ||
        evt.event === 'incident.analyzed' ||
        evt.event === 'incident.assigned' ||
        evt.event === 'incident.created'
      ) {
        setIncident((prev) =>
          prev ? { ...prev, ...(evt.data as Partial<Incident>) } : prev,
        );
      }
    });
    return unsub;
  }, [incidentId]);

  async function changeStatus(s: IncidentStatus) {
    await incidentsApi.updateStatus(incidentId, s, note || undefined);
    setNote('');
    refresh();
  }

  async function sendMessage() {
    if (!reply.trim()) return;
    await incidentsApi.postMessage(incidentId, reply.trim());
    setReply('');
    refresh();
  }

  if (!incident) return <div>Loading…</div>;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>
        Incident #{incident.id}{' '}
        <StatusBadge status={incident.status} />{' '}
        <SeverityBadge severity={incident.severity_level} />
      </h2>

      <div className="detail-grid">
        <div className="card">
          {incident.image_url ? (
            <img src={incident.image_url} className="image-preview" alt="incident" />
          ) : (
            <div style={{ color: 'var(--muted)' }}>No image.</div>
          )}
          <div style={{ marginTop: 12 }}>
            <h4>AI Description</h4>
            <pre style={{
              whiteSpace: 'pre-wrap', background: 'var(--panel-2)',
              padding: 12, borderRadius: 6, fontSize: 13,
            }}>
              {incident.ai_description || '— Not analyzed yet —'}
            </pre>

            {incident.ai_analysis && (
              <div className="chip-row" style={{ marginTop: 8 }}>
                <span className="chip">Scene: {incident.ai_analysis.scene_label}</span>
                <span className="chip">
                  Confidence: {Math.round((incident.ai_analysis.confidence_score ?? 0) * 100)}%
                </span>
                <span className="chip">Model: {incident.ai_analysis.model_version}</span>
              </div>
            )}

            {incident.user_description && (
              <>
                <h4 style={{ marginTop: 16 }}>Citizen description</h4>
                <p>{incident.user_description}</p>
              </>
            )}
          </div>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Details</h3>
          <table className="table">
            <tbody>
              <tr><th>Type</th><td>{incident.incident_type ?? '—'}</td></tr>
              <tr><th>Status</th><td><StatusBadge status={incident.status} /></td></tr>
              <tr><th>Severity</th><td><SeverityBadge severity={incident.severity_level} /></td></tr>
              <tr><th>Reporter</th><td>#{incident.reporter_id}</td></tr>
              <tr>
                <th>Location</th>
                <td>
                  {incident.latitude && incident.longitude
                    ? `${Number(incident.latitude).toFixed(5)}, ${Number(incident.longitude).toFixed(5)}`
                    : '—'}
                </td>
              </tr>
              <tr><th>Created</th><td>{new Date(incident.created_at).toLocaleString()}</td></tr>
              <tr><th>Updated</th><td>{new Date(incident.updated_at).toLocaleString()}</td></tr>
              {incident.resolved_at && (
                <tr><th>Resolved</th><td>{new Date(incident.resolved_at).toLocaleString()}</td></tr>
              )}
            </tbody>
          </table>

          <h4 style={{ marginTop: 24 }}>Update status</h4>
          <textarea
            placeholder="Optional note for the citizen…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
          />
          <div className="actions">
            {NEXT_STATUSES.map((s) => (
              <button
                key={s}
                className={s === 'rejected' ? 'danger' : s === 'resolved' ? '' : 'ghost'}
                onClick={() => changeStatus(s)}
              >
                {s.replace('_', ' ')}
              </button>
            ))}
          </div>

          <h4 style={{ marginTop: 24 }}>Messages</h4>
          <div className="message-list">
            {messages.map((m) => (
              <div key={m.id} className={`message ${m.sender_role === 'officer' || m.sender_role === 'admin' ? 'officer' : ''}`}>
                <div className="message-meta">
                  {m.sender_role} • {new Date(m.created_at).toLocaleString()}
                </div>
                {m.message}
              </div>
            ))}
            {messages.length === 0 && (
              <div style={{ color: 'var(--muted)', fontSize: 13 }}>No messages yet.</div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <input
              placeholder="Reply to citizen…"
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            />
            <button onClick={sendMessage}>Send</button>
          </div>
        </div>
      </div>
    </div>
  );
}
