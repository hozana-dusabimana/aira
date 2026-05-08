import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import ConfirmDialog, { type ConfirmTone } from '../components/common/ConfirmDialog';
import IncidentLocationCard from '../components/incidents/IncidentLocationCard';
import { SeverityBadge, StatusBadge } from '../components/incidents/StatusBadge';
import { incidents as incidentsApi } from '../services/api';
import { realtime } from '../services/realtime';
import type { Incident, IncidentMessage, IncidentStatus } from '../types';

const STATUS_CONFIRM: Record<
  IncidentStatus,
  { tone: ConfirmTone; label: string; verb: string; description: string }
> = {
  pending: {
    tone: 'primary',
    label: 'Mark as pending',
    verb: 'reset to pending',
    description: 'The incident will return to the pending queue and become unassigned.',
  },
  analyzing: {
    tone: 'primary',
    label: 'Mark as analyzing',
    verb: 'mark as analyzing',
    description: 'The incident will be flagged as currently being analyzed.',
  },
  verified: {
    tone: 'primary',
    label: 'Verify incident',
    verb: 'mark as verified',
    description: 'The incident details have been reviewed and confirmed as a real report.',
  },
  assigned: {
    tone: 'primary',
    label: 'Assign incident',
    verb: 'mark as assigned',
    description: 'An officer has been assigned to handle this incident.',
  },
  in_progress: {
    tone: 'warning',
    label: 'Set in progress',
    verb: 'set to in progress',
    description: 'Officers are now actively responding to this incident.',
  },
  resolved: {
    tone: 'success',
    label: 'Resolve incident',
    verb: 'resolve',
    description: 'The case will be closed and the citizen will be notified that the incident is resolved.',
  },
  rejected: {
    tone: 'danger',
    label: 'Reject incident',
    verb: 'reject',
    description: 'The report will be marked as rejected. The citizen will see this and may be notified.',
  },
};

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
  const [pendingStatus, setPendingStatus] = useState<IncidentStatus | null>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);

  const refresh = useCallback(async () => {
    const data = await incidentsApi.get(incidentId);
    setIncident(data);
    const msgs = await incidentsApi.messages(incidentId);
    setMessages(msgs);
  }, [incidentId]);

  useEffect(() => {
    if (!isNaN(incidentId)) refresh();
  }, [incidentId, refresh]);

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

  async function confirmStatusChange() {
    if (!pendingStatus) return;
    setConfirmBusy(true);
    try {
      await changeStatus(pendingStatus);
      setPendingStatus(null);
    } catch (err) {
      console.error('Failed to update status', err);
      // keep the dialog open so the user knows it failed; they can cancel/retry
    } finally {
      setConfirmBusy(false);
    }
  }

  async function sendMessage() {
    if (!reply.trim()) return;
    await incidentsApi.postMessage(incidentId, reply.trim());
    setReply('');
    refresh();
  }

  if (!incident) return <div>Loading…</div>;

  const pendingMeta = pendingStatus ? STATUS_CONFIRM[pendingStatus] : null;

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
              <tr><th>Created</th><td>{new Date(incident.created_at).toLocaleString()}</td></tr>
              <tr><th>Updated</th><td>{new Date(incident.updated_at).toLocaleString()}</td></tr>
              {incident.resolved_at && (
                <tr><th>Resolved</th><td>{new Date(incident.resolved_at).toLocaleString()}</td></tr>
              )}
            </tbody>
          </table>

          <div style={{ marginTop: 16 }}>
            <IncidentLocationCard
              latitude={incident.latitude}
              longitude={incident.longitude}
              severity={incident.severity_level}
              incidentId={incident.id}
            />
          </div>

          <h4 style={{ marginTop: 24 }}>
            <label htmlFor="status-note">Update status</label>
          </h4>
          <textarea
            id="status-note"
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
                onClick={() => setPendingStatus(s)}
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

      {pendingMeta && (
        <ConfirmDialog
          open
          title={pendingMeta.label}
          tone={pendingMeta.tone}
          confirmLabel={pendingMeta.label}
          cancelLabel="Cancel"
          busy={confirmBusy}
          onCancel={() => !confirmBusy && setPendingStatus(null)}
          onConfirm={confirmStatusChange}
          message={
            <div>
              <p style={{ margin: '0 0 10px' }}>
                You're about to <strong>{pendingMeta.verb}</strong> incident{' '}
                <strong>#{incident.id}</strong>.
              </p>
              <p style={{ margin: '0 0 12px', color: 'var(--muted)', fontSize: 13 }}>
                {pendingMeta.description}
              </p>
              {note.trim() ? (
                <div className="confirm-note">
                  <div className="confirm-note-label">Note for the citizen</div>
                  <div className="confirm-note-text">{note}</div>
                </div>
              ) : (
                <div className="confirm-note confirm-note-empty">
                  No note will be sent. You can cancel and add one in the field above.
                </div>
              )}
            </div>
          }
        />
      )}
    </div>
  );
}
