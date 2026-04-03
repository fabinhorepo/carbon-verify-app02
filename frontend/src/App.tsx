import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { useState, createContext, useContext, useMemo } from 'react';
import {
  LayoutDashboard, FolderKanban, ShieldAlert, Briefcase, TrendingUp,
  Map, GitCompareArrows, FileText, Settings, BarChart3, Globe, Leaf,
  Link2, Layers3, BadgeDollarSign, LogOut, Shield, Target, Scale, Users,
  ChevronDown
} from 'lucide-react';
import './index.css';

import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import FraudAlerts from './pages/FraudAlerts';
import Portfolio from './pages/Portfolio';
import MarketCenter from './pages/MarketCenter';
import ProjectMap from './pages/ProjectMap';
import ProjectComparison from './pages/ProjectComparison';
import Reports from './pages/Reports';
import SettingsPage from './pages/Settings';
import Analytics from './pages/Analytics';
import ApiDocs from './pages/ApiDocs';
import ESGIntegration from './pages/ESGIntegration';
import Web3Dashboard from './pages/Web3Dashboard';
import CarbonAccounting from './pages/CarbonAccounting';
import Marketplace from './pages/Marketplace';
import CompliancePage from './pages/Compliance';
import MarketFrontier from './pages/MarketFrontier';
import Workspaces from './pages/Workspaces';
import RiskAdjusted from './pages/RiskAdjusted';

// ─── Types ──────────────────────────────────────────────────────────────

interface User { id: number; email: string; full_name: string; role: string; organization_id: number; }
interface AuthCtx {
  user: User | null; token: string | null;
  login: (t: string, u: User) => void; logout: () => void;
}

interface WorkspaceProfile {
  id: string;
  label: string;
  description: string;
  visible_modules: string[];
}

interface WorkspaceCtx {
  activeProfile: WorkspaceProfile;
  setActiveProfile: (p: WorkspaceProfile) => void;
  allProfiles: WorkspaceProfile[];
}

// ─── Workspace Profiles ─────────────────────────────────────────────────

const DEFAULT_PROFILES: WorkspaceProfile[] = [
  {
    id: 'sustainability',
    label: 'Sustentabilidade / Clima',
    description: 'Visão completa de projetos, ratings, portfólio e compliance.',
    visible_modules: [
      'dashboard', 'projects', 'fraud_ops', 'portfolio', 'risk_adjusted',
      'market', 'frontier', 'compliance', 'analytics',
      'map', 'compare', 'workspaces',
      'web3', 'esg', 'accounting', 'marketplace',
      'reports', 'api_docs', 'settings',
    ],
  },
  {
    id: 'risk_compliance',
    label: 'Risco / Compliance',
    description: 'Foco em fraud detection, alertas de risco e compliance regulatória.',
    visible_modules: [
      'dashboard', 'projects', 'fraud_ops', 'compliance',
      'risk_adjusted', 'analytics', 'reports', 'settings',
    ],
  },
  {
    id: 'legal',
    label: 'Jurídico',
    description: 'Acesso a compliance, enforcement e fluxos de aprovação.',
    visible_modules: [
      'compliance', 'fraud_ops', 'workspaces', 'reports', 'settings',
    ],
  },
  {
    id: 'procurement',
    label: 'Compras / Procurement',
    description: 'Ferramentas de mercado, frontier preço-qualidade e simulação.',
    visible_modules: [
      'dashboard', 'market', 'frontier', 'portfolio', 'compare',
      'marketplace', 'reports', 'settings',
    ],
  },
  {
    id: 'external_audit',
    label: 'Auditoria Externa',
    description: 'Acesso read-only a compliance, evidências e relatórios.',
    visible_modules: [
      'compliance', 'reports',
    ],
  },
];

// ─── Contexts ───────────────────────────────────────────────────────────

const AuthContext = createContext<AuthCtx>({ user: null, token: null, login: () => {}, logout: () => {} });
export const useAuth = () => useContext(AuthContext);

const WorkspaceContext = createContext<WorkspaceCtx>({
  activeProfile: DEFAULT_PROFILES[0],
  setActiveProfile: () => {},
  allProfiles: DEFAULT_PROFILES,
});
export const useWorkspace = () => useContext(WorkspaceContext);

