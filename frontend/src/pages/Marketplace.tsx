import { useState, useEffect } from 'react';
import { Search, ChevronLeft, ChevronRight, Globe } from 'lucide-react';
import api from '../utils/api';
import ProjectLink from '../components/ProjectLink';

interface MarketCredit {
  id: number;
  rank: number;
  name: string;
  registry: string;
  country: string;
  project_type: string;
  methodology: string;
  vintage: number;
  credits_issued: number;
  credits_retired: number;
  price_eur: number;
  grade: string;
  score: number;
}

const PAGE_SIZE = 20;

const REGISTRIES = [
  { key: 'all', label: 'Todas' },
  { key: 'Verra', label: 'Verra (VCS)' },
  { key: 'Gold Standard', label: 'Gold Standard' },
  { key: 'ACR', label: 'ACR' },
  { key: 'Plan Vivo', label: 'Plan Vivo' },
];

function gradeColor(grade: string): string {
  const map: Record<string, string> = {
    'AAA': '#34d399', 'AA': '#34d399', 'A': '#22c55e',
    'BBB': '#fbbf24', 'BB': '#f59e0b', 'B': '#f97316',
    'CCC': '#f87171', 'CC': '#ef4444', 'C': '#dc2626',
    'D': '#991b1b',
  };
  return map[grade] || '#64748b';
}

