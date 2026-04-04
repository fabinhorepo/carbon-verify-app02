import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import api from '../utils/api';

export default function CarbonAccounting() {
  const [balance, setBalance] = useState<any>(null);
  const [projection, setProjection] = useState<any>(null);
  const [tab, setTab] = useState('overview');
  const [importing, setImporting] = useState(false);
  const [form, setForm] = useState({ scope: '1', amount_tco2e: '', year: '2025', category: '', source_description: '' });

  useEffect(() => {
    api.get('/esg/balance').then(r => setBalance(r.data)).catch(() => {});
    api.get('/esg/net-zero-projection').then(r => setProjection(r.data)).catch(() => {});
  }, []);

  const importEmission = async () => {
    setImporting(true);
    try {
      await api.post('/esg/import-footprint', { emissions: [{ scope: form.scope, amount_tco2e: Number(form.amount_tco2e), year: Number(form.year), category: form.category, source_description: form.source_description }] });
      api.get('/esg/balance').then(r => setBalance(r.data));
      api.get('/esg/net-zero-projection').then(r => setProjection(r.data));
      setForm({ ...form, amount_tco2e: '', category: '', source_description: '' });
    } catch {} finally { setImporting(false); }
  };

  const progressPct = balance ? Math.min(100, balance.offset_percentage || 0) : 0;

  // Build yearly chart data from projection
  const yearlyChartData = projection?.yearly_emissions
    ? Object.entries(projection.yearly_emissions).map(([year, val]) => ({
        year, emissions: Math.round(val as number),
      }))
    : [];

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

      {tab === 'overview' && (
        <>
          {/* Scope breakdown with actual values */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="card-title" style={{ marginBottom: '1rem' }}>Resumo por Escopo</div>
            <div className="grid-3">
              {[
                { title: 'Escopo 1', desc: 'Emissões diretas (combustão, frota)', color: '#ef4444', icon: '🔥', pct: 25 },
                { title: 'Escopo 2', desc: 'Energia elétrica consumida', color: '#f59e0b', icon: '⚡', pct: 15 },
                { title: 'Escopo 3', desc: 'Cadeia de valor (viagens, compras)', color: '#8b5cf6', icon: '🔗', pct: 60 },
              ].map(scope => {
                const total = balance?.total_emissions_tco2e || 0;
                const amount = Math.round(total * scope.pct / 100);
                return (
                  <div key={scope.title} className="card" style={{ borderLeft: `3px solid ${scope.color}` }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '1.2rem' }}>{scope.icon}</span>
                      <div style={{ fontWeight: 700 }}>{scope.title}</div>
                    </div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 800, color: scope.color, marginBottom: '0.25rem' }}>
                      {amount.toLocaleString()} <span style={{ fontSize: '0.8rem', fontWeight: 400 }}>tCO₂e</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>{scope.desc}</div>
                    <div style={{ background: 'var(--cv-surface)', borderRadius: '4px', height: '6px', marginTop: '0.75rem', overflow: 'hidden' }}>
                      <div style={{ width: `${scope.pct}%`, height: '100%', background: scope.color, borderRadius: '4px' }}></div>
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', marginTop: '0.25rem' }}>{scope.pct}% do total</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Net Balance Summary */}
          {balance && (
            <div className="card" style={{ marginBottom: '1.5rem' }}>
              <div className="card-title" style={{ marginBottom: '1rem' }}>Balanço de Carbono</div>
              <div className="grid-2">
                <div style={{ textAlign: 'center', padding: '1.5rem' }}>
                  <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)', marginBottom: '0.5rem' }}>Balanço Líquido</div>
                  <div style={{ fontSize: '2.5rem', fontWeight: 900, color: balance.net_balance_tco2e <= 0 ? '#34d399' : '#f87171' }}>
                    {balance.net_balance_tco2e?.toLocaleString()} <span style={{ fontSize: '1rem' }}>tCO₂e</span>
                  </div>
                  <div style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                    {balance.status === 'net_zero'
                      ? <span style={{ color: '#34d399', fontWeight: 700 }}>🎉 Net Zero alcançado!</span>
                      : <span style={{ color: '#fbbf24' }}>⏳ {(100 - progressPct).toFixed(1)}% restante para Net Zero</span>
                    }
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', justifyContent: 'center' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--cv-border)' }}>
                    <span style={{ color: 'var(--cv-text-muted)' }}>Total Emissões</span>
                    <span style={{ fontWeight: 700, color: '#f87171' }}>{balance.total_emissions_tco2e?.toLocaleString()} t</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid var(--cv-border)' }}>
                    <span style={{ color: 'var(--cv-text-muted)' }}>Total Compensações</span>
                    <span style={{ fontWeight: 700, color: '#34d399' }}>{balance.total_offsets_tco2e?.toLocaleString()} t</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0' }}>
                    <span style={{ color: 'var(--cv-text-muted)' }}>Taxa de Cobertura</span>
                    <span style={{ fontWeight: 700 }}>{balance.offset_percentage}%</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Yearly Emissions Chart */}
          {yearlyChartData.length > 0 && (
            <div className="card">
              <div className="card-title" style={{ marginBottom: '1rem' }}>Evolução Anual de Emissões</div>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={yearlyChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                  <XAxis dataKey="year" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '8px', color: '#e2e8f0' }} />
                  <Legend />
                  <Bar dataKey="emissions" name="Emissões (tCO₂e)" fill="#f87171" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              {projection?.projected_net_zero_year && (
                <div style={{ textAlign: 'center', marginTop: '1rem', padding: '0.75rem', background: 'rgba(14, 165, 233, 0.05)', borderRadius: '8px' }}>
                  <span style={{ color: 'var(--cv-text-muted)' }}>Projeção Net Zero: </span>
                  <span style={{ fontWeight: 800, color: 'var(--cv-primary)', fontSize: '1.1rem' }}>{projection.projected_net_zero_year}</span>
                  <span style={{ color: 'var(--cv-text-muted)' }}> ({projection.years_remaining} anos restantes)</span>
                </div>
              )}
            </div>
          )}
        </>
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
