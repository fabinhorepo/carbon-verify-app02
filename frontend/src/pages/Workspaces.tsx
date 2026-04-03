import { useState, useEffect } from 'react';
import { Users, Layout, Shield, ShoppingCart, BookOpen, Eye, ChevronRight, Settings as SettingsIcon } from 'lucide-react';

const profileIcons: Record<string, any> = {
  sustainability: <Layout className="text-emerald-400" />,
  risk_compliance: <Shield className="text-red-400" />,
  legal: <BookOpen className="text-purple-400" />,
  procurement: <ShoppingCart className="text-amber-400" />,
  external_audit: <Eye className="text-cyan-400" />,
};

const profileColors: Record<string, string> = {
  sustainability: 'border-emerald-500/30 hover:border-emerald-500/60',
  risk_compliance: 'border-red-500/30 hover:border-red-500/60',
  legal: 'border-purple-500/30 hover:border-purple-500/60',
  procurement: 'border-amber-500/30 hover:border-amber-500/60',
  external_audit: 'border-cyan-500/30 hover:border-cyan-500/60',
};

export default function Workspaces() {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [profiles, setProfiles] = useState<Record<string, any>>({});
  const [selectedWs, setSelectedWs] = useState<number | null>(null);
  const [wsConfig, setWsConfig] = useState<any>(null);
  const API = import.meta.env.VITE_API_URL || '';

  useEffect(() => {
    fetch(`${API}/api/v1/workspaces`).then(r => r.json()).then(setWorkspaces);
    fetch(`${API}/api/v1/workspaces/profiles`).then(r => r.json()).then(setProfiles);
  }, []);

  useEffect(() => {
    if (!selectedWs) return;
    fetch(`${API}/api/v1/workspaces/${selectedWs}/config`).then(r => r.json()).then(setWsConfig);
  }, [selectedWs]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Users className="text-purple-400" /> Workspaces Multi-stakeholder
          </h1>
          <p className="text-gray-400 mt-1">Configure visões personalizadas por perfil organizacional</p>
        </div>
      </div>

      {/* Profile Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {Object.entries(profiles).map(([key, profile]: [string, any]) => (
          <div key={key}
            className={`bg-gray-800/50 border rounded-xl p-5 backdrop-blur-sm cursor-pointer transition-all ${profileColors[key] || 'border-gray-700/50 hover:border-gray-500'}`}
          >
            <div className="flex items-center gap-3 mb-3">
              {profileIcons[key] || <SettingsIcon className="text-gray-400" />}
              <h3 className="text-white font-medium text-sm">{profile.label}</h3>
            </div>
            <p className="text-xs text-gray-400 leading-relaxed">{profile.description}</p>
          </div>
        ))}
      </div>

      {/* Active Workspaces */}
      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6 backdrop-blur-sm">
        <h2 className="text-lg font-semibold text-white mb-4">Workspaces Ativos</h2>
        <div className="space-y-3">
          {workspaces.map(ws => (
            <div key={ws.id}
              className={`border rounded-lg p-4 cursor-pointer transition-all flex items-center justify-between ${
                selectedWs === ws.id ? 'border-indigo-500/50 bg-indigo-500/5' : 'border-gray-700/50 hover:border-gray-600'
              }`}
              onClick={() => setSelectedWs(ws.id)}
            >
              <div className="flex items-center gap-4">
                {profileIcons[ws.profile_type] || <Layout className="text-gray-400" />}
                <div>
                  <h3 className="text-white font-medium">{ws.name}</h3>
                  <p className="text-xs text-gray-500 capitalize">{ws.profile_type.replace('_', ' ')}</p>
                </div>
                {ws.is_default && <span className="text-xs px-2 py-0.5 bg-indigo-500/15 text-indigo-400 rounded-full border border-indigo-500/30">Padrão</span>}
              </div>
              <ChevronRight size={18} className="text-gray-500" />
            </div>
          ))}
          {!workspaces.length && <p className="text-gray-500 text-center py-8">Nenhum workspace configurado.</p>}
        </div>
      </div>

      {/* Workspace Config Detail */}
      {wsConfig && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6 backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-white mb-4">
            Configuração: {wsConfig.workspace.name}
            <span className="text-sm text-gray-500 ml-2 capitalize">({wsConfig.workspace.profile_type.replace('_', ' ')})</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm text-gray-400 uppercase tracking-wider mb-3">Módulos Visíveis</h3>
              <div className="flex flex-wrap gap-2">
                {wsConfig.config?.visible_modules?.map((mod: string) => (
                  <span key={mod} className="text-xs px-3 py-1.5 rounded-lg bg-gray-700/50 text-gray-200 border border-gray-600/50">
                    {mod.replace('_', ' ')}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-sm text-gray-400 uppercase tracking-wider mb-3">Ações Permitidas</h3>
              <div className="flex flex-wrap gap-2">
                {wsConfig.config?.allowed_actions?.map((action: string) => (
                  <span key={action} className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {action.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {wsConfig.config?.dashboard_kpis && (
            <div className="mt-6">
              <h3 className="text-sm text-gray-400 uppercase tracking-wider mb-3">KPIs do Dashboard</h3>
              <div className="flex flex-wrap gap-2">
                {wsConfig.config.dashboard_kpis.map((kpi: string) => (
                  <span key={kpi} className="text-xs px-3 py-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
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
