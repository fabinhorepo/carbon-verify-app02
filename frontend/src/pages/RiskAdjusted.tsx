import { useState, useEffect } from 'react';
import { Scale, ArrowUpDown, AlertTriangle, Calculator, BarChart3 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import api from '../utils/api';

const gradeColors: Record<string, string> = {
  AAA: '#10b981', AA: '#34d399', A: '#6ee7b7', BBB: '#fbbf24', BB: '#f59e0b',
  B: '#f97316', CCC: '#ef4444', CC: '#dc2626', C: '#991b1b', D: '#7f1d1d',
};

export default function RiskAdjustedPortfolio() {
  const [metrics, setMetrics] = useState<any>(null);
  const [riskData, setRiskData] = useState<any>(null);
  const [targetImpact, setTargetImpact] = useState(100000);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get('/portfolios').then(r => {
      const portfolios = r.data || [];
      if (portfolios.length > 0) {
        const pid = portfolios[0].id;
        Promise.all([
          api.get(`/portfolios/${pid}/metrics`),
          api.get(`/portfolios/${pid}/risk-adjusted`, { params: { target_impact: targetImpact } }),
        ]).then(([mRes, rRes]) => {
          setMetrics(mRes.data);
          setRiskData(rRes.data);
          setLoading(false);
        }).catch(() => { setError(true); setLoading(false); });
      } else {
        setError(true);
        setLoading(false);
      }
    }).catch(() => { setError(true); setLoading(false); });
  }, [targetImpact]);

  const gradeChartData = metrics?.grade_distribution
    ? Object.entries(metrics.grade_distribution).map(([grade, qty]) => ({
        grade, qty: qty as number, fill: gradeColors[grade] || '#6b7280',
      }))
    : [];

  const gradeColor = (grade: string) => {
    if (['AAA', 'AA', 'A'].includes(grade)) return '#34d399';
    if (['BBB', 'BB'].includes(grade)) return '#fbbf24';
    return '#f87171';
  };

  if (error && !metrics) return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Scale size={28} style={{ color: '#06b6d4' }} /> Toneladas Ajustadas ao Risco
        </h1>
        <p className="page-subtitle">Cálculo BeZero-style: quanto carbono seu portfólio realmente compensa</p>
      </div>
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚖️</div>
        <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '0.5rem' }}>Sem dados de portfólio</div>
        <div style={{ color: 'var(--cv-text-muted)' }}>Crie um portfólio com posições para visualizar a análise de risco.</div>
      </div>
    </div>
  );

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Scale size={28} style={{ color: '#06b6d4' }} /> Toneladas Ajustadas ao Risco
        </h1>
        <p className="page-subtitle">Cálculo BeZero-style: quanto carbono seu portfólio realmente compensa</p>
      </div>

      {loading ? (
        <div className="loading-page"><div className="spinner" /></div>
      ) : metrics && (
        <>
          {/* Key Metrics */}
          <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
            <div className="card">
              <div className="card-title">Toneladas Nominais</div>
              <div className="card-value">{metrics.nominal_tonnes?.toLocaleString()}</div>
              <div className="card-subtitle">tCO₂e compradas</div>
            </div>
            <div className="card glow" style={{ borderColor: 'rgba(6, 182, 212, 0.3)' }}>
              <div className="card-title" style={{ color: '#06b6d4' }}>Toneladas Risk-Adjusted</div>
              <div className="card-value" style={{ color: '#06b6d4' }}>{metrics.risk_adjusted_tonnes?.toLocaleString()}</div>
              <div className="card-subtitle">tCO₂e efetivas</div>
            </div>
            <div className="card">
              <div className="card-title">Fator de Desconto Médio</div>
              <div className="card-value">{((metrics.discount_factor_avg || 0) * 100).toFixed(1)}%</div>
              <div className="card-subtitle">eficiência do portfólio</div>
            </div>
            <div className="card">
              <div className="card-title">Rating do Portfólio</div>
              <div className="card-value" style={{ color: gradeColor(metrics.portfolio_grade) }}>{metrics.portfolio_grade}</div>
              <div className="card-subtitle">score {metrics.avg_quality_score?.toFixed(1)}/100</div>
            </div>
          </div>

          {/* Visual: Nominal vs Risk-Adjusted */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="card-title" style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ArrowUpDown size={18} style={{ color: '#06b6d4' }} /> Comparação: Nominal vs Risk-Adjusted
            </div>
            <div>
              <div style={{ position: 'relative' }}>
                <div style={{ height: '3rem', background: 'var(--cv-surface)', borderRadius: '8px', overflow: 'hidden', marginBottom: '0.5rem' }}>
                  <div style={{
                    height: '100%', width: '100%',
                    background: 'linear-gradient(90deg, rgba(148,163,184,0.3), rgba(148,163,184,0.15))',
                    borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 600, fontSize: '0.85rem',
                  }}>
                    {metrics.nominal_tonnes?.toLocaleString()} tCO₂e (Nominal)
                  </div>
                </div>
                <div style={{ height: '3rem', background: 'var(--cv-surface)', borderRadius: '8px', overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', width: `${(metrics.discount_factor_avg || 0) * 100}%`,
                    background: 'linear-gradient(90deg, #0891b2, #06b6d4)',
                    borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 600, fontSize: '0.85rem', color: '#fff', minWidth: '200px',
                  }}>
                    {metrics.risk_adjusted_tonnes?.toLocaleString()} tCO₂e (Risk-Adjusted)
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <AlertTriangle size={14} style={{ color: '#fbbf24' }} />
                  Perda por risco: {((1 - (metrics.discount_factor_avg || 0)) * 100).toFixed(1)}% das toneladas
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)' }}>
                  Diferença: {((metrics.nominal_tonnes || 0) - (metrics.risk_adjusted_tonnes || 0)).toLocaleString()} tCO₂e
                </div>
              </div>
            </div>
          </div>

          {/* Grade Distribution Chart + Simulator */}
          <div className="grid-2">
            <div className="card">
              <div className="card-title" style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <BarChart3 size={18} style={{ color: '#818cf8' }} /> Distribuição por Rating
              </div>
              {gradeChartData.length > 0 && (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={gradeChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                    <XAxis dataKey="grade" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '8px', color: '#e2e8f0' }} />
                    <Bar dataKey="qty" name="Créditos" radius={[4, 4, 0, 0]}>
                      {gradeChartData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Target Impact Calculator */}
            <div className="card">
              <div className="card-title" style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Calculator size={18} style={{ color: '#fbbf24' }} /> Simulador de Impacto
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)', marginBottom: '1rem' }}>
                Quantos créditos nominais você precisa comprar para atingir um impacto climático real?
              </div>
              <label style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Meta de impacto (tCO₂e)</label>
              <input type="number" value={targetImpact} onChange={e => setTargetImpact(Number(e.target.value))}
                style={{ width: '100%', marginBottom: '1rem' }} />

              {riskData?.grade_breakdown && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--cv-border)' }}>
                    <span style={{ color: 'var(--cv-text-muted)', fontSize: '0.85rem' }}>Total nominal necessário:</span>
                    <span style={{ fontWeight: 700 }}>{riskData.total_nominal_needed?.toLocaleString()} tCO₂e</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--cv-border)' }}>
                    <span style={{ color: 'var(--cv-text-muted)', fontSize: '0.85rem' }}>Fator de sobre-compra:</span>
                    <span style={{ fontWeight: 700, color: '#fbbf24' }}>{riskData.over_purchase_ratio?.toFixed(2)}x</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', marginTop: '0.5rem', padding: '0.75rem', background: 'var(--cv-surface)', borderRadius: '8px' }}>
                    💡 Com a composição atual do portfólio, você precisa comprar <strong style={{ color: '#fbbf24' }}>{riskData.over_purchase_ratio?.toFixed(2)}x</strong> mais créditos
                    do que sua meta para compensar o risco de não-entrega.
                  </div>
                </div>
              )}

              {!riskData?.grade_breakdown && (
                <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--cv-text-muted)' }}>
                  Aguardando dados de risco...
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
