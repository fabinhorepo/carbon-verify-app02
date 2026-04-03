import { BrowserRouter, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { useState, createContext, useContext } from 'react';
import {
  LayoutDashboard, FolderKanban, ShieldAlert, Briefcase, TrendingUp,
  Map, GitCompareArrows, FileText, Settings, BarChart3, Globe, Leaf,
  Link2, Layers3, BadgeDollarSign, LogOut
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

interface User { id: number; email: string; full_name: string; role: string; organization_id: number; }
interface AuthCtx { user: User | null; token: string | null; login: (t: string, u: User) => void; logout: () => void; }
const AuthContext = createContext<AuthCtx>({ user: null, token: null, login: () => {}, logout: () => {} });
export const useAuth = () => useContext(AuthContext);

const NAV_ITEMS = [
  { section: 'Principal', items: [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/projects', icon: FolderKanban, label: 'Projetos' },
    { path: '/fraud-alerts', icon: ShieldAlert, label: 'Fraude' },
    { path: '/portfolio', icon: Briefcase, label: 'Portfólio' },
  ]},
  { section: 'Mercado & Dados', items: [
    { path: '/market', icon: TrendingUp, label: 'Centro de Mercado' },
    { path: '/map', icon: Map, label: 'Mapa de Projetos' },
    { path: '/compare', icon: GitCompareArrows, label: 'Comparador' },
    { path: '/analytics', icon: BarChart3, label: 'Analytics' },
  ]},
  { section: 'Integrações', items: [
    { path: '/web3', icon: Layers3, label: 'Web3 / Blockchain' },
    { path: '/esg', icon: Leaf, label: 'ESG & Plan A' },
    { path: '/accounting', icon: BadgeDollarSign, label: 'Contabilidade' },
    { path: '/marketplace', icon: Globe, label: 'Marketplace' },
  ]},
  { section: 'Sistema', items: [
    { path: '/reports', icon: FileText, label: 'Relatórios' },
    { path: '/api-docs', icon: Link2, label: 'API & Integrações' },
    { path: '/settings', icon: Settings, label: 'Configurações' },
  ]},
];

function Sidebar() {
  const { user, logout } = useAuth();
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="icon">CV</div>
        <div>
          <h1>Carbon Verify</h1>
          <span>v2.0 · Production</span>
        </div>
      </div>
      {NAV_ITEMS.map((section) => (
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
        <div style={{ fontSize: '0.8rem', color: 'var(--cv-text-muted)', marginBottom: '0.5rem' }}>
          {user?.full_name}
        </div>
        <button onClick={logout} className="sidebar-link" style={{ width: '100%', border: 'none', background: 'none', cursor: 'pointer' }}>
          <LogOut /> Sair
        </button>
      </div>
    </aside>
  );
}

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
          <Route path="/fraud-alerts" element={<FraudAlerts />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/market" element={<MarketCenter />} />
          <Route path="/map" element={<ProjectMap />} />
          <Route path="/compare" element={<ProjectComparison />} />
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

export default function App() {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem('cv_user');
    return stored ? JSON.parse(stored) : null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('cv_token'));

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
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<ProtectedLayout />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
