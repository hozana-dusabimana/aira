import L from 'leaflet';
import { useEffect, useState } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import { incidents as incidentsApi } from '../services/api';
import type { Incident, SeverityLevel } from '../types';

// Fix default marker icons in react-leaflet 4 + Vite
delete (L.Icon.Default.prototype as any)._getIconUrl;
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

export default function MapView() {
  const [list, setList] = useState<Incident[]>([]);

  useEffect(() => {
    incidentsApi.list({ limit: 200 }).then(setList).catch(() => {});
  }, []);

  const points = list.filter((i) => i.latitude != null && i.longitude != null);
  const center: [number, number] = points.length
    ? [Number(points[0].latitude), Number(points[0].longitude)]
    : [-1.9536, 30.0606]; // Kigali

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Incident heatmap</h3>
      <div className="map-container">
        <MapContainer center={center} zoom={12} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {points.map((i) => (
            <CircleMarker
              key={i.id}
              center={[Number(i.latitude), Number(i.longitude)]}
              radius={8}
              pathOptions={{
                color: SEV_COLORS[i.severity_level],
                fillColor: SEV_COLORS[i.severity_level],
                fillOpacity: 0.6,
              }}
            >
              <Popup>
                <strong>#{i.id} — {i.incident_type ?? 'unknown'}</strong>
                <br />Severity: {i.severity_level}
                <br />Status: {i.status}
                <br /><a href={`/incidents/${i.id}`}>Open details</a>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
