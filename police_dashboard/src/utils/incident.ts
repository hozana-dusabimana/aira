// Human-friendly labels for the canonical incident types produced by the
// backend AI classifier. Falls back gracefully for null/empty/legacy values
// so officers never see a raw "unknown".

const TYPE_LABELS: Record<string, string> = {
  fire: 'Fire',
  traffic: 'Traffic accident',
  violent_crime: 'Violent crime',
  theft: 'Theft',
  vandalism: 'Vandalism',
  suspicious_activity: 'Suspicious activity',
  general: 'Other',
};

export function incidentTypeLabel(type?: string | null): string {
  if (!type || !type.trim()) return 'Pending review';
  const key = type.trim().toLowerCase();
  if (TYPE_LABELS[key]) return TYPE_LABELS[key];
  // Prettify any unmapped value: "vehicle_collision" -> "Vehicle collision".
  return key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
}
