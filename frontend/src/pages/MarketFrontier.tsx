import { useState, useEffect, useMemo } from 'react';
import { TrendingDown, TrendingUp, Target, Award, Star } from 'lucide-react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import api from '../utils/api';
import ProjectLink from '../components/ProjectLink';

interface FrontierPoint {
  project_id: number;
  project_name: string;
  project_type: string;
  grade: string;
  price_eur: number;
  rating_score: number;
  is_frontier: boolean;
  is_opportunity: boolean;
}

interface Opportunity {
  project_id: number;
  project_name: string;
  project_type: string;
  grade: string;
  price_eur: number;
  median_price_eur: number;
  discount_pct: number;
  rating_score: number;
  risk_adjusted_cost_eur: number;
  opportunity_score: number;
}

const gradeColors: Record<string, string> = {
  AAA: '#10b981', AA: '#34d399', A: '#6ee7b7', BBB: '#fbbf24', BB: '#f59e0b',
  B: '#f97316', CCC: '#ef4444', CC: '#dc2626', C: '#991b1b', D: '#7f1d1d',
};

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '8px', padding: '0.75rem', fontSize: '0.75rem' }}>
      <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{d.project_name}</div>
      <div style={{ color: 'var(--cv-text-muted)' }}>{d.project_type} · {d.grade}</div>
      <div style={{ color: '#34d399' }}>€{d.price_eur?.toFixed(2)}/tCO₂</div>
      <div style={{ color: '#818cf8' }}>Score: {d.rating_score?.toFixed(1)}/100</div>
      {d.is_frontier && <div style={{ color: '#fbbf24', fontWeight: 600, marginTop: '0.25rem' }}>★ Fronteira Eficiente</div>}
      {d.is_opportunity && <div style={{ color: '#34d399', fontWeight: 600, marginTop: '0.25rem' }}>💎 Oportunidade</div>}
    </div>
  );
};

const gradeStyle = (grade: string) => {
  if (['AAA', 'AA', 'A'].includes(grade)) return { color: '#34d399', background: 'rgba(52, 211, 153, 0.1)', border: '1px solid rgba(52, 211, 153, 0.2)' };
  if (['BBB', 'BB'].includes(grade)) return { color: '#fbbf24', background: 'rgba(251, 191, 36, 0.1)', border: '1px solid rgba(251, 191, 36, 0.2)' };
  return { color: '#f87171', background: 'rgba(248, 113, 113, 0.1)', border: '1px solid rgba(248, 113, 113, 0.2)' };
};

