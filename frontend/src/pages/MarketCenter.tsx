import { useEffect, useState } from 'react';
import { XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { TrendingUp, TrendingDown } from 'lucide-react';
import api from '../utils/api';

export default function MarketCenter() {
  const [price, setPrice] = useState<any>(null);
  const [history, setHistory] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [impact, setImpact] = useState<any>(null);
  const [simPct, setSimPct] = useState(0);
  const [period, setPeriod] = useState('7d');

  useEffect(() => {
    api.get('/market/carbon-price').then(r => setPrice(r.data)).catch(() => {});
    api.get('/market/summary').then(r => setSummary(r.data)).catch(() => {});
    api.get('/market/price-history', { params: { period } }).then(r => setHistory(r.data)).catch(() => {});
  }, [period]);

  const simulate = () => api.get('/market/portfolio-impact', { params: { price_change_pct: simPct } }).then(r => setImpact(r.data)).catch(() => {});
  useEffect(() => { simulate(); }, []);

  if (!price) return <div className="loading-page"><div className="spinner" /></div>;
  const ch = price.change_pct_24h || 0;
  const up = ch >= 0;

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Centro de Mercado</h1><p className="page-subtitle">Cotações e análise de mercado de carbono</p></div>

      <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
        <div className="card glow" style={{ gridColumn: 'span 2' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div className="card-title">EU ETS · EUA Futures</div>
              <div className="card-value" style={{ fontSize: '2.5rem', color: up ? '#34d399' : '#f87171' }}>€{price.price_eur?.toFixed(2)}</div>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.85rem' }}>
                <span style={{ color: up ? '#34d399' : '#f87171' }}>{up ? <TrendingUp size={14} style={{ display: 'inline' }} /> : <TrendingDown size={14} style={{ display: 'inline' }} />} {up ? '+' : ''}{ch.toFixed(2)}%</span>
                <span style={{ color: 'var(--cv-text-muted)' }}>Fechamento: €{price.previous_close_eur?.toFixed(2)}</span>
              </div>
            </div>
            <div style={{ textAlign: 'right', fontSize: '0.8rem', color: 'var(--cv-text-muted)' }}>
              <div>High: €{price.day_high_eur?.toFixed(2) || '—'}</div>
              <div>Low: €{price.day_low_eur?.toFixed(2) || '—'}</div>
              <div>Fonte: {price.source}</div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-title">Mercados Voluntários</div>
          {summary?.voluntary_markets && Object.entries(summary.voluntary_markets).map(([k, v]: any) => (
            <div key={k} style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--cv-border)' }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{v.name}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--cv-accent)' }}>{v.avg_price_range}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>{v.description}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Price History */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div className="card-title">Histórico de Preços</div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {['24h', '7d', '30d'].map(p => (
              <button key={p} className={`btn btn-sm ${period === p ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setPeriod(p)}>{p}</button>
            ))}
          </div>
        </div>
        {history?.data?.length > 0 ? (
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={history.data}><XAxis dataKey="recorded_at" tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={(v: string) => v?.split('T')[0]?.slice(5) || ''} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={['auto', 'auto']} />
              <Area type="monotone" dataKey="price_eur" stroke="#0ea5e9" fill="rgba(14,165,233,0.1)" strokeWidth={2} /><Tooltip /></AreaChart>
          </ResponsiveContainer>
        ) : <p style={{ color: 'var(--cv-text-muted)', textAlign: 'center', padding: '2rem' }}>Dados históricos serão acumulados ao longo do tempo</p>}
      </div>

      {/* Portfolio Impact Simulator */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: '1rem' }}>Simulador de Impacto no Portfólio</div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--cv-text-muted)' }}>Se o preço variar</label>
          <input type="range" min="-30" max="30" value={simPct} onChange={e => setSimPct(Number(e.target.value))} style={{ flex: 1 }} />
          <span style={{ fontWeight: 700, fontSize: '1.1rem', color: simPct >= 0 ? '#34d399' : '#f87171', minWidth: '60px' }}>{simPct >= 0 ? '+' : ''}{simPct}%</span>
          <button className="btn btn-primary btn-sm" onClick={simulate}>Simular</button>
        </div>
        {impact && (
          <div className="grid-4">
            <div><span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>Preço Atual</span><div style={{ fontWeight: 700 }}>€{impact.current_price_eur?.toFixed(2)}</div></div>
            <div><span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>Preço Simulado</span><div style={{ fontWeight: 700 }}>€{impact.simulated_price_eur?.toFixed(2)}</div></div>
            <div><span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>Valor Portfólio</span><div style={{ fontWeight: 700 }}>€{impact.simulated_portfolio_value?.toLocaleString()}</div></div>
            <div><span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>Variação</span><div style={{ fontWeight: 700, color: impact.value_change_eur >= 0 ? '#34d399' : '#f87171' }}>{impact.value_change_eur >= 0 ? '+' : ''}€{impact.value_change_eur?.toLocaleString()}</div></div>
          </div>
        )}
      </div>
    </div>
  );
}
