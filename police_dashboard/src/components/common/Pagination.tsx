type Props = {
  page: number;          // 1-based current page
  pageSize: number;
  total: number;         // total item count (unpaginated)
  onPageChange: (page: number) => void;
  label?: string;        // noun for the "Showing X of Y <label>" line
};

// Build a compact page list with ellipsis gaps, e.g. [1, '…', 4, 5, 6, '…', 12].
function pageItems(current: number, count: number): (number | '…')[] {
  if (count <= 7) return Array.from({ length: count }, (_, i) => i + 1);
  const items: (number | '…')[] = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(count - 1, current + 1);
  if (start > 2) items.push('…');
  for (let p = start; p <= end; p++) items.push(p);
  if (end < count - 1) items.push('…');
  items.push(count);
  return items;
}

export default function Pagination({ page, pageSize, total, onPageChange, label = 'items' }: Props) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) return null;

  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  const go = (p: number) => onPageChange(Math.min(pageCount, Math.max(1, p)));

  return (
    <div className="pagination">
      <span className="pagination-info">
        Showing {from}–{to} of {total} {label}
      </span>
      <div className="pagination-pages">
        <button className="pagination-btn" onClick={() => go(page - 1)} disabled={page <= 1}>
          ‹ Prev
        </button>
        {pageItems(page, pageCount).map((it, idx) =>
          it === '…' ? (
            <span key={`gap-${idx}`} className="pagination-gap">…</span>
          ) : (
            <button
              key={it}
              className={`pagination-btn${it === page ? ' is-active' : ''}`}
              onClick={() => go(it)}
            >
              {it}
            </button>
          ),
        )}
        <button className="pagination-btn" onClick={() => go(page + 1)} disabled={page >= pageCount}>
          Next ›
        </button>
      </div>
    </div>
  );
}
