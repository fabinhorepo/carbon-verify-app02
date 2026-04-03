import { useEffect, useState } from 'react';

import api from '../utils/api';

export default function CarbonAccounting() {
  const [balance, setBalance] = useState<any>(null);
  const [tab, setTab] = useState('overview');
  const [importing, setImporting] = useState(false);
  const [form, setForm] = useState({ scope: '1', amount_tco2e: '', year: '2025', category: '', source_description: '' });

  useEffect(() => { api.get('/esg/balance').then(r => setBalance(r.data)).catch(() => {}); }, []);

  const importEmission = async () => {
    setImporting(true);
    try {
      await api.post('/esg/import-footprint', { emissions: [{ scope: form.scope, amount_tco2e: Number(form.amount_tco2e), year: Number(form.year), category: form.category, source_description: form.source_description }] });
      api.get('/esg/balance').then(r => setBalance(r.data));
      setForm({ ...form, amount_tco2e: '', category: '', source_description: '' });
    } catch (e) {} finally { setImporting(false); }
  };

  const progressPct = balance ? Math.min(100, balance.offset_percentage || 0) : 0;

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Contabilidade de Carbono</h1><p className="page-subtitle">GHG Protocol · Escopo 1, 2 e 3</p></div>

      {balance && (
        <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
          <div className="card"><div className="card-title">Emissões (tCO₂e)</div><div className="card-value" style={{ color: '#f87171' }}>{balance.total_emissions_tco2e?.toLocaleString()}</div></div>
          <div className="card"><div className="card-title">Compensações (tCO₂e)</div><div className="card-value" style={{ color: '#34d399' }}>{balance.total_offsets_tco2e?.toLocaleString()}</div></div>
          <div className="card glow">
            <div className="card-title">Progresso Net Zero</div>
            <div style={{ background: 'var(--cv-surface)', borderRadius: '8px', height: '24px', marginTop: '0.75rem', overflow: 'hidden' }}>
              <div style={{ width: `${progressPct}%`, height: '100%', background: progressPct >= 100 ? '#34d399' : 'linear-gradient(90deg, #0ea5e9, #10b981)', borderRadius: '8px', transition: 'width 0.5s' }}></div>
            </div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, marginTop: '0.5rem' }}>{progressPct.toFixed(1)}% compensado</div>
          </div>
        </div>
      )}

      <div className="tabs">
        {[['overview', 'Visão Geral'], ['import', 'Importar Emissões']].map(([k, v]) => (
          <div key={k} className={`tab ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)}>{v}</div>
        ))}
      </div>

      {tab === 'overview' && balance && (
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Resumo por Escopo</div>
          <div className="grid-3">
            {[['Escopo 1', 'Emissões diretas (combustão, frota)', '#ef4444'],
              ['Escopo 2', 'Energia elétrica consumida', '#f59e0b'],
              ['Escopo 3', 'Cadeia de valor (viagens, compras)', '#8b5cf6']].map(([title, desc, color]) => (
              <div key={title as string} className="card" style={{ borderLeft: `3px solid ${color}` }}>
                <div style={{ fontWeight: 700 }}>{title}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)', marginTop: '0.25rem' }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'import' && (
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Registrar Emissão</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div><label style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Escopo</label>
              <select value={form.scope} onChange={e => setForm({ ...form, scope: e.target.value })}>
                <option value="1">Escopo 1</option><option value="2">Escopo 2</option><option value="3">Escopo 3</option>
              </select></div>
            <div><label style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Quantidade (tCO₂e)</label>
              <input type="number" value={form.amount_tco2e} onChange={e => setForm({ ...form, amount_tco2e: e.target.value })} /></div>
            <div><label style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Ano</label>
              <input type="number" value={form.year} onChange={e => setForm({ ...form, year: e.target.value })} /></div>
            <div><label style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Categoria</label>
              <input value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} placeholder="Ex: Frota, Energia" /></div>
            <div style={{ gridColumn: 'span 2' }}><label style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', display: 'block', marginBottom: '0.25rem' }}>Descrição</label>
              <input value={form.source_description} onChange={e => setForm({ ...form, source_description: e.target.value })} style={{ width: '100%' }} /></div>
          </div>
          <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={importEmission} disabled={importing || !form.amount_tco2e}>
            {importing ? 'Importando...' : 'Registrar Emissão'}
          </button>
        </div>
      )}
    </div>
  );
}
