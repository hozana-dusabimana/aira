import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { mediaUrl, spam as spamApi } from '../services/api';
import type { SpamReport } from '../types';
import { incidentTypeLabel } from '../utils/incident';

export default function Spam() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [list, setList] = useState<SpamReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggleExpanded = (id: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  async function load() {
    setLoading(true);
    try {
      setList(await spamApi.list({ limit: 100 }));
    } finally {
      setLoading(false);
    }
  }

  async function importPast() {
    setImporting(true);
    try {
      const res = await spamApi.backfill();
      await load();
      window.alert(
        res.created > 0
          ? `Imported ${res.created} past rejected report(s).`
          : `Nothing to import — all ${res.total_rejected} rejected report(s) are already here.`,
      );
    } finally {
      setImporting(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function markNotSpam(id: number) {
    if (!window.confirm('Restore this report as a real incident? It will appear on the Incidents page and officers will be notified.')) {
      return;
    }
    setBusyId(id);
    try {
      await spamApi.notSpam(id);
      setList((prev) => prev.filter((s) => s.id !== id));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(id: number) {
    if (!window.confirm('Permanently delete this spam report and its image? This cannot be undone.')) {
      return;
    }
    setBusyId(id);
    try {
      await spamApi.remove(id);
      setList((prev) => prev.filter((s) => s.id !== id));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <strong>Spam / rejected reports</strong>
          <span style={{ color: 'var(--muted)', fontSize: 13 }}>
            Photos the AI did not recognise as a reportable incident. They are hidden from the
            Incidents page. Use “Not spam” to restore a genuine incident.
          </span>
          <button
            className="ghost"
            style={{ marginLeft: 'auto' }}
            onClick={importPast}
            disabled={importing}
            title="Import reports that were rejected before the Spam page existed"
          >
            {importing ? 'Importing...' : 'Import past rejections'}
          </button>
          <button className="ghost" onClick={load} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Image</th><th>Detected type</th><th>AI caption</th>
              <th>Reporter</th><th>Created</th><th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {list.map((s) => (
              <tr key={s.id}>
                <td>
                  {s.image_url ? (
                    <img
                      src={mediaUrl(s.image_url)}
                      alt="spam"
                      style={{ width: 56, height: 42, objectFit: 'cover', borderRadius: 6, cursor: 'pointer' }}
                      onClick={() => setPreview(mediaUrl(s.image_url))}
                    />
                  ) : (
                    '—'
                  )}
                </td>
                <td>{incidentTypeLabel(s.incident_type)}</td>
                <td style={{ maxWidth: 320, color: 'var(--muted)', fontSize: 13 }}>
                  <AiCaption
                    text={s.ai_caption ?? s.ai_description ?? '—'}
                    expanded={expanded.has(s.id)}
                    onToggle={() => toggleExpanded(s.id)}
                  />
                </td>
                <td>{s.reporter?.full_name ?? (s.reporter_id ? `#${s.reporter_id}` : '—')}</td>
                <td>{new Date(s.created_at).toLocaleString()}</td>
                <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                  <button
                    className="primary"
                    onClick={() => markNotSpam(s.id)}
                    disabled={busyId === s.id}
                  >
                    Not spam
                  </button>
                  {isAdmin && (
                    <button
                      className="ghost"
                      style={{ marginLeft: 8 }}
                      onClick={() => remove(s.id)}
                      disabled={busyId === s.id}
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {list.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: 'var(--muted)' }}>
                  {loading ? 'Loading...' : 'No spam reports.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {preview && (
        <div
          onClick={() => setPreview(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
        >
          <img
            src={preview}
            alt="spam preview"
            style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 8 }}
          />
        </div>
      )}
    </div>
  );
}

/** Trim a caption to its first two sentences (with a hard character cap). */
function summarize(text: string, maxSentences = 2, maxChars = 200): { short: string; truncated: boolean } {
  const trimmed = text.trim();
  const sentences = trimmed.match(/[^.!?]+[.!?]+/g);
  let short = trimmed;
  if (sentences && sentences.length > maxSentences) {
    short = sentences.slice(0, maxSentences).join(' ').replace(/\s+/g, ' ').trim();
  }
  if (short.length > maxChars) {
    short = `${short.slice(0, maxChars).trimEnd()}…`;
  }
  return { short, truncated: short.length < trimmed.length };
}

function AiCaption({ text, expanded, onToggle }: { text: string; expanded: boolean; onToggle: () => void }) {
  const { short, truncated } = summarize(text);
  if (!truncated) return <>{text}</>;
  return (
    <>
      {expanded ? text : short}{' '}
      <button
        type="button"
        onClick={onToggle}
        style={{
          background: 'none', border: 'none', padding: 0, cursor: 'pointer',
          color: 'var(--primary, #4f8cff)', fontSize: 13, fontWeight: 600,
        }}
      >
        {expanded ? 'View less' : 'View more'}
      </button>
    </>
  );
}
