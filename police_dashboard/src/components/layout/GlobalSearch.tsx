import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { incidents as incidentsApi } from '../../services/api';
import type { Incident } from '../../types';

export default function GlobalSearch() {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const trimmed = q.trim();
    if (!trimmed) {
      setResults([]);
      return;
    }
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await incidentsApi.list({ limit: 20 });
        const lower = trimmed.toLowerCase();
        const filtered = data.filter((i) => {
          const blob = `${i.id} ${i.incident_type ?? ''} ${i.user_description ?? ''} ${i.ai_description ?? ''} ${i.status} ${i.severity_level}`.toLowerCase();
          return blob.includes(lower);
        });
        setResults(filtered.slice(0, 8));
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  function go(id: number) {
    setOpen(false);
    setQ('');
    navigate(`/incidents/${id}`);
  }

  return (
    <div className="search-wrap" ref={wrapRef}>
      <div className="search-input">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <path d="m21 21-4.3-4.3"></path>
        </svg>
        <input
          type="search"
          placeholder="Search incidents by ID, type, description..."
          value={q}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setOpen(false);
            if (e.key === 'Enter' && results.length > 0) go(results[0].id);
          }}
        />
      </div>

      {open && q.trim().length > 0 && (
        <div className="search-panel">
          {loading && <div className="search-empty">Searching...</div>}
          {!loading && results.length === 0 && (
            <div className="search-empty">No matches.</div>
          )}
          {results.map((i) => (
            <button
              key={i.id}
              type="button"
              className="search-item"
              onClick={() => go(i.id)}
            >
              <span className={`search-sev ${i.severity_level}`} />
              <div className="search-body">
                <div className="search-title">
                  #{i.id} · {i.incident_type ?? 'Incident'}
                </div>
                <div className="search-sub">
                  {i.user_description?.slice(0, 70) ?? i.ai_description?.slice(0, 70) ?? 'No description'}
                </div>
              </div>
              <span className={`badge ${i.status}`}>{i.status.replace('_', ' ')}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
