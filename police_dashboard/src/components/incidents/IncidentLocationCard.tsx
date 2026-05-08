import L from 'leaflet';
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { CircleMarker, MapContainer, TileLayer } from 'react-leaflet';
import type { SeverityLevel } from '../../types';

// Fix Leaflet default marker icons in case any default markers render.
delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const SEV_COLORS: Record<SeverityLevel, string> = {
  low: '#94a3b8',
  medium: '#f59e0b',
  high: '#f97316',
  critical: '#ef4444',
};

interface Props {
  latitude: number | null | undefined;
  longitude: number | null | undefined;
  severity: SeverityLevel;
  incidentId: number;
}

export default function IncidentLocationCard({
  latitude,
  longitude,
  severity,
  incidentId,
}: Props) {
  const lat = latitude != null ? Number(latitude) : null;
  const lng = longitude != null ? Number(longitude) : null;
  const hasLocation = lat != null && lng != null && !Number.isNaN(lat) && !Number.isNaN(lng);

  const mapsUrl = useMemo(() => {
    if (!hasLocation) return null;
    return `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
  }, [lat, lng, hasLocation]);

  const directionsUrl = useMemo(() => {
    if (!hasLocation) return null;
    return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`;
  }, [lat, lng, hasLocation]);

  const osmUrl = useMemo(() => {
    if (!hasLocation) return null;
    return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=17/${lat}/${lng}`;
  }, [lat, lng, hasLocation]);

  if (!hasLocation) {
    return (
      <div className="loc-card loc-card-empty">
        <div className="loc-card-row">
          <span className="loc-icon" aria-hidden>📍</span>
          <div>
            <strong>No location attached</strong>
            <span>This report did not include GPS coordinates.</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="loc-card">
      <div className="loc-card-head">
        <span className="loc-icon" aria-hidden>📍</span>
        <div>
          <strong>Scene location</strong>
          <span>{lat!.toFixed(5)}, {lng!.toFixed(5)}</span>
        </div>
      </div>

      <div className="loc-mini-map">
        <MapContainer
          center={[lat!, lng!]}
          zoom={15}
          scrollWheelZoom={false}
          dragging={false}
          doubleClickZoom={false}
          zoomControl={false}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution="&copy; OpenStreetMap"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <CircleMarker
            center={[lat!, lng!]}
            radius={10}
            pathOptions={{
              color: SEV_COLORS[severity],
              fillColor: SEV_COLORS[severity],
              fillOpacity: 0.7,
              weight: 3,
            }}
          />
        </MapContainer>
      </div>

      <div className="loc-actions">
        <a
          className="loc-btn loc-btn-primary"
          href={directionsUrl!}
          target="_blank"
          rel="noopener noreferrer"
        >
          🧭 Navigate to scene
        </a>
        <a
          className="loc-btn"
          href={mapsUrl!}
          target="_blank"
          rel="noopener noreferrer"
        >
          🗺️ Open in Google Maps
        </a>
        <a
          className="loc-btn"
          href={osmUrl!}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open in OpenStreetMap
        </a>
        <Link
          className="loc-btn"
          to={`/map?focus=${incidentId}`}
        >
          View on operations map
        </Link>
      </div>
    </div>
  );
}
