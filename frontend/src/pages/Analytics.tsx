import { useEffect, useState } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../utils/api';

export default function Analytics() {
  const [corr, setCorr] = useState<any>(null);
  const [kpis, setKpis] = useState<any>(null);

  useEffect(() => {
    api.get('/analytics/correlations').then(r => setCorr(r.data)).catch(() => {});
    api.get('/analytics/performance-kpis').then(r => setKpis(r.data)).catch(() => {});
  }, []);

  if (!corr || !kpis) return <div className="loading-page"><div className="spinner" /></div>;

  const scatterData = corr.scatter_data?.map((d: any) => ({ ...d, x: d.score, y: d.credits, z: d.fraud_count })) || [];
  const heatmapTypes = Object.keys(corr.heatmap || {});
  const allAlertTypes = new Set<string>();
  heatmapTypes.forEach(pt => Object.keys(corr.heatmap[pt] || {}).forEach(at => allAlertTypes.add(at)));
  const alertTypesList = Array.from(allAlertTypes);

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Analytics Avançado</h1><p className="page-subtitle">Correlações e KPIs de performance</p></div>

      {/* KPIs */}
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="card"><div className="card-title">Taxa Resolução Alertas</div><div className="card-value" style={{ color: kpis.alert_resolution_rate > 50 ? '#34d399' : '#fbbf24' }}>{kpis.alert_resolution_rate}%</div></div>
        <div className="card"><div className="card-title">Score Médio Portfólio</div><div className="card-value">{kpis.avg_portfolio_score}</div></div>
        <div className="card"><div className="card-title">Total Alertas</div><div className="card-value">{kpis.total_alerts}</div><div className="card-subtitle">{kpis.resolved_alerts} resolvidos</div></div>
        <div className="card"><div className="card-title">Valor Portfólio</div><div className="card-value">€{kpis.total_portfolio_value_eur?.toLocaleString()}</div></div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
        {/* Scatter */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Score vs Créditos Emitidos</div>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart><XAxis dataKey="x" name="Score" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis dataKey="y" name="Créditos" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Scatter data={scatterData} fill="#0ea5e9" opacity={0.6} /><Tooltip /></ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Heatmap */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Heatmap: Tipo × Alerta</div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ fontSize: '0.75rem' }}>
              <thead><tr><th></th>{alertTypesList.map(at => <th key={at} style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', padding: '0.5rem 0.25rem' }}>{at.replace(/_/g, ' ')}</th>)}</tr></thead>
              <tbody>
                {heatmapTypes.map(pt => (
                  <tr key={pt}><td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{pt}</td>
                    {alertTypesList.map(at => {
                      const v = corr.heatmap[pt]?.[at] || 0;
                      const bg = v === 0 ? 'var(--cv-surface)' : v < 3 ? 'rgba(14,165,233,0.15)' : v < 6 ? 'rgba(245,158,11,0.2)' : 'rgba(239,68,68,0.2)';
                      return <td key={at} style={{ background: bg, textAlign: 'center', fontWeight: 700 }}>{v || '-'}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