export default function MarketFrontier() {
  const [data, setData] = useState<{ frontier: FrontierPoint[]; opportunities: Opportunity[]; all_points: FrontierPoint[]; stats: any } | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'chart' | 'opportunities'>('chart');

  useEffect(() => {
    setLoading(true);
    api.get('/market/frontier')
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const chartData = useMemo(() => {
    if (!data?.all_points) return [];
    return data.all_points.map(p => ({ ...p, x: p.price_eur, y: p.rating_score }));
  }, [data]);

  return (
    <div className="fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Target size={28} style={{ color: '#fbbf24' }} /> Price-Quality Frontier
          </h1>
          <p className="page-subtitle">Fronteira eficiente preço-qualidade e identificação de oportunidades</p>
        </div>
        <div className="tabs" style={{ margin: 0 }}>
          <div className={`tab ${view === 'chart' ? 'active' : ''}`} onClick={() => setView('chart')}>Gráfico</div>
          <div className={`tab ${view === 'opportunities' ? 'active' : ''}`} onClick={() => setView('opportunities')}>
            Oportunidades ({data?.opportunities?.length || 0})
          </div>
        </div>
      </div>

      {/* Stats */}
      {data?.stats && (
        <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
          {[
            { label: 'Créditos Analisados', value: data.stats.total_credits_analyzed, icon: <Award size={18} style={{ color: '#818cf8' }} /> },
            { label: 'Na Fronteira', value: data.stats.frontier_points, icon: <Star size={18} style={{ color: '#fbbf24' }} /> },
            { label: 'Oportunidades', value: data.stats.opportunities_found, icon: <TrendingUp size={18} style={{ color: '#34d399' }} /> },
            { label: 'Preço Médio', value: `€${data.stats.avg_price?.toFixed(2)}`, icon: <TrendingDown size={18} style={{ color: '#fbbf24' }} /> },
          ].map((stat, i) => (
            <div key={i} className="card">
              <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>{stat.icon} {stat.label}</div>
              <div className="card-value">{stat.value}</div>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="loading-page"><div className="spinner" /></div>
      ) : view === 'chart' ? (
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Curva Eficiente — Preço (EUR/tCO₂) vs Qualidade (Score)</div>
          <ResponsiveContainer width="100%" height={450}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
              <XAxis type="number" dataKey="x" name="Preço" unit="€" tick={{ fill: '#94a3b8', fontSize: 12 }}
                label={{ value: 'Preço (EUR/tCO₂)', position: 'insideBottom', offset: -20, style: { fill: '#94a3b8', fontSize: 12 } }} />
              <YAxis type="number" dataKey="y" name="Score" tick={{ fill: '#94a3b8', fontSize: 12 }} domain={[0, 100]}
                label={{ value: 'Score de Qualidade', angle: -90, position: 'insideLeft', offset: 10, style: { fill: '#94a3b8', fontSize: 12 } }} />
              <Tooltip content={<CustomTooltip />} />
              <Scatter name="Créditos" data={chartData} shape="circle">
                {chartData.map((entry, i) => (
                  <Cell key={i}
                    fill={entry.is_frontier ? '#fbbf24' : entry.is_opportunity ? '#10b981' : gradeColors[entry.grade] || '#6b7280'}
                    r={entry.is_frontier ? 8 : entry.is_opportunity ? 7 : 5}
                    stroke={entry.is_frontier ? '#fbbf24' : entry.is_opportunity ? '#10b981' : 'none'}
                    strokeWidth={entry.is_frontier || entry.is_opportunity ? 2 : 0}
                    opacity={entry.is_frontier || entry.is_opportunity ? 1 : 0.7}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', marginTop: '1rem', fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><span style={{ width: 12, height: 12, borderRadius: '50%', background: '#fbbf24', display: 'inline-block' }}></span> Fronteira Eficiente</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><span style={{ width: 12, height: 12, borderRadius: '50%', background: '#10b981', display: 'inline-block' }}></span> Oportunidade</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><span style={{ width: 12, height: 12, borderRadius: '50%', background: '#6b7280', display: 'inline-block' }}></span> Outros</span>
          </div>
        </div>
      ) : (
        <div>
          {data?.opportunities?.map((opp, i) => {
            const gs = gradeStyle(opp.grade);
            return (
              <div key={i} className="card" style={{ marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                      <span style={{ ...gs, padding: '0.15rem 0.5rem', borderRadius: '999px', fontWeight: 800, fontSize: '0.7rem', fontFamily: 'monospace' }}>{opp.grade}</span>
                      <ProjectLink projectId={opp.project_id} name={opp.project_name} />
                      <span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>{opp.project_type}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.8rem' }}>
                      <span style={{ color: '#34d399' }}>€{opp.price_eur.toFixed(2)}/tCO₂</span>
                      <span style={{ color: 'var(--cv-text-muted)' }}>Mediana: €{opp.median_price_eur.toFixed(2)}</span>
                      <span style={{ color: '#22c55e', fontWeight: 600 }}>{opp.discount_pct.toFixed(1)}% abaixo</span>
                      <span style={{ color: 'var(--cv-text-muted)' }}>Risk-adj: €{opp.risk_adjusted_cost_eur.toFixed(2)}</span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', marginLeft: '1rem' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#34d399' }}>{opp.opportunity_score.toFixed(1)}</div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)' }}>Score Oportunidade</div>
                  </div>
                </div>
              </div>
            );
          })}
          {!data?.opportunities?.length && (
            <div className="card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--cv-text-muted)' }}>
              Nenhuma oportunidade identificada no momento.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