// ─── Module → Route mapping ────────────────────────────────────────────



const ALL_NAV_ITEMS = [
  { section: 'Principal', items: [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard', module: 'dashboard' },
    { path: '/projects', icon: FolderKanban, label: 'Projetos', module: 'projects' },
    { path: '/fraud-ops', icon: ShieldAlert, label: 'Fraud Ops', module: 'fraud_ops' },
    { path: '/portfolio', icon: Briefcase, label: 'Portfólio', module: 'portfolio' },
    { path: '/risk-adjusted', icon: Scale, label: 'Risk-Adjusted', module: 'risk_adjusted' },
  ]},
  { section: 'Mercado & Compliance', items: [
    { path: '/market', icon: TrendingUp, label: 'Centro de Mercado', module: 'market' },
    { path: '/frontier', icon: Target, label: 'Price-Quality Frontier', module: 'frontier' },
    { path: '/compliance', icon: Shield, label: 'Compliance & CSRD', module: 'compliance' },
    { path: '/analytics', icon: BarChart3, label: 'Analytics', module: 'analytics' },
  ]},
  { section: 'Ferramentas', items: [
    { path: '/map', icon: Map, label: 'Mapa de Projetos', module: 'map' },
    { path: '/compare', icon: GitCompareArrows, label: 'Comparador', module: 'compare' },
    { path: '/workspaces', icon: Users, label: 'Workspaces', module: 'workspaces' },
  ]},
  { section: 'Integrações', items: [
    { path: '/web3', icon: Layers3, label: 'Web3 / Blockchain', module: 'web3' },
    { path: '/esg', icon: Leaf, label: 'ESG & Plan A', module: 'esg' },
    { path: '/accounting', icon: BadgeDollarSign, label: 'Contabilidade', module: 'accounting' },
    { path: '/marketplace', icon: Globe, label: 'Marketplace', module: 'marketplace' },
  ]},
  { section: 'Sistema', items: [
    { path: '/reports', icon: FileText, label: 'Relatórios', module: 'reports' },
    { path: '/api-docs', icon: Link2, label: 'API & Integrações', module: 'api_docs' },
    { path: '/settings', icon: Settings, label: 'Configurações', module: 'settings' },
  ]},
];

// ─── Workspace Selector Component ──────────────────────────────────────

