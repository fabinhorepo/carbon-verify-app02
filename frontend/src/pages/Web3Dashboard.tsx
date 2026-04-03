import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../utils/api';

export default function Web3Dashboard() {
  const [pools, setPools] = useState<any>(null);
  const [verifyAddr, setVerifyAddr] = useState('');
  const [verifyResult, setVerifyResult] = useState<any>(null);

  useEffect(() => { api.get('/web3/pool-stats').then(r => setPools(r.data)).catch(() => {}); }, []);

  const verify = () => { if (verifyAddr) api.get('/web3/verify-token', { params: { address: verifyAddr } }).then(r => setVerifyResult(r.data)).catch(() => {}); };

  const poolData = pools?.pools?.map((p: any) => ({
    name: p.name?.replace(/\(.*\)/, '').trim(), locked: p.total_carbon_locked, retired: p.total_retired,
  })) || [];

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">Web3 / Blockchain</h1><p className="page-subtitle">Integração com Toucan Protocol (Polygon)</p></div>

      {/* Pool Stats */}
      <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
        {pools?.pools?.map((p: any, i: number) => (
          <div key={i} className="card glow">
            <div className="card-title">{p.name}</div>
            <div className="grid-2" style={{ marginTop: '0.75rem' }}>
              <div><span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>Carbon Locked</span><div style={{ fontWeight: 800, fontSize: '1.3rem', color: '#34d399' }}>{(p.total_carbon_locked / 1_000_000).toFixed(1)}M tCO₂</div></div>
              <div><span style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)' }}>Retired</span><div style={{ fontWeight: 800, fontSize: '1.3rem', color: '#f87171' }}>{(p.total_retired / 1_000_000).toFixed(1)}M tCO₂</div></div>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', marginTop: '0.75rem', fontFamily: 'monospace' }}>{p.address}</div>
          </div>
        ))}
      </div>

      {/* Pool Chart */}
      {poolData.length > 0 && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div className="card-title" style={{ marginBottom: '1rem' }}>Comparação de Pools</div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={poolData}><XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} /><YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} tickFormatter={(v: number) => `${(v / 1_000_000).toFixed(0)}M`} />
              <Bar dataKey="locked" fill="#34d399" radius={[4, 4, 0, 0]} name="Locked" />
              <Bar dataKey="retired" fill="#f87171" radius={[4, 4, 0, 0]} name="Retired" /><Tooltip /></BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Token Verification */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: '1rem' }}>Verificar Token Address</div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <input value={verifyAddr} onChange={e => setVerifyAddr(e.target.value)} placeholder="0x..." style={{ flex: 1, fontFamily: 'monospace' }} />
          <button className="btn btn-primary" onClick={verify}>Verificar</button>
        </div>
        {verifyResult && (
          <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--cv-surface)', borderRadius: '8px' }}>
            {verifyResult.valid ? (
              <div><span className="badge badge-green">Token Válido</span>
                <div style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>Nome: {verifyResult.token?.name} · Símbolo: {verifyResult.token?.symbol}</div></div>
            ) : <div><span className="badge badge-red">Não Encontrado</span><div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--cv-text-muted)' }}>{verifyResult.message}</div></div>}
          </div>
        )}
      </div>
    </div>
  );
}
