import { useState, useEffect } from 'react';
import { Shield, CheckCircle, AlertCircle, XCircle, FileText, Download, ChevronRight } from 'lucide-react';

interface ComplianceItem {
  disclosure_item: string;
  disclosure_title: string;
  description: string;
  status: string;
  coverage_pct: number;
  evidence_summary: string;
}

interface ComplianceSummary {
  csrd_esrs: { items: ComplianceItem[]; avg_coverage: number; verified: number; gaps: number };
  sbti: { items: any[]; compliant: number; total: number };
  icvcm: { items: any[]; met: number; total: number };
  overall_score: number;
}

const frameworkTabs = [
  { key: 'csrd', label: 'CSRD / ESRS E1', icon: <Shield size={16} /> },
  { key: 'sbti', label: 'SBTi', icon: <FileText size={16} /> },
  { key: 'icvcm', label: 'ICVCM CCP', icon: <CheckCircle size={16} /> },
];

const statusColors: Record<string, string> = {
  verified: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  mapped: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  gap: 'bg-red-500/15 text-red-400 border-red-500/30',
  compliant: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  non_compliant: 'bg-red-500/15 text-red-400 border-red-500/30',
  met: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  partially_met: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  not_met: 'bg-red-500/15 text-red-400 border-red-500/30',
};

const statusLabels: Record<string, string> = {
  verified: 'Verificado', mapped: 'Mapeado', gap: 'Lacuna',
  compliant: 'Conforme', non_compliant: 'Não Conforme',
  met: 'Atendido', partially_met: 'Parcial', not_met: 'Não Atendido',
};

export default function CompliancePage() {
  const [activeTab, setActiveTab] = useState('csrd');
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [compliance, setCompliance] = useState<ComplianceSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const API = import.meta.env.VITE_API_URL || '';

  useEffect(() => {
    fetch(`${API}/api/v1/projects?page_size=100`)
      .then(r => r.json())
      .then(d => { setProjects(d.items || []); if (d.items?.length) setSelectedProject(d.items[0].id); });
  }, []);

  useEffect(() => {
    if (!selectedProject) return;
    setLoading(true);
    fetch(`${API}/api/v1/compliance/mapping/${selectedProject}`)
      .then(r => r.json())
      .then(d => { setCompliance(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [selectedProject]);

  const getStatusIcon = (status: string) => {
    if (status === 'verified' || status === 'compliant' || status === 'met') return <CheckCircle size={16} className="text-emerald-400" />;
    if (status === 'gap' || status === 'non_compliant' || status === 'not_met') return <XCircle size={16} className="text-red-400" />;
    return <AlertCircle size={16} className="text-amber-400" />;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Shield className="text-indigo-400" /> Compliance & Regulatório
          </h1>
          <p className="text-gray-400 mt-1">Mapeamento CSRD/ESRS, SBTi e ICVCM com trilha de evidências</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium transition-colors">
          <Download size={16} /> Exportar Pacote
        </button>
      </div>

      {/* Project Selector + Overall Score */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-2">
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            value={selectedProject || ''} onChange={e => setSelectedProject(Number(e.target.value))}
          >
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name} — {p.rating?.grade || 'N/A'}</option>
            ))}
          </select>
        </div>
        {compliance && (
          <>
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4 backdrop-blur-sm">
              <p className="text-xs text-gray-500 uppercase tracking-wider">Score Geral</p>
              <p className="text-3xl font-bold text-white mt-1">{compliance.overall_score.toFixed(1)}<span className="text-lg text-gray-500">/100</span></p>
            </div>
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4 backdrop-blur-sm">
              <p className="text-xs text-gray-500 uppercase tracking-wider">CSRD Cobertura</p>
              <p className="text-3xl font-bold text-white mt-1">{compliance.csrd_esrs.avg_coverage.toFixed(0)}<span className="text-lg text-gray-500">%</span></p>
            </div>
          </>
        )}
      </div>

      {/* Framework Tabs */}
      <div className="flex gap-2 border-b border-gray-700/50 pb-0">
        {frameworkTabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-5 py-3 text-sm font-medium rounded-t-lg transition-all ${
              activeTab === tab.key
                ? 'bg-gray-800 text-white border border-gray-700/50 border-b-transparent -mb-px'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >{tab.icon} {tab.label}</button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-20">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-500"></div>
        </div>
      ) : compliance && (
        <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-6 backdrop-blur-sm">
          {activeTab === 'csrd' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white">ESRS E1 — Climate Change Disclosures</h2>
                <div className="flex gap-3 text-xs">
                  <span className="text-emerald-400">✓ {compliance.csrd_esrs.verified} verificados</span>
                  <span className="text-red-400">✗ {compliance.csrd_esrs.gaps} lacunas</span>
                </div>
              </div>
              {compliance.csrd_esrs.items.map((item, i) => (
                <div key={i} className="border border-gray-700/50 rounded-lg p-5 hover:border-indigo-500/30 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        {getStatusIcon(item.status)}
                        <span className="text-sm font-mono text-indigo-400">{item.disclosure_item}</span>
                        <h3 className="text-white font-medium">{item.disclosure_title}</h3>
                      </div>
                      <p className="text-sm text-gray-400 ml-7">{item.description}</p>
                      {item.evidence_summary && (
                        <p className="text-xs text-gray-500 ml-7 mt-2 italic">
                          <ChevronRight size={12} className="inline" /> {item.evidence_summary}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-3 ml-4">
                      <div className="text-right">
                        <p className="text-lg font-bold text-white">{item.coverage_pct.toFixed(0)}%</p>
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${statusColors[item.status]}`}>
                          {statusLabels[item.status]}
                        </span>
                      </div>
                    </div>
                  </div>
                  {/* Coverage bar */}
                  <div className="mt-3 ml-7">
                    <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-500 ${
                        item.coverage_pct >= 80 ? 'bg-emerald-500' : item.coverage_pct >= 40 ? 'bg-amber-500' : 'bg-red-500'
                      }`} style={{ width: `${item.coverage_pct}%` }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          {activeTab === 'sbti' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-white mb-4">SBTi Carbon Credit Requirements</h2>
              {compliance.sbti.items.map((item: any, i: number) => (
                <div key={i} className="border border-gray-700/50 rounded-lg p-5 hover:border-indigo-500/30 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(item.status)}
                      <div>
                        <h3 className="text-white font-medium">{item.title}</h3>
                        <p className="text-sm text-gray-400 mt-1">{item.description}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs px-3 py-1 rounded-full border ${statusColors[item.status]}`}>
                        {statusLabels[item.status]}
                      </span>
                      <p className="text-xs text-gray-500 mt-2">
                        Min: {item.min_rating_required} / Atual: {item.current_rating}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          {activeTab === 'icvcm' && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-white mb-4">ICVCM Core Carbon Principles</h2>
              {compliance.icvcm.items.map((item: any, i: number) => (
                <div key={i} className="border border-gray-700/50 rounded-lg p-5 hover:border-indigo-500/30 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(item.status)}
                      <div>
                        <h3 className="text-white font-medium">{item.title}</h3>
                        <p className="text-sm text-gray-400 mt-1">{item.description}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs px-3 py-1 rounded-full border ${statusColors[item.status]}`}>
                        {statusLabels[item.status]}
                      </span>
                      <p className="text-xs text-gray-500 mt-2">Pilar: {item.pillar_name} ({item.pillar_score}/100)</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
