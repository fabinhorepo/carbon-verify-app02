import { useState, useEffect } from 'react';
import { Users, Layout, Shield, ShoppingCart, BookOpen, Eye, ChevronRight, Settings as SettingsIcon } from 'lucide-react';
import api from '../utils/api';

const profileIcons: Record<string, any> = {
  sustainability: <Layout size={20} style={{ color: '#34d399' }} />,
  risk_compliance: <Shield size={20} style={{ color: '#f87171' }} />,
  legal: <BookOpen size={20} style={{ color: '#a78bfa' }} />,
  procurement: <ShoppingCart size={20} style={{ color: '#fbbf24' }} />,
  external_audit: <Eye size={20} style={{ color: '#38bdf8' }} />,
};

const profileColorMap: Record<string, string> = {
  sustainability: '#34d399',
  risk_compliance: '#f87171',
  legal: '#a78bfa',
  procurement: '#fbbf24',
  external_audit: '#38bdf8',
};

const PROFILE_DESCRIPTIONS: Record<string, string> = {
  sustainability: 'Visão completa com acesso a todos os módulos de projetos, rating, compliance e portfólio.',
  risk_compliance: 'Foco em detecção de fraudes, alertas de risco e compliance regulatória CSRD.',
  legal: 'Acesso a compliance, fluxos de aprovação e documentação jurídica.',
  procurement: 'Ferramentas de mercado, fronteira preço-qualidade e simulação de portfólio.',
  external_audit: 'Acesso read-only a relatórios de compliance e evidências para auditoria.',
};

export default function Workspaces() {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [profiles, setProfiles] = useState<Record<string, any>>({});
  const [selectedWs, setSelectedWs] = useState<number | null>(null);
  const [wsConfig, setWsConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get('/workspaces').then(r => setWorkspaces(r.data || [])).catch(() => setWorkspaces([])),
      api.get('/workspaces/profiles').then(r => setProfiles(r.data || {})).catch(() => setProfiles(PROFILE_DESCRIPTIONS)),
    ]).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedWs) return;
    api.get(`/workspaces/${selectedWs}/config`).then(r => setWsConfig(r.data)).catch(() => setWsConfig(null));
  }, [selectedWs]);

  // Use fallback profiles if API returns empty
  const displayProfiles = Object.keys(profiles).length > 0 ? profiles : 
    Object.fromEntries(Object.entries(PROFILE_DESCRIPTIONS).map(([k, v]) => [k, { label: k.replace(/_/g, ' '), description: v }]));

  if (loading) return <div className="loading-page"><div className="spinner" /></div>;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Users size={28} style={{ color: '#a78bfa' }} /> Workspaces Multi-stakeholder
        </h1>
        <p className="page-subtitle">Configure visões personalizadas por perfil organizacional</p>
      </div>

      {/* Profile Overview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        {Object.entries(displayProfiles).map(([key, profile]: [string, any]) => {
          const color = profileColorMap[key] || '#64748b';
          return (
            <div key={key} className="card" style={{ borderTop: `3px solid ${color}`, cursor: 'default' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                {profileIcons[key] || <SettingsIcon size={20} style={{ color: '#64748b' }} />}
                <div style={{ fontWeight: 600, fontSize: '0.85rem', textTransform: 'capitalize' }}>{profile.label || key.replace(/_/g, ' ')}</div>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', lineHeight: 1.5 }}>
                {profile.description || PROFILE_DESCRIPTIONS[key] || 'Perfil personalizado'}
              </div>
            </div>
          );
        })}
      </div>

      {/* Active Workspaces */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-title" style={{ marginBottom: '1rem' }}>Workspaces Ativos</div>
        {workspaces.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {workspaces.map(ws => {
              const color = profileColorMap[ws.profile_type] || '#64748b';
              return (
                <div key={ws.id}
                  className="card"
                  style={{
                    cursor: 'pointer', transition: 'all 0.2s',
                    borderLeft: selectedWs === ws.id ? `3px solid ${color}` : '3px solid transparent',
                    background: selectedWs === ws.id ? 'rgba(99, 102, 241, 0.05)' : undefined,
                  }}
                  onClick={() => setSelectedWs(ws.id)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      {profileIcons[ws.profile_type] || <Layout size={20} style={{ color: '#64748b' }} />}
                      <div>
                        <div style={{ fontWeight: 600 }}>{ws.name}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--cv-text-muted)', textTransform: 'capitalize' }}>
                          {ws.profile_type?.replace(/_/g, ' ')}
                        </div>
                      </div>
                      {ws.is_default && (
                        <span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>Padrão</span>
                      )}
                    </div>
                    <ChevronRight size={18} style={{ color: 'var(--cv-text-muted)' }} />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--cv-text-muted)' }}>
            <Users size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
            <div>Nenhum workspace configurado.</div>
          </div>
        )}
      </div>

      {/* Workspace Config Detail */}
      {wsConfig && (
        <div className="card">
          <div className="card-title" style={{ marginBottom: '1rem' }}>
            Configuração: {wsConfig.workspace?.name || 'N/A'}
            <span style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)', marginLeft: '0.5rem', textTransform: 'capitalize' }}>
              ({(wsConfig.workspace?.profile_type || '').replace(/_/g, ' ')})
            </span>
          </div>

          <div className="grid-2">
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Módulos Visíveis</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                {(wsConfig.config?.visible_modules || []).map((mod: string) => (
                  <span key={mod} className="badge" style={{ background: 'rgba(100, 116, 139, 0.15)', textTransform: 'capitalize' }}>
                    {mod.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Ações Permitidas</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                {(wsConfig.config?.allowed_actions || []).map((action: string) => (
                  <span key={action} className="badge badge-green" style={{ fontSize: '0.7rem' }}>
                    {action.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {wsConfig.config?.dashboard_kpis && (
            <div style={{ marginTop: '1.5rem' }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>KPIs do Dashboard</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                {wsConfig.config.dashboard_kpis.map((kpi: string) => (
                  <span key={kpi} className="badge badge-blue" style={{ fontSize: '0.7rem' }}>
                    {kpi.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