function WorkspaceSelector() {
  const { activeProfile, setActiveProfile, allProfiles } = useWorkspace();
  const [open, setOpen] = useState(false);

  return (
    <div className="workspace-selector" style={{ padding: '0.5rem 1.25rem', marginBottom: '0.5rem' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '100%', background: 'rgba(6, 182, 212, 0.08)', border: '1px solid rgba(6, 182, 212, 0.2)',
          borderRadius: '8px', padding: '0.5rem 0.75rem', cursor: 'pointer', color: 'var(--cv-text)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem',
          transition: 'all 0.2s ease',
        }}
      >
        <div style={{ textAlign: 'left' }}>
          <div style={{ fontSize: '0.65rem', color: 'var(--cv-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Workspace</div>
          <div style={{ fontWeight: 600, color: 'var(--cv-accent)' }}>{activeProfile.label}</div>
        </div>
        <ChevronDown size={14} style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', left: '1rem', right: '1rem', marginTop: '4px',
          background: 'var(--cv-bg-card)', border: '1px solid var(--cv-border)',
          borderRadius: '8px', boxShadow: '0 8px 24px rgba(0,0,0,0.3)', zIndex: 100,
          overflow: 'hidden',
        }}>
          {allProfiles.map(p => (
            <button
              key={p.id}
              onClick={() => { setActiveProfile(p); setOpen(false); }}
              style={{
                width: '100%', padding: '0.6rem 0.75rem', border: 'none',
                background: p.id === activeProfile.id ? 'rgba(6, 182, 212, 0.12)' : 'transparent',
                cursor: 'pointer', textAlign: 'left', color: 'var(--cv-text)',
                borderBottom: '1px solid var(--cv-border)', display: 'block',
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => { if (p.id !== activeProfile.id) (e.target as HTMLElement).style.background = 'rgba(255,255,255,0.03)'; }}
              onMouseLeave={e => { if (p.id !== activeProfile.id) (e.target as HTMLElement).style.background = 'transparent'; }}
            >
              <div style={{ fontWeight: p.id === activeProfile.id ? 600 : 400, fontSize: '0.8rem' }}>{p.label}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', marginTop: '2px' }}>{p.description}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Sidebar ────────────────────────────────────────────────────────────

function Sidebar() {
  const { user, logout } = useAuth();
  const { activeProfile } = useWorkspace();
  const visibleModules = new Set(activeProfile.visible_modules);

  const filteredNav = useMemo(() => {
    return ALL_NAV_ITEMS
      .map(section => ({
        ...section,
        items: section.items.filter(item => visibleModules.has(item.module)),
      }))
      .filter(section => section.items.length > 0);
  }, [activeProfile.id]);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="icon">CV</div>
        <div>
          <h1>Carbon Verify</h1>
          <span>v4.0 · Platform</span>
        </div>
      </div>
      <WorkspaceSelector />
      {filteredNav.map((section) => (
        <div key={section.section}>
          <div className="sidebar-section">{section.section}</div>
          {section.items.map((item) => (
            <NavLink key={item.path} to={item.path} end={item.path === '/'} className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
              <item.icon /> {item.label}
            </NavLink>
          ))}
        </div>
      ))}
      <div style={{ marginTop: 'auto', padding: '1rem 1.25rem', borderTop: '1px solid var(--cv-border)' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--cv-accent)', marginBottom: '2px', fontWeight: 600 }}>
          {activeProfile.label}
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--cv-text-muted)', marginBottom: '0.5rem' }}>
          {user?.full_name} · {user?.role}
        </div>
        <button onClick={logout} className="sidebar-link" style={{ width: '100%', border: 'none', background: 'none', cursor: 'pointer' }}>
          <LogOut /> Sair
        </button>
      </div>
    </aside>
  );
}

// ─── Protected Layout ───────────────────────────────────────────────────

function ProtectedLayout() {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content fade-in">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/fraud-ops" element={<FraudAlerts />} />
          <Route path="/fraud-alerts" element={<FraudAlerts />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/risk-adjusted" element={<RiskAdjusted />} />
          <Route path="/market" element={<MarketCenter />} />
          <Route path="/frontier" element={<MarketFrontier />} />
          <Route path="/compliance" element={<CompliancePage />} />
          <Route path="/map" element={<ProjectMap />} />
          <Route path="/compare" element={<ProjectComparison />} />
          <Route path="/workspaces" element={<Workspaces />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/web3" element={<Web3Dashboard />} />
          <Route path="/esg" element={<ESGIntegration />} />
          <Route path="/accounting" element={<CarbonAccounting />} />
          <Route path="/marketplace" element={<Marketplace />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/api-docs" element={<ApiDocs />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}

// ─── App ────────────────────────────────────────────────────────────────

export default function App() {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem('cv_user');
    return stored ? JSON.parse(stored) : null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('cv_token'));

  const [activeProfile, setActiveProfileState] = useState<WorkspaceProfile>(() => {
    const stored = localStorage.getItem('cv_workspace_profile');
    if (stored) {
      const parsed = JSON.parse(stored);
      const found = DEFAULT_PROFILES.find(p => p.id === parsed.id);
      return found || DEFAULT_PROFILES[0];
    }
    return DEFAULT_PROFILES[0];
  });

  const setActiveProfile = (p: WorkspaceProfile) => {
    setActiveProfileState(p);
    localStorage.setItem('cv_workspace_profile', JSON.stringify({ id: p.id }));
  };

  const login = (t: string, u: User) => {
    setToken(t); setUser(u);
    localStorage.setItem('cv_token', t);
    localStorage.setItem('cv_user', JSON.stringify(u));
  };
  const logout = () => {
    setToken(null); setUser(null);
    localStorage.removeItem('cv_token');
    localStorage.removeItem('cv_user');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      <WorkspaceContext.Provider value={{ activeProfile, setActiveProfile, allProfiles: DEFAULT_PROFILES }}>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/*" element={<ProtectedLayout />} />
          </Routes>
        </BrowserRouter>
      </WorkspaceContext.Provider>
    </AuthContext.Provider>
  );
}
