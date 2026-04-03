import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';
import { ArrowLeft, AlertTriangle } from 'lucide-react';
import api from '../utils/api';

export default function ProjectDetail() {
  const { id } = useParams();
  const [project, setProject] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => { api.get(`/projects/${id}`).then(r => setProject(r.data)).catch(() => {}); }, [id]);

  if (!project) return <div className="loading-page"><div className="spinner" /></div>;

  const r = project.rating;
  const radarData = r ? [
    { dim: 'Adicionalidade', score: r.additionality_score },
    { dim: 'Permanência', score: r.permanence_score },
    { dim: 'Leakage', score: r.leakage_score },
    { dim: 'MRV', score: r.mrv_score },
    { dim: 'Co-benefícios', score: r.co_benefits_score },
    { dim: 'Governança', score: r.governance_score },
    { dim: 'Baseline', score: r.baseline_integrity_score },
  ] : [];

  const forecast = project.credits_forecast;
  const vintageData = forecast?.vintages?.map((v: any) => ({
    year: v.vintage_year, planned: v.planned_quantity, realized: v.realized_quantity || 0, type: v.type,
  })) || [];

  const gradeColor = (g: string) => {
    if (['AAA', 'AA', 'A'].includes(g)) return '#34d399';
    if (['BBB', 'BB'].includes(g)) return '#fbbf24';
    return '#f87171';
  };

  return (
    <div className="fade-in">
      <button className="btn btn-secondary btn-sm" onClick={() => navigate('/projects')} style={{ marginBottom: '1rem' }}>
        <ArrowLeft size={16} /> Voltar
      </button>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">{project.name}</h1>
          <p className="page-subtitle">{project.project_type} · {project.country} {project.registry && `· ${project.registry}`}</p>
        </div>
        {r && <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '2.5rem', fontWeight: 900, color: gradeColor(r.grade) }}>{r.grade}</div>
          <div style={{ fontSize: '0.9rem', color: 'var(--cv-text-muted)' }}>Score: {r.overall_score?.toFixed(1)}/100</div>
        </div>}
      </div>

      {/* Info Cards */}
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="card"><div className="card-title">Créditos Emitidos</div><div className="card-value">{(project.total_credits_issued || 0).toLocaleString()}</div></div>
        <div className="card"><div className="card-title">Aposentados</div><div className="card-value">{(project.total_credits_retired || 0).toLocaleString()}</div></div>
        <div className="card"><div className="card-title">Disponíveis</div><div className="card-value">{(project.total_credits_available || 0).toLocaleString()}</div></div>
        <div className="card"><div className="card-title">Vintage</div><div className="card-value">{project.vintage_year || 'N/A'}</div></div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
        {/* Radar Chart */}
        {r && <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Rating 7 Dimensões</div>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={radarData}><PolarGrid stroke="var(--cv-border)" />
              <PolarAngleAxis dataKey="dim" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Radar dataKey="score" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.2} strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>
        </div>}

        {/* Project Details */}
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Detalhes do Projeto</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.85rem' }}>
            {[['Metodologia', project.methodology], ['Proponente', project.proponent], ['Área (ha)', project.area_hectares?.toLocaleString()],
              ['Buffer %', project.buffer_pool_percentage], ['Monitoramento', project.monitoring_frequency], ['ID Externo', project.external_id],
              ['Latitude', project.latitude?.toFixed(4)], ['Longitude', project.longitude?.toFixed(4)]].map(([k, v]) => (
              <div key={k as string}><div style={{ color: 'var(--cv-text-muted)', fontSize: '0.75rem', marginBottom: '2px' }}>{k}</div><div style={{ fontWeight: 600 }}>{v || 'N/A'}</div></div>
            ))}
          </div>
        </div>
      </div>

      {/* Credit Forecast */}
      {forecast && <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-title" style={{ marginBottom: '1rem' }}>Previsão de Créditos</div>
        <div className="grid-4" style={{ marginBottom: '1rem' }}>
          <div><span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>Taxa Realização</span><div style={{ fontWeight: 700 }}>{forecast.summary.realization_rate_pct}%</div></div>
          <div><span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>Projeção Futura</span><div style={{ fontWeight: 700 }}>{forecast.summary.total_projected_future?.toLocaleString()}</div></div>
          <div><span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>Período</span><div style={{ fontWeight: 700 }}>{forecast.summary.project_start} - {forecast.summary.project_end}</div></div>
          <div><span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>Total Emitidos</span><div style={{ fontWeight: 700 }}>{forecast.summary.total_issued?.toLocaleString()}</div></div>
        </div>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={vintageData}><XAxis dataKey="year" tick={{ fill: '#94a3b8', fontSize: 11 }} /><YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <Bar dataKey="planned" fill="#334155" radius={[4, 4, 0, 0]} name="Planejado" />
            <Bar dataKey="realized" fill="#0ea5e9" radius={[4, 4, 0, 0]} name="Realizado" /><Tooltip />
          </BarChart>
        </ResponsiveContainer>
      </div>}

      {/* Risk Flags */}
      {r?.risk_flags?.length > 0 && <div className="card">
        <div className="card-title" style={{ marginBottom: '1rem' }}><AlertTriangle size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />Flags de Risco ({r.risk_flags.length})</div>
        {r.risk_flags.map((f: any, i: number) => (
          <div key={i} style={{ padding: '0.75rem', background: 'var(--cv-surface)', borderRadius: '8px', marginBottom: '0.5rem', borderLeft: `3px solid ${f.severity === 'high' ? '#f87171' : '#fbbf24'}` }}>
            <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.25rem' }}>{f.message}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)' }}>{f.description}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--cv-primary)', marginTop: '0.25rem' }}>💡 {f.recommendation}</div>
          </div>
        ))}
      </div>}
    </div>
  );
}
