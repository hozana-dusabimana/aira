import L from 'leaflet';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import { incidents as incidentsApi } from '../services/api';
import type { Incident, SeverityLevel } from '../types';
import { incidentTypeLabel } from '../utils/incident';

// Fix default marker icons in react-leaflet 4 + Vite
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

function FlyTo({ position, zoom = 16 }: { position: [number, number] | null; zoom?: number }) {
  const map = useMap();
  useEffect(() => {
    if (!position) return;
    map.flyTo(position, zoom, { duration: 0.8 });
  }, [position, zoom, map]);
  return null;
}

export default function MapView() {
  const [list, setList] = useState<Incident[]>([]);
  const [searchParams] = useSearchParams();
  const focusId = Number(searchParams.get('focus') ?? '');

  useEffect(() => {
    incidentsApi.list({ limit: 200 }).then(setList).catch(() => {});
  }, []);

  const points = useMemo(
    () => list.filter((i) => i.latitude != null && i.longitude != null),
    [list],
  );

  const focus = useMemo(() => {
    if (!focusId) return null;
    return points.find((i) => i.id === focusId) ?? null;
  }, [points, focusId]);

  const center: [number, number] = focus
    ? [Number(focus.latitude), Number(focus.longitude)]
    : points.length
      ? [Number(points[0].latitude), Number(points[0].longitude)]
      : [-1.9536, 30.0606]; // Kigali

  const flyTarget: [number, number] | null = focus
    ? [Number(focus.latitude), Number(focus.longitude)]
    : null;

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>
        Operations map
        {focus && (
          <span style={{ marginLeft: 12, color: 'var(--accent)', fontSize: 14 }}>
            · focused on #{focus.id}
          </span>
        )}
      </h3>
      <div className="map-container">
        <MapContainer center={center} zoom={focus ? 16 : 12} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FlyTo position={flyTarget} />
          {points.map((i) => {
            const isFocus = focus && i.id === focus.id;
            return (
              <CircleMarker
                key={i.id}
                center={[Number(i.latitude), Number(i.longitude)]}
                radius={isFocus ? 14 : 8}
                pathOptions={{
                  color: SEV_COLORS[i.severity_level],
                  fillColor: SEV_COLORS[i.severity_level],
                  fillOpacity: isFocus ? 0.8 : 0.6,
                  weight: isFocus ? 4 : 2,
                }}
              >
                <Popup>
                  <strong>#{i.id} — {incidentTypeLabel(i.incident_type)}</strong>
                  <br />Severity: {i.severity_level}
                  <br />Status: {i.status}
                  <br />
                  <a href={`/incidents/${i.id}`}>Open details</a>
                  {' · '}
                  <a
                    href={`https://www.google.com/maps/dir/?api=1&destination=${i.latitude},${i.longitude}&travelmode=driving`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Navigate
                  </a>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
