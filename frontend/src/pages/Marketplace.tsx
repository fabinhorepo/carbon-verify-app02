import { useState } from 'react';
import { Search } from 'lucide-react';
import api from '../utils/api';

export default function Marketplace() {
  const [tab, setTab] = useState('verra');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState<string | null>(null);
  const [msg, setMsg] = useState('');

  const search = async () => {
    if (!query) return;
    setLoading(true); setResults([]); setMsg('');
    try {
      const endpoint = tab === 'verra' ? '/integrations/verra/search' : '/integrations/gold-standard/search';
      const { data } = await api.post(endpoint, null, { params: { query } });
      setResults(data.results || []);
      if (data.results?.length === 0) setMsg('Nenhum resultado encontrado');
    } catch (e) { setMsg('Erro na busca'); } finally { setLoading(false); }
  };

  const importProject = async (id: string) => {
    setImporting(id);
    try {
      const endpoint = tab === 'verra' ? '/integrations/verra/import' : '/integrations/gold-standard/import';
      const { data } = await api.post(endpoint, null, { params: { project_id: id } });
      setMsg(`✅ ${data.message}`);
    } catch (e: any) { setMsg(`❌ ${e.response?.data?.detail || 'Erro ao importar'}`); } finally { setImporting(null); }
  };

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Marketplace</h1><p className="page-subtitle">Busque e importe projetos de registros certificados</p></div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="tabs" style={{ marginBottom: '1rem' }}>
          <div className={`tab ${tab === 'verra' ? 'active' : ''}`} onClick={() => { setTab('verra'); setResults([]); }}>Verra (VCS)</div>
          <div className={`tab ${tab === 'gs' ? 'active' : ''}`} onClick={() => { setTab('gs'); setResults([]); }}>Gold Standard</div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder={`Buscar projetos no ${tab === 'verra' ? 'Verra' : 'Gold Standard'}...`} style={{ flex: 1 }} onKeyDown={e => e.key === 'Enter' && search()} />
          <button className="btn btn-primary" onClick={search} disabled={loading}><Search size={16} />{loading ? 'Buscando...' : 'Buscar'}</button>
        </div>
      </div>

      {msg && <div className="card" style={{ marginBottom: '1rem', padding: '1rem', textAlign: 'center' }}>{msg}</div>}

      {results.length > 0 && (
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>{results.length} resultados</div>
          {results.map((r: any, i: number) => {
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
                <button className="btn btn-primary btn-sm" onClick={() => importProject(id)} disabled={importing === id}>
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
