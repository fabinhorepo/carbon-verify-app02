import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import api from '../utils/api';

export default function ESGIntegration() {
  const [balance, setBalance] = useState<any>(null);
  const [recs, setRecs] = useState<any>(null);
  const [projection, setProjection] = useState<any>(null);

  useEffect(() => {
    api.get('/esg/balance').then(r => setBalance(r.data)).catch(() => {});
    api.get('/esg/offset-recommendations').then(r => setRecs(r.data)).catch(() => {});
    api.get('/esg/net-zero-projection').then(r => setProjection(r.data)).catch(() => {});
  }, []);

  const emissionData = balance ? [
    { name: 'Emissões', value: balance.total_emissions_tco2e, fill: '#f87171' },
    { name: 'Offsets', value: balance.total_offsets_tco2e, fill: '#34d399' },
  ] : [];

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">ESG & Plan A</h1><p className="page-subtitle">Pegada de carbono e alinhamento ESG</p></div>

      {balance && (
        <>
          <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
            <div className="card"><div className="card-title">Emissões Totais</div><div className="card-value" style={{ color: '#f87171' }}>{balance.total_emissions_tco2e?.toLocaleString()} t</div></div>
            <div className="card"><div className="card-title">Offsets</div><div className="card-value" style={{ color: '#34d399' }}>{balance.total_offsets_tco2e?.toLocaleString()} t</div></div>
            <div className="card"><div className="card-title">Balanço Líquido</div><div className="card-value" style={{ color: balance.net_balance_tco2e <= 0 ? '#34d399' : '#fbbf24' }}>{balance.net_balance_tco2e?.toLocaleString()} t</div></div>
            <div className="card glow"><div className="card-title">Compensação</div><div className="card-value">{balance.offset_percentage}%</div>
              <div className="card-subtitle">{balance.status === 'net_zero' ? '🎉 Net Zero!' : 'Em progresso'}</div></div>
          </div>

          <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
            <div className="card">
              <div className="card-title" style={{ marginBottom: '1rem' }}>Emissões vs Offsets</div>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart><Pie data={emissionData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                  {emissionData.map((d, i) => <Cell key={i} fill={d.fill} />)}</Pie><Tooltip /></PieChart>
              </ResponsiveContainer>
            </div>
            {projection && projection.projected_net_zero_year && (
              <div className="card">
                <div className="card-title" style={{ marginBottom: '1rem' }}>Projeção Net Zero</div>
                <div style={{ textAlign: 'center', padding: '1rem' }}>
                  <div style={{ fontSize: '3rem', fontWeight: 900, color: 'var(--cv-primary)' }}>{projection.projected_net_zero_year}</div>
                  <div style={{ fontSize: '0.9rem', color: 'var(--cv-text-muted)' }}>{projection.years_remaining} anos restantes</div>
                  <div style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>Redução média: {projection.avg_annual_reduction?.toFixed(0)} tCO₂e/ano</div>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {recs && recs.recommended_projects?.length > 0 && (
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>Projetos Recomendados para Compensação</div>
          <div className="table-wrap"><table><thead><tr><th>Projeto</th><th>País</th><th>Tipo</th><th>Score</th><th>Grade</th><th>Créditos Disponíveis</th></tr></thead>
            <tbody>{recs.recommended_projects.map((p: any) => (
              <tr key={p.project_id}><td style={{ fontWeight: 600 }}>{p.name}</td><td>{p.country}</td>
                <td><span className="badge badge-blue">{p.project_type}</span></td><td>{p.score?.toFixed(1)}</td>
                <td style={{ fontWeight: 800 }}>{p.grade}</td><td>{p.available_credits?.toLocaleString()}</td></tr>
            ))}</tbody></table></div>
        </div>
      )}
    </div>
  );
}
