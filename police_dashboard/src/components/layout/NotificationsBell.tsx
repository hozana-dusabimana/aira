import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { notifications as notifApi } from '../../services/api';
import { realtime } from '../../services/realtime';
import type { Notification } from '../../types';

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function iconFor(type: string): string {
  if (type.includes('assigned')) return '👮';
  if (type.includes('resolved')) return '✅';
  if (type.includes('rejected')) return '❌';
  if (type.includes('message')) return '💬';
  if (type.includes('critical') || type.includes('emergency')) return '🚨';
  return '🔔';
}

export default function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  const unread = items.filter((n) => !n.is_read).length;

  async function load() {
    setLoading(true);
    try {
      const data = await notifApi.list();
      setItems(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, []);

  // Live refresh via shared staff WebSocket
  useEffect(() => {
    const unsubscribe = realtime.subscribeStaff(() => load());
    return unsubscribe;
  }, []);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  async function handleMarkAll() {
    await notifApi.markAllRead();
    load();
  }

  async function handleItemClick(n: Notification) {
    if (!n.is_read) {
      try {
        await notifApi.markRead(n.id);
        setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)));
      } catch {
        // ignore
      }
    }
    setOpen(false);
  }

  return (
    <div className="notif-wrap" ref={wrapRef}>
      <button
        type="button"
        className="icon-btn"
        aria-label="Notifications"
        onClick={() => setOpen((s) => !s)}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"></path>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
        </svg>
        {unread > 0 && <span className="notif-badge">{unread > 9 ? '9+' : unread}</span>}
      </button>

      {open && (
        <div className="notif-panel" role="menu">
          <div className="notif-header">
            <strong>Notifications</strong>
            {unread > 0 && (
              <button className="notif-link" type="button" onClick={handleMarkAll}>
                Mark all as read
              </button>
            )}
          </div>
          <div className="notif-list">
            {loading && items.length === 0 && (
              <div className="notif-empty">Loading...</div>
            )}
            {!loading && items.length === 0 && (
              <div className="notif-empty">You're all caught up.</div>
            )}
            {items.slice(0, 12).map((n) => {
              const target = n.related_incident_id
                ? `/incidents/${n.related_incident_id}`
                : '#';
              const Wrapper = n.related_incident_id ? Link : 'div';
              const wrapperProps = n.related_incident_id
                ? { to: target, onClick: () => handleItemClick(n) }
                : { onClick: () => handleItemClick(n) };
              return (
                // @ts-expect-error dynamic element
                <Wrapper
                  key={n.id}
                  className={`notif-item ${n.is_read ? '' : 'unread'}`}
                  {...wrapperProps}
                >
                  <span className="notif-icon">{iconFor(n.type)}</span>
                  <div className="notif-body">
                    <div className="notif-title">{n.title}</div>
                    {n.message && <div className="notif-msg">{n.message}</div>}
                    <div className="notif-time">{timeAgo(n.created_at)}</div>
                  </div>
                  {!n.is_read && <span className="notif-dot" />}
                </Wrapper>
              );
            })}
          </div>
          <div className="notif-footer">
            <Link to="/incidents" onClick={() => setOpen(false)}>View all incidents →</Link>
          </div>
        </div>
      )}
    </div>
  );
}