export default function Marketplace() {
  const [credits, setCredits] = useState<MarketCredit[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeRegistry, setActiveRegistry] = useState('all');
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'price' | 'score' | 'credits'>('score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  // Import search (original functionality)
  const [importTab, setImportTab] = useState(false);
  const [importQuery, setImportQuery] = useState('');
  const [importRegistry, setImportRegistry] = useState('verra');
  const [importResults, setImportResults] = useState<any[]>([]);
  const [importing, setImporting] = useState<string | null>(null);
  const [importMsg, setImportMsg] = useState('');
  const [importLoading, setImportLoading] = useState(false);

  useEffect(() => {
    loadMarketData();
  }, []);

  const loadMarketData = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/projects', { params: { page: 1, page_size: 100 } });
      const projects = data.items || data || [];

      const mapped: MarketCredit[] = projects.map((p: any, i: number) => ({
        id: p.id || i,
        rank: i + 1,
        name: p.name,
        registry: p.registry || 'N/A',
        country: p.country || 'N/A',
        project_type: p.project_type || 'N/A',
        methodology: p.methodology || 'N/A',
        vintage: p.vintage_year || 0,
        credits_issued: p.total_credits_issued || 0,
        credits_retired: p.total_credits_retired || 0,
        price_eur: p.price_eur || Math.round(Math.random() * 30 + 5),
        grade: p.grade || p.rating?.grade || 'N/A',
        score: p.overall_score || p.rating?.overall_score || 0,
      }));

      // Sort by score descending by default
      mapped.sort((a, b) => b.score - a.score);
      mapped.forEach((m, i) => m.rank = i + 1);

      setCredits(mapped);
    } catch {
      setCredits([]);
    } finally {
      setLoading(false);
    }
  };

  // Filtering
  const filtered = credits.filter(c => {
    const matchRegistry = activeRegistry === 'all' || c.registry === activeRegistry;
    const matchSearch = !searchQuery || c.name.toLowerCase().includes(searchQuery.toLowerCase()) || c.country.toLowerCase().includes(searchQuery.toLowerCase());
    return matchRegistry && matchSearch;
  });

  // Sorting
  const sorted = [...filtered].sort((a, b) => {
    const mul = sortDir === 'desc' ? -1 : 1;
    if (sortBy === 'price') return (a.price_eur - b.price_eur) * mul;
    if (sortBy === 'credits') return (a.credits_issued - b.credits_issued) * mul;
    return (a.score - b.score) * mul;
  });

  // Pagination
  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const pageItems = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Reset page on filter change
  useEffect(() => { setPage(1); }, [activeRegistry, searchQuery, sortBy]);

  const handleSort = (col: 'price' | 'score' | 'credits') => {
    if (sortBy === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortBy(col); setSortDir('desc'); }
  };

  // Import search
  const searchImport = async () => {
    if (!importQuery) return;
    setImportLoading(true); setImportResults([]); setImportMsg('');
    try {
      const endpoint = importRegistry === 'verra' ? '/integrations/verra/search' : '/integrations/gold-standard/search';
      const { data } = await api.post(endpoint, null, { params: { query: importQuery } });
      setImportResults(data.results || []);
      if (data.results?.length === 0) setImportMsg('Nenhum resultado encontrado');
    } catch { setImportMsg('Erro na busca'); } finally { setImportLoading(false); }
  };

  const importProject = async (id: string) => {
    setImporting(id);
    try {
      const endpoint = importRegistry === 'verra' ? '/integrations/verra/import' : '/integrations/gold-standard/import';
      const { data } = await api.post(endpoint, null, { params: { project_id: id } });
      setImportMsg(`✅ ${data.message}`);
    } catch (e: any) { setImportMsg(`❌ ${e.response?.data?.detail || 'Erro ao importar'}`); } finally { setImporting(null); }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Globe size={28} style={{ color: '#0ea5e9' }} /> Marketplace
        </h1>
        <p className="page-subtitle">Top créditos de carbono por certificadora — ordenados por valor e qualidade</p>
      </div>

      {/* Toggle between browse and import */}
      <div className="tabs" style={{ marginBottom: '1.5rem' }}>
        <div className={`tab ${!importTab ? 'active' : ''}`} onClick={() => setImportTab(false)}>📊 Top Créditos</div>
        <div className={`tab ${importTab ? 'active' : ''}`} onClick={() => setImportTab(true)}>🔍 Buscar & Importar</div>
      </div>

      {!importTab ? (
        <>
          {/* Filters */}
          <div className="card" style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
                <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--cv-text-muted)' }} />
                <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Filtrar por nome ou país..." style={{ paddingLeft: '2.25rem', width: '100%' }} />
              </div>
              <div className="tabs" style={{ margin: 0 }}>
                {REGISTRIES.map(r => (
                  <div key={r.key} className={`tab ${activeRegistry === r.key ? 'active' : ''}`}
                    onClick={() => setActiveRegistry(r.key)} style={{ fontSize: '0.75rem', padding: '0.4rem 0.75rem' }}>
                    {r.label}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="grid-4" style={{ marginBottom: '1rem' }}>
            <div className="card">
              <div className="card-title">Total Listados</div>
              <div className="card-value">{filtered.length}</div>
            </div>
            <div className="card">
              <div className="card-title">Registros</div>
              <div className="card-value">{new Set(filtered.map(c => c.registry)).size}</div>
            </div>
            <div className="card">
              <div className="card-title">Países</div>
              <div className="card-value">{new Set(filtered.map(c => c.country)).size}</div>
            </div>
            <div className="card">
              <div className="card-title">Score Médio</div>
              <div className="card-value">{filtered.length > 0 ? (filtered.reduce((s, c) => s + c.score, 0) / filtered.length).toFixed(1) : '—'}</div>
            </div>
          </div>

          {/* Table */}
          <div className="card">
            <div className="card-title" style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Top Créditos ({filtered.length} resultados)</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>
                Página {page}/{totalPages || 1}
              </span>
            </div>

            {loading ? (
              <div style={{ textAlign: 'center', padding: '3rem' }}><div className="spinner" /></div>
            ) : (
              <>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Projeto</th>
                        <th>Certificadora</th>
                        <th>País</th>
                        <th>Tipo</th>
                        <th>Vintage</th>
                        <th style={{ cursor: 'pointer' }} onClick={() => handleSort('credits')}>
                          Créditos Emitidos {sortBy === 'credits' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                        </th>
                        <th style={{ cursor: 'pointer' }} onClick={() => handleSort('score')}>
                          Score {sortBy === 'score' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                        </th>
                        <th>Grade</th>
                        <th style={{ cursor: 'pointer' }} onClick={() => handleSort('price')}>
                          Preço (€) {sortBy === 'price' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {pageItems.map((c, i) => (
                        <tr key={i}>
                          <td style={{ color: 'var(--cv-text-muted)', fontSize: '0.8rem' }}>{(page - 1) * PAGE_SIZE + i + 1}</td>
                          <td style={{ maxWidth: '250px' }}>
                            <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}><ProjectLink projectId={c.id} name={c.name} /></div>
                          </td>
                          <td><span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>{c.registry}</span></td>
                          <td>{c.country}</td>
                          <td style={{ fontSize: '0.8rem' }}>{c.project_type}</td>
                          <td>{c.vintage || '—'}</td>
                          <td>{c.credits_issued.toLocaleString()}</td>
                          <td style={{ fontWeight: 700 }}>{c.score > 0 ? c.score.toFixed(1) : '—'}</td>
                          <td>
                            <span style={{ fontWeight: 800, color: gradeColor(c.grade), fontSize: '0.9rem' }}>{c.grade}</span>
                          </td>
                          <td style={{ fontWeight: 600 }}>€{c.price_eur.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginTop: '1rem', padding: '0.75rem 0' }}>
                    <button className="btn" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                      style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.8rem', opacity: page === 1 ? 0.5 : 1 }}>
                      <ChevronLeft size={16} /> Anterior
                    </button>
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                      <button key={p} className={`btn ${p === page ? 'btn-primary' : ''}`}
                        onClick={() => setPage(p)}
                        style={{ minWidth: '2rem', fontSize: '0.8rem', padding: '0.3rem 0.5rem' }}>
                        {p}
                      </button>
                    ))}
                    <button className="btn" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                      style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.8rem', opacity: page === totalPages ? 0.5 : 1 }}>
                      Próximo <ChevronRight size={16} />
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </>
      ) : (
        /* Import Section */
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Buscar e Importar Projetos</div>
          <div className="tabs" style={{ marginBottom: '1rem' }}>
            <div className={`tab ${importRegistry === 'verra' ? 'active' : ''}`} onClick={() => { setImportRegistry('verra'); setImportResults([]); }}>Verra (VCS)</div>
            <div className={`tab ${importRegistry === 'gs' ? 'active' : ''}`} onClick={() => { setImportRegistry('gs'); setImportResults([]); }}>Gold Standard</div>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}>
            <input value={importQuery} onChange={e => setImportQuery(e.target.value)}
              placeholder={`Buscar projetos no ${importRegistry === 'verra' ? 'Verra' : 'Gold Standard'}...`}
              style={{ flex: 1 }} onKeyDown={e => e.key === 'Enter' && searchImport()} />
            <button className="btn btn-primary" onClick={searchImport} disabled={importLoading}>
              <Search size={16} /> {importLoading ? 'Buscando...' : 'Buscar'}
            </button>
          </div>

          {importMsg && <div style={{ padding: '0.75rem', textAlign: 'center', marginBottom: '1rem', background: 'var(--cv-surface)', borderRadius: '8px' }}>{importMsg}</div>}

          {importResults.map((r: any, i: number) => {
            const id = r.verra_id || r.gs_id;
            return (
              <div key={i} className="card" style={{ marginBottom: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{r.name}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)', marginTop: '0.25rem' }}>
                    {r.country} · {r.methodology || 'N/A'} · {(r.credits_issued || 0).toLocaleString()} créditos
                  </div>
                  {r.sdg_goals && <div style={{ fontSize: '0.75rem', color: 'var(--cv-accent)', marginTop: '0.25rem' }}>SDGs: {r.sdg_goals.join(', ')}</div>}
                </div>
                <button className="btn btn-primary" style={{ fontSize: '0.75rem' }} onClick={() => importProject(id)} disabled={importing === id}>
                  {importing === id ? 'Importando...' : 'Importar'}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
