import type { IncidentStatus, SeverityLevel } from '../../types';

export function StatusBadge({ status }: { status: IncidentStatus }) {
  return <span className={`badge ${status}`}>{status.replace('_', ' ')}</span>;
}

export function SeverityBadge({ severity }: { severity: SeverityLevel }) {
  return <span className={`severity ${severity}`}>{severity.toUpperCase()}</span>;
}
