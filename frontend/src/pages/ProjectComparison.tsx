import { useEffect, useState } from 'react';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts';
import api from '../utils/api';

export default function ProjectComparison() {
  const [projects, setProjects] = useState<any[]>([]);
  const [allProjects, setAllProjects] = useState<any[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  useEffect(() => { api.get('/projects', { params: { page_size: 100 } }).then(r => setAllProjects(r.data.items || [])).catch(() => {}); }, []);

  const compare = () => {
    if (selectedIds.length < 2) return;
    api.get('/projects/compare', { params: { ids: selectedIds.join(',') } }).then(r => setProjects(r.data)).catch(() => {});
  };

  const toggleProject = (id: number) => setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 4 ? [...prev, id] : prev);
  const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444'];
  const dims = ['additionality_score', 'permanence_score', 'leakage_score', 'mrv_score', 'co_benefits_score', 'governance_score', 'baseline_integrity_score'];
  const dimLabels: any = { additionality_score: 'Adicionalidade', permanence_score: 'Permanência', leakage_score: 'Leakage', mrv_score: 'MRV', co_benefits_score: 'Co-benefícios', governance_score: 'Governança', baseline_integrity_score: 'Baseline' };

  const radarData = dims.map(d => {
    const point: any = { dim: dimLabels[d] };
    projects.forEach((p, i) => { if (p.rating) point[`p${i}`] = p.rating[d]; });
    return point;
  });

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Comparador de Projetos</h1><p className="page-subtitle">Selecione 2-4 projetos para comparar</p></div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          {allProjects.slice(0, 30).map(p => (
            <button key={p.id} onClick={() => toggleProject(p.id)}
              className={`btn btn-sm ${selectedIds.includes(p.id) ? 'btn-primary' : 'btn-secondary'}`}>
              {p.name?.slice(0, 25)}{p.name?.length > 25 ? '...' : ''}
            </button>
          ))}
        </div>
        <button className="btn btn-primary" onClick={compare} disabled={selectedIds.length < 2}>Comparar ({selectedIds.length})</button>
      </div>

      {projects.length >= 2 && (
        <>
          {/* Radar */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="card-title" style={{ marginBottom: '1rem' }}>Comparação Radar</div>
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem' }}>
              {projects.map((p, i) => <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}><div style={{ width: 12, height: 12, borderRadius: '50%', background: COLORS[i] }}></div>{p.name?.slice(0, 30)}</div>)}
            </div>
            <ResponsiveContainer width="100%" height={350}>
              <RadarChart data={radarData}><PolarGrid stroke="var(--cv-border)" /><PolarAngleAxis dataKey="dim" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                {projects.map((_, i) => <Radar key={i} dataKey={`p${i}`} stroke={COLORS[i]} fill={COLORS[i]} fillOpacity={0.1} strokeWidth={2} />)}
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Comparison Table */}
          <div className="card">
            <div className="card-title" style={{ marginBottom: '1rem' }}>Tabela Comparativa</div>
            <div className="table-wrap"><table><thead><tr><th>Atributo</th>{projects.map((p, i) => <th key={i} style={{ color: COLORS[i] }}>{p.name?.slice(0, 20)}</th>)}</tr></thead>
              <tbody>
                {[['Score', (p: any) => p.rating?.overall_score?.toFixed(1) || 'N/A'], ['Grade', (p: any) => p.rating?.grade || 'N/A'],
                  ['Tipo', (p: any) => p.project_type], ['País', (p: any) => p.country], ['Registry', (p: any) => p.registry || 'N/A'],
                  ['Créditos', (p: any) => (p.total_credits_issued || 0).toLocaleString()], ['Vintage', (p: any) => p.vintage_year || 'N/A'],
                  ['Área (ha)', (p: any) => p.area_hectares?.toLocaleString() || 'N/A'], ['Alertas', (p: any) => p.fraud_alert_count || 0],
                ].map(([label, fn]: any) => (
                  <tr key={label}><td style={{ fontWeight: 600 }}>{label}</td>{projects.map((p, i) => <td key={i}>{fn(p)}</td>)}</tr>
                ))}
              </tbody></table></div>
          </div>
        </>
      )}
    </div>
  );
}
