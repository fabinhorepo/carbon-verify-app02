import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../utils/api';
import ProjectLink from '../components/ProjectLink';

const COLORS = ['#34d399', '#fbbf24', '#f87171', '#38bdf8', '#c084fc', '#fb923c'];

export default function Portfolio() {
  const [portfolios, setPortfolios] = useState<any[]>([]);
  const [detail, setDetail] = useState<any>(null);
  const [error, setError] = useState(false);
  const [activeRecTab, setActiveRecTab] = useState('sell');

  useEffect(() => {
    api.get('/portfolios').then(r => {
      const list = r.data || [];
      setPortfolios(list);
      if (list.length > 0) loadDetail(list[0].id);
      else setError(true);
    }).catch(() => setError(true));
  }, []);

  const loadDetail = (id: number) => {
    api.get(`/portfolios/${id}`).then(r => setDetail(r.data)).catch(() => setError(true));
  };

  if (error && !detail) return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Portfólio</h1><p className="page-subtitle">Gestão de créditos de carbono</p></div>
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
        <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '0.5rem' }}>Nenhum portfólio encontrado</div>
        <div style={{ color: 'var(--cv-text-muted)' }}>Crie um portfólio na API ou aguarde o carregamento dos dados.</div>
      </div>
    </div>
  );

  if (!detail) return <div className="loading-page"><div className="spinner" /></div>;

  const m = detail.metrics;
  const typeData = Object.entries(m.project_type_distribution || {}).map(([k, v]) => ({ name: k, value: v as number }));
  const gradeData = Object.entries(m.grade_distribution || {}).map(([k, v]) => ({ name: k, value: v as number }));
  const recs = m.recommendations_grouped || {};
  const actionLabels: any = { sell: '🔴 Vender', rebalance: '🟡 Rebalancear', hold: '🟢 Manter' };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Portfólio</h1>
        <p className="page-subtitle">{detail.portfolio.name}</p>
        {portfolios.length > 1 && (
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            {portfolios.map(p => (
              <button key={p.id} className={`btn ${p.id === detail?.portfolio?.id ? 'btn-primary' : ''}`}
                style={{ fontSize: '0.75rem', padding: '0.25rem 0.75rem' }}
                onClick={() => loadDetail(p.id)}>{p.name}</button>
            ))}
          </div>
        )}
      </div>

      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="card"><div className="card-title">Total Créditos</div><div className="card-value">{m.total_credits?.toLocaleString()}</div></div>
        <div className="card"><div className="card-title">Valor Total</div><div className="card-value">€{m.total_value_eur?.toLocaleString()}</div></div>
        <div className="card"><div className="card-title">Score Médio</div><div className="card-value">{m.avg_quality_score?.toFixed(1)}</div></div>
        <div className="card"><div className="card-title">Recomendações</div><div className="card-value">{m.total_recommendations}</div></div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Por Tipo</div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart><Pie data={typeData} cx="50%" cy="50%" innerRadius={40} outerRadius={75} dataKey="value" label={({ name }) => name}>
              {typeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /></PieChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Por Grade</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={gradeData}><XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} /><YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Bar dataKey="value" fill="#0ea5e9" radius={[4, 4, 0, 0]} /><Tooltip /></BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recommendations */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-title" style={{ marginBottom: '1rem' }}>Recomendações</div>
        <div className="tabs">
          {Object.keys(recs).map(a => (
            <div key={a} className={`tab ${activeRecTab === a ? 'active' : ''}`} onClick={() => setActiveRecTab(a)}>
              {actionLabels[a] || a} ({recs[a]?.total || 0})
            </div>
          ))}
        </div>
        {recs[activeRecTab]?.items?.map((r: any, i: number) => (
          <div key={i} className="card" style={{ marginBottom: '0.5rem', borderLeft: `3px solid ${r.risk_level === 'high' ? '#f87171' : r.risk_level === 'medium' ? '#fbbf24' : '#34d399'}` }}>
            <div style={{ fontWeight: 700, fontSize: '0.9rem' }}><ProjectLink projectId={r.project_id || 0} name={r.project_name} /></div>
            <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)', marginTop: '0.25rem' }}>Score: {r.current_score?.toFixed(0)} · Grade: {r.current_grade} · {r.total_quantity?.toLocaleString()} créditos</div>
            <div style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>{r.reason}</div>
          </div>
        ))}
      </div>

      {/* Positions Table */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: '1rem' }}>Posições</div>
        <div className="table-wrap">
          <table><thead><tr><th>Projeto</th><th>Tipo</th><th>País</th><th>Quantidade</th><th>Score</th><th>Grade</th><th>Preço (€)</th></tr></thead>
            <tbody>{m.positions?.map((p: any) => (
              <tr key={p.position_id}><td><ProjectLink projectId={p.project_id || 0} name={p.project_name} /></td><td><span className="badge badge-blue">{p.project_type}</span></td>
                <td>{p.country}</td><td>{p.quantity?.toLocaleString()}</td><td>{p.score?.toFixed(1)}</td><td style={{ fontWeight: 800 }}>{p.grade}</td><td>€{p.price_eur?.toFixed(2)}</td></tr>
            ))}</tbody></table>
        </div>
      </div>
    </div>
  );
}
