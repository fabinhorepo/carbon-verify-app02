import { useEffect, useState, useRef } from 'react';
import api from '../utils/api';

export default function ProjectMap() {
  const [projects, setProjects] = useState<any[]>([]);
  const [mapReady, setMapReady] = useState(false);
  const mapRef = useRef<any>(null);
  const mapContainer = useRef<HTMLDivElement>(null);

  useEffect(() => { api.get('/projects/geo').then(r => setProjects(r.data)).catch(() => {}); }, []);

  useEffect(() => {
    if (projects.length === 0 || mapReady) return;
    const loadMap = async () => {
      const L = await import('leaflet');
      await import('leaflet/dist/leaflet.css');
      if (!mapContainer.current || mapRef.current) return;

      const map = L.map(mapContainer.current).setView([0, 20], 2);
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© CartoDB © OpenStreetMap', maxZoom: 18,
      }).addTo(map);

      projects.forEach(p => {
        if (!p.lat || !p.lng) return;
        const color = p.score > 60 ? '#34d399' : p.score > 40 ? '#fbbf24' : '#f87171';
        const icon = L.divIcon({
          className: '', html: `<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2px solid ${color};opacity:0.85;box-shadow:0 0 8px ${color}60"></div>`,
        });
        L.marker([p.lat, p.lng], { icon }).addTo(map)
          .bindPopup(`<div style="font-family:Inter,sans-serif;min-width:200px">
            <b style="font-size:14px">${p.name}</b><br>
            <span style="color:#666">${p.project_type} · ${p.country}</span><br>
            <b>Score:</b> ${p.score?.toFixed(1)} · <b>Grade:</b> ${p.grade}<br>
            ${p.alert_count > 0 ? `<span style="color:#ef4444">⚠️ ${p.alert_count} alertas</span>` : '<span style="color:#22c55e">✓ Sem alertas</span>'}
            <br><a href="/projects/${p.id}" style="color:#0ea5e9">Ver detalhes →</a></div>`);
      });
      mapRef.current = map;
      setMapReady(true);
    };
    loadMap();
    return () => { if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } };
  }, [projects]);

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Mapa de Projetos</h1><p className="page-subtitle">{projects.length} projetos com coordenadas</p></div>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}><div style={{ width: 10, height: 10, borderRadius: '50%', background: '#34d399' }}></div>Score &gt; 60</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}><div style={{ width: 10, height: 10, borderRadius: '50%', background: '#fbbf24' }}></div>Score 40-60</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}><div style={{ width: 10, height: 10, borderRadius: '50%', background: '#f87171' }}></div>Score &lt; 40</div>
      </div>
      <div ref={mapContainer} style={{ height: '600px', borderRadius: '12px', border: '1px solid var(--cv-border)' }} />
    </div>
  );
}
