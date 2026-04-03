import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Briefcase, FolderKanban, ShieldAlert } from 'lucide-react';
import api from '../utils/api';

const COLORS = ['#34d399', '#fbbf24', '#f87171', '#38bdf8', '#c084fc', '#fb923c', '#818cf8'];

export default function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [price, setPrice] = useState<any>(null);
  const [riskMatrix, setRiskMatrix] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/dashboard/metrics').then(r => setMetrics(r.data)).catch(() => {});
    api.get('/market/carbon-price').then(r => setPrice(r.data)).catch(() => {});
    api.get('/dashboard/risk-matrix').then(r => setRiskMatrix(r.data)).catch(() => {});
  }, []);

  if (!metrics) return <div className="loading-page"><div className="spinner" /><p>Carregando dashboard...</p></div>;

  const gradeData = Object.entries(metrics.grade_distribution || {}).map(([k, v]) => ({ name: k, value: v as number }));
  const typeData = Object.entries(metrics.project_type_distribution || {}).map(([k, v]) => ({ name: k, value: v as number }));

  const riskData = metrics.risk_summary ? [
    { name: 'Alto Risco', value: metrics.risk_summary.high_risk, fill: '#f87171' },
    { name: 'Médio', value: metrics.risk_summary.medium_risk, fill: '#fbbf24' },
    { name: 'Baixo', value: metrics.risk_summary.low_risk, fill: '#34d399' },
  ] : [];

  const priceChange = price?.change_pct_24h || 0;
  const priceColor = priceChange >= 0 ? '#34d399' : '#f87171';

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Visão geral do sistema Carbon Verify</p>
      </div>

      {/* KPI Cards */}
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="card" onClick={() => navigate('/projects')} style={{ cursor: 'pointer' }}>
          <div className="card-header"><span className="card-title">Projetos</span><FolderKanban size={18} color="var(--cv-primary)" /></div>
          <div className="card-value">{metrics.total_projects}</div>
          <div className="card-subtitle">Score médio: {metrics.avg_quality_score?.toFixed(1)}</div>
        </div>
        <div className="card">
          <div className="card-header"><span className="card-title">Créditos</span><Briefcase size={18} color="var(--cv-accent)" /></div>
          <div className="card-value">{(metrics.total_credits || 0).toLocaleString()}</div>
          <div className="card-subtitle">Portfólio: €{(metrics.portfolio_value_eur || 0).toLocaleString()}</div>
        </div>
        <div className="card" onClick={() => navigate('/fraud-alerts')} style={{ cursor: 'pointer' }}>
          <div className="card-header"><span className="card-title">Alertas Fraude</span><ShieldAlert size={18} color="var(--cv-danger)" /></div>
          <div className="card-value">{metrics.fraud_alerts_count}</div>
          <div className="card-subtitle">
            {Object.entries(metrics.fraud_alerts_by_severity || {}).map(([k, v]) => `${k}: ${v}`).join(' · ')}
          </div>
        </div>
        <div className="card glow" onClick={() => navigate('/market')} style={{ cursor: 'pointer' }}>
          <div className="card-header"><span className="card-title">EU ETS</span>
            {priceChange >= 0 ? <TrendingUp size={18} color={priceColor} /> : <TrendingDown size={18} color={priceColor} />}
          </div>
          <div className="card-value" style={{ color: priceColor }}>€{price?.price_eur?.toFixed(2) || '—'}</div>
          <div className="card-subtitle" style={{ color: priceColor }}>{priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)}% (24h)</div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Distribuição de Grades</div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart><Pie data={gradeData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
              {gradeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie><Tooltip /></PieChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Exposição a Risco</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={riskData}><XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} /><YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>{riskData.map((d, i) => <Cell key={i} fill={d.fill} />)}</Bar><Tooltip />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Por Tipo de Projeto</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={typeData} layout="vertical"><YAxis type="category" dataKey="name" width={100} tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} /><Bar dataKey="value" fill="#0ea5e9" radius={[0, 4, 4, 0]} /><Tooltip />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Risk Matrix */}
      {riskMatrix && (
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Matriz de Risco vs Qualidade</div>
          <div className="grid-4" style={{ gap: '0.5rem' }}>
            {['high', 'medium', 'low'].map(quality => (
              ['none', 'low', 'medium', 'high'].map(risk => {
                const cell = riskMatrix.grid?.[quality]?.[risk];
                const count = cell?.count || 0;
                const bg = count === 0 ? 'var(--cv-surface)' : quality === 'high' && risk === 'none' ? 'rgba(16,185,129,0.1)' : quality === 'low' && risk === 'high' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.1)';
                return (
                  <div key={`${quality}-${risk}`} style={{ background: bg, borderRadius: '8px', padding: '0.75rem', textAlign: 'center', border: '1px solid var(--cv-border)' }}>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>{count}</div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--cv-text-muted)' }}>{quality.charAt(0).toUpperCase()}{quality.slice(1)} Q / {risk} R</div>
                  </div>
                );
              })
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
