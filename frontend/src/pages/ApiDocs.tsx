import { useState } from 'react';


const API_SECTIONS = [
  { cat: 'Autenticação', endpoints: [
    { method: 'POST', path: '/api/v1/auth/register', desc: 'Criar conta e organização' },
    { method: 'POST', path: '/api/v1/auth/login', desc: 'Login com email/senha' },
    { method: 'GET', path: '/api/v1/auth/me', desc: 'Perfil do usuário autenticado' },
  ]},
  { cat: 'Projetos de Carbono', endpoints: [
    { method: 'GET', path: '/api/v1/projects', desc: 'Listar projetos com filtros e paginação' },
    { method: 'GET', path: '/api/v1/projects/geo', desc: 'Dados geográficos para mapa' },
    { method: 'GET', path: '/api/v1/projects/compare?ids=1,2,3', desc: 'Comparar projetos side-by-side' },
    { method: 'GET', path: '/api/v1/projects/{id}', desc: 'Detalhes completos com forecast' },
    { method: 'GET', path: '/api/v1/projects/{id}/rating', desc: 'Rating 7 dimensões' },
    { method: 'POST', path: '/api/v1/projects/{id}/recalculate-rating', desc: 'Recalcular rating' },
  ]},
  { cat: 'Fraud Detection', endpoints: [
    { method: 'GET', path: '/api/v1/fraud-alerts', desc: 'Alertas com filtros' },
    { method: 'GET', path: '/api/v1/fraud-alerts/grouped-by-type', desc: 'Agrupados com explicações' },
    { method: 'GET', path: '/api/v1/fraud-alerts/summary', desc: 'Resumo por severidade' },
  ]},
  { cat: 'Portfólio', endpoints: [
    { method: 'GET', path: '/api/v1/portfolios', desc: 'Listar portfólios' },
    { method: 'GET', path: '/api/v1/portfolios/{id}', desc: 'Métricas detalhadas' },
    { method: 'GET', path: '/api/v1/dashboard/metrics', desc: 'Dashboard KPIs' },
    { method: 'GET', path: '/api/v1/dashboard/risk-matrix', desc: 'Matriz risco × qualidade' },
  ]},
  { cat: 'Market Data', endpoints: [
    { method: 'GET', path: '/api/v1/market/carbon-price', desc: 'Cotação EU ETS em tempo real' },
    { method: 'GET', path: '/api/v1/market/summary', desc: 'Resumo de mercados' },
    { method: 'GET', path: '/api/v1/market/portfolio-impact', desc: 'Simulador de impacto' },
  ]},
  { cat: 'Satellite & Remote Sensing', endpoints: [
    { method: 'GET', path: '/api/v1/satellite/fire-alerts', desc: 'Alertas de incêndio (NASA FIRMS)' },
    { method: 'GET', path: '/api/v1/satellite/ndvi/{id}', desc: 'Série temporal NDVI' },
    { method: 'GET', path: '/api/v1/satellite/ghg/{id}', desc: 'Dados GHG (Sentinel-5P)' },
    { method: 'GET', path: '/api/v1/satellite/xco2/{id}', desc: 'Validação XCO2 (OCO-2/3)' },
    { method: 'GET', path: '/api/v1/satellite/deforestation-alerts', desc: 'Alertas de desmatamento' },
    { method: 'GET', path: '/api/v1/satellite/biomass-estimate/{id}', desc: 'Estimativa de biomassa' },
  ]},
  { cat: 'Web3 / Blockchain', endpoints: [
    { method: 'GET', path: '/api/v1/web3/pool-stats', desc: 'Estatísticas Toucan BCT/NCT' },
    { method: 'GET', path: '/api/v1/web3/verify-token', desc: 'Verificar token address' },
    { method: 'GET', path: '/api/v1/web3/project-tokenization/{id}', desc: 'Status de tokenização' },
  ]},
  { cat: 'ESG & Contabilidade', endpoints: [
    { method: 'POST', path: '/api/v1/esg/import-footprint', desc: 'Importar pegada de carbono' },
    { method: 'GET', path: '/api/v1/esg/balance', desc: 'Balanço emissões × offsets' },
    { method: 'GET', path: '/api/v1/esg/offset-recommendations', desc: 'Recomendações de compensação' },
    { method: 'GET', path: '/api/v1/esg/net-zero-projection', desc: 'Projeção de Net Zero' },
  ]},
  { cat: 'Analytics', endpoints: [
    { method: 'GET', path: '/api/v1/analytics/correlations', desc: 'Correlações e heatmaps' },
    { method: 'GET', path: '/api/v1/analytics/performance-kpis', desc: 'KPIs de performance' },
    { method: 'GET', path: '/api/v1/analytics/trends', desc: 'Tendências temporais' },
  ]},
  { cat: 'Relatórios', endpoints: [
    { method: 'GET', path: '/api/v1/reports', desc: 'Listar relatórios gerados' },
    { method: 'POST', path: '/api/v1/reports', desc: 'Gerar novo relatório (PDF/CSV/JSON)' },
    { method: 'GET', path: '/api/v1/reports/templates', desc: 'Templates disponíveis' },
  ]},
];

export default function ApiDocs() {
  const [active, setActive] = useState(0);
  const methodColor = (m: string) => m === 'GET' ? '#34d399' : m === 'POST' ? '#38bdf8' : m === 'PATCH' ? '#fbbf24' : '#f87171';

  return (
    <div className="fade-in">
      <div className="page-header"><h1 className="page-title">API & Integrações</h1><p className="page-subtitle">Documentação completa da API REST</p></div>
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        <div className="card"><div className="card-title">Total Endpoints</div><div className="card-value">{API_SECTIONS.reduce((a, s) => a + s.endpoints.length, 0)}</div></div>
        <div className="card"><div className="card-title">Categorias</div><div className="card-value">{API_SECTIONS.length}</div></div>
        <div className="card"><div className="card-title">Base URL</div><div style={{ fontWeight: 600, fontSize: '0.9rem', fontFamily: 'monospace' }}>/api/v1</div></div>
        <div className="card"><div className="card-title">Autenticação</div><div style={{ fontSize: '0.85rem' }}>Bearer JWT Token</div></div>
      </div>

      <div style={{ display: 'flex', gap: '1.5rem' }}>
        <div style={{ width: '220px', flexShrink: 0 }}>
          {API_SECTIONS.map((s, i) => (
            <div key={i} className={`sidebar-link ${active === i ? 'active' : ''}`} onClick={() => setActive(i)} style={{ cursor: 'pointer' }}>{s.cat}</div>
          ))}
        </div>
        <div style={{ flex: 1 }}>
          <div className="card">
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem' }}>{API_SECTIONS[active].cat}</h3>
            {API_SECTIONS[active].endpoints.map((ep, j) => (
              <div key={j} style={{ padding: '0.75rem', background: 'var(--cv-surface)', borderRadius: '8px', marginBottom: '0.5rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <span style={{ background: `${methodColor(ep.method)}20`, color: methodColor(ep.method), padding: '2px 8px', borderRadius: '4px', fontWeight: 700, fontSize: '0.75rem', fontFamily: 'monospace', minWidth: '45px', textAlign: 'center' }}>{ep.method}</span>
                <code style={{ fontSize: '0.85rem', color: 'var(--cv-primary)', fontFamily: 'monospace' }}>{ep.path}</code>
                <span style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)', marginLeft: 'auto' }}>{ep.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
