import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';

export default function Projects() {
  const [data, setData] = useState<any>(null);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ project_type: '', country: '', search: '', min_score: '', max_score: '' });
  const [sortField, setSortField] = useState('');
  const [sortDir, setSortDir] = useState('asc');
  const navigate = useNavigate();

  const load = () => {
    const params: any = { page, page_size: 20 };
    if (filters.project_type) params.project_type = filters.project_type;
    if (filters.country) params.country = filters.country;
    if (filters.search) params.search = filters.search;
    if (filters.min_score) params.min_score = filters.min_score;
    if (filters.max_score) params.max_score = filters.max_score;
    if (sortField) { params.sort_field = sortField; params.sort_dir = sortDir; }
    api.get('/projects', { params }).then(r => setData(r.data)).catch(() => {});
  };

  useEffect(() => { load(); }, [page, sortField, sortDir]);

  const gradeClass = (g: string) => `grade-${g?.toLowerCase().replace(/\+/g, '')}`;
  const handleSort = (f: string) => { setSortDir(sortField === f && sortDir === 'asc' ? 'desc' : 'asc'); setSortField(f); };

  if (!data) return <div className="loading-page"><div className="spinner" /></div>;

  return (
    <div className="fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div><h1 className="page-title">Projetos de Carbono</h1><p className="page-subtitle">{data.total} projetos encontrados</p></div>
      </div>
      {/* Filters */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div><label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Buscar</label>
            <input value={filters.search} onChange={e => setFilters({ ...filters, search: e.target.value })} placeholder="Nome do projeto..." style={{ width: '200px' }} /></div>
          <div><label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Tipo</label>
            <select value={filters.project_type} onChange={e => setFilters({ ...filters, project_type: e.target.value })} style={{ width: '160px' }}>
              <option value="">Todos</option>
              {['REDD+', 'ARR', 'Renewable Energy', 'Cookstove', 'Methane Avoidance', 'Blue Carbon', 'Biochar', 'Direct Air Capture', 'Other'].map(t => <option key={t} value={t}>{t}</option>)}
            </select></div>
          <div><label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Score mín</label>
            <input type="number" value={filters.min_score} onChange={e => setFilters({ ...filters, min_score: e.target.value })} style={{ width: '80px' }} /></div>
          <div><label style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Score máx</label>
            <input type="number" value={filters.max_score} onChange={e => setFilters({ ...filters, max_score: e.target.value })} style={{ width: '80px' }} /></div>
          <button className="btn btn-primary btn-sm" onClick={() => { setPage(1); load(); }}>Filtrar</button>
          <button className="btn btn-secondary btn-sm" onClick={() => { setFilters({ project_type: '', country: '', search: '', min_score: '', max_score: '' }); setPage(1); setTimeout(load, 100); }}>Limpar</button>
        </div>
      </div>
      {/* Table */}
      <div className="table-wrap">
        <table>
          <thead><tr>
            <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>Nome {sortField === 'name' ? (sortDir === 'asc' ? '↑' : '↓') : ''}</th>
            <th onClick={() => handleSort('project_type')} style={{ cursor: 'pointer' }}>Tipo</th>
            <th onClick={() => handleSort('country')} style={{ cursor: 'pointer' }}>País</th>
            <th>Registry</th>
            <th onClick={() => handleSort('credits')} style={{ cursor: 'pointer' }}>Créditos</th>
            <th onClick={() => handleSort('score')} style={{ cursor: 'pointer' }}>Score</th>
            <th>Grade</th>
            <th>Alertas</th>
          </tr></thead>
          <tbody>
            {data.items?.map((p: any) => (
              <tr key={p.id} onClick={() => navigate(`/projects/${p.id}`)} style={{ cursor: 'pointer' }}>
                <td style={{ fontWeight: 600, maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--cv-accent)', cursor: 'pointer' }}>{p.name}</td>
                <td><span className="badge badge-blue">{p.project_type}</span></td>
                <td>{p.country}</td>
                <td>{p.registry || '—'}</td>
                <td>{(p.total_credits_issued || 0).toLocaleString()}</td>
                <td style={{ fontWeight: 700 }}>{p.rating?.overall_score?.toFixed(1) || '—'}</td>
                <td><span className={`${gradeClass(p.rating?.grade || 'N/A')}`} style={{ fontWeight: 800, fontSize: '0.9rem' }}>{p.rating?.grade || 'N/A'}</span></td>
                <td>{p.fraud_alert_count > 0 ? <span className="badge badge-red">{p.fraud_alert_count}</span> : <span className="badge badge-green">0</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {/* Pagination */}
      <div className="pagination">
        <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Anterior</button>
        <span style={{ fontSize: '0.85rem', color: 'var(--cv-text-muted)' }}>Página {page} de {data.total_pages}</span>
        <button disabled={page >= data.total_pages} onClick={() => setPage(p => p + 1)}>Próxima →</button>
      </div>
    </div>
  );
}
