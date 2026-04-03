import { useEffect, useState } from 'react';
import { ShieldAlert, AlertTriangle, Clock, MapPin, FileWarning, ShieldOff, Flame, TreeDeciduous } from 'lucide-react';
import api from '../utils/api';

const ICONS: any = { 'alert-triangle': AlertTriangle, clock: Clock, 'map-pin': MapPin, 'file-warning': FileWarning, 'shield-off': ShieldOff, flame: Flame, 'tree-deciduous': TreeDeciduous, repeat: Clock };

export default function FraudAlerts() {
  const [data, setData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<string>('');

  useEffect(() => {
    api.get('/fraud-alerts/grouped-by-type').then(r => {
      setData(r.data);
      const types = Object.keys(r.data.types || {});
      if (types.length > 0) setActiveTab(types[0]);
    }).catch(() => {});
  }, []);

  if (!data) return <div className="loading-page"><div className="spinner" /></div>;

  const types = data.types || {};
  const typeKeys = Object.keys(types);
  const current = types[activeTab];
  const explanation = current?.explanation;
  const sevColor = (s: string) => s === 'critical' ? '#ef4444' : s === 'high' ? '#f87171' : s === 'medium' ? '#fbbf24' : '#94a3b8';

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Detecção de Fraude</h1>
        <p className="page-subtitle">{data.total_alerts} alertas em {data.total_types} categorias</p>
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ overflowX: 'auto' }}>
        {typeKeys.map(t => {
          const exp = types[t]?.explanation;
          const Icon = ICONS[exp?.icon] || ShieldAlert;
          return (
            <div key={t} className={`tab ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>
              <Icon size={14} style={{ display: 'inline', marginRight: '0.35rem', verticalAlign: 'middle' }} />
              {exp?.title?.split(' (')[0] || t.replace(/_/g, ' ')}
              <span className="badge badge-red" style={{ marginLeft: '0.35rem' }}>{types[t].total}</span>
            </div>
          );
        })}
      </div>

      {/* Explanation Card */}
      {explanation && (
        <div className="card" style={{ marginBottom: '1.5rem', borderLeft: '3px solid var(--cv-primary)' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.75rem' }}>{explanation.title}</h3>
          <div className="grid-3" style={{ gap: '1.5rem' }}>
            <div><div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--cv-primary)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>O que é?</div><p style={{ fontSize: '0.85rem', color: 'var(--cv-text-muted)', lineHeight: 1.5 }}>{explanation.what_is}</p></div>
            <div><div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--cv-danger)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>Consequências</div><p style={{ fontSize: '0.85rem', color: 'var(--cv-text-muted)', lineHeight: 1.5 }}>{explanation.consequences}</p></div>
            <div><div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--cv-accent)', marginBottom: '0.4rem', textTransform: 'uppercase' }}>Situação Ideal</div><p style={{ fontSize: '0.85rem', color: 'var(--cv-text-muted)', lineHeight: 1.5 }}>{explanation.ideal_situation}</p></div>
          </div>
        </div>
      )}

      {/* Alert Cards */}
      {current?.items?.map((a: any) => (
        <div key={a.id} className="card" style={{ marginBottom: '0.75rem', borderLeft: `3px solid ${sevColor(a.severity)}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: '0.25rem' }}>{a.title}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)', marginBottom: '0.5rem' }}>
                Projeto: <strong>{a.project_name}</strong> · Confiança: {(a.confidence * 100).toFixed(0)}%
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--cv-text)', lineHeight: 1.5 }}>{a.description}</p>
              {a.recommendation && <p style={{ fontSize: '0.8rem', color: 'var(--cv-primary)', marginTop: '0.5rem' }}>💡 {a.recommendation}</p>}
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <span className={`badge ${a.severity === 'critical' || a.severity === 'high' ? 'badge-red' : a.severity === 'medium' ? 'badge-yellow' : 'badge-blue'}`}>{a.severity}</span>
              <div style={{ marginTop: '0.5rem' }}><span className={`badge ${a.status === 'open' ? 'badge-yellow' : a.status === 'confirmed' ? 'badge-red' : 'badge-green'}`}>{a.status}</span></div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
