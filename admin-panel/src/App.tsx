import React from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAdminStore } from './hooks/useAdminStore';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { IndicatorsPage } from './pages/IndicatorsPage';
import { HierarchiePage } from './pages/HierarchiePage';
import { KleurschemasPage } from './pages/KleurschemasPage';
import { ReportPage } from './pages/ReportPage';
import { BenchmarkPage } from './pages/BenchmarkPage';
import { MultiGebiedPage } from './pages/MultiGebiedPage';
import { ThemaAnalysePage } from './pages/ThemaAnalysePage';
import { DeelgebiedPage } from './pages/DeelgebiedPage';
import { LLMConfigPage } from './pages/LLMConfigPage';
import { AccountPage } from './pages/AccountPage';
import { LogViewerPage } from './pages/LogViewerPage';
import { ExterneKaartlagenPage } from './pages/ExterneKaartlagenPage';
import { DataKwaliteitPage } from './pages/DataKwaliteitPage';
import { OrganisatiePage } from './pages/OrganisatiePage';
import {
  LayoutDashboard,
  Database,
  Palette,
  GitBranch,
  LogOut,
  FileText,
  Scale,
  Layers,
  Settings,
  User,
  ChevronDown,
  ScrollText,
  Globe,
  Activity,
  Users,
  ExternalLink,
  Building2
} from 'lucide-react';
import { authAPI } from './services/api';
import Beeldmerk from './components/Beeldmerk';
import './styles/admin.css';

const queryClient = new QueryClient();

// Layout component for authenticated pages
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout: storeLogout, authConfig } = useAdminStore();
  // Ingelogd via Keycloak: wachtwoord en gebruikers beheer je daar (#251)
  const viaKeycloak = user?.bron === 'oidc';
  const [dropdownOpen, setDropdownOpen] = React.useState(false);
  // Gebiedsdossier = /rapport of /rapport/<gebied_id>, niet de andere rapporten onder /rapport/
  const { pathname } = useLocation();
  const isGebiedsdossier = /^\/rapport(\/(?!benchmark|multi-gebied|thema-analyse|deelgebied)[^/]+)?\/?$/.test(pathname);

  const handleLogout = async () => {
    try {
      const res = await authAPI.logout();
      // Keycloak-sessie: ook bij Keycloak uitloggen (RP-initiated logout), die stuurt terug naar /admin/login
      if (res.data.uitlog_url) {
        window.location.assign(res.data.uitlog_url);
        return;
      }
    } catch (e) {
      console.error(e);
    }
    storeLogout();
  };

  const menuStijl: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: '0.5rem',
    padding: '0.75rem 1rem', color: 'var(--color-text-primary)',
    textDecoration: 'none', borderBottom: '1px solid var(--color-border)',
    fontSize: '0.875rem'
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <Beeldmerk size={36} />
          <div>
            <h1>D-OmniTwin</h1>
            <p>Beheerscherm</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <NavLink
            to="/dashboard"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <LayoutDashboard size={18} />
            Dashboard
          </NavLink>

          <NavLink
            to="/indicatoren"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Database size={18} />
            Indicatoren
          </NavLink>

          <NavLink
            to="/data-kwaliteit"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Activity size={18} />
            Data Kwaliteit
          </NavLink>

          <NavLink
            to="/hierarchie"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <GitBranch size={18} />
            Hiërarchie
          </NavLink>

          <NavLink
            to="/kleurschemas"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Palette size={18} />
            Kleurschema's
          </NavLink>

          <NavLink
            to="/rapport"
            className={() => `nav-item ${isGebiedsdossier ? 'active' : ''}`}
          >
            <FileText size={18} />
            Gebiedsdossier
          </NavLink>

          <NavLink
            to="/rapport/benchmark"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Scale size={18} />
            Benchmark
          </NavLink>

          <NavLink
            to="/rapport/multi-gebied"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Layers size={18} />
            Multi-Gebiedsdossier
          </NavLink>

          <NavLink
            to="/rapport/thema-analyse"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Layers size={18} />
            Thema-Analyse
          </NavLink>

          <NavLink
            to="/llm"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Settings size={18} />
            AI Configuratie
          </NavLink>

          <NavLink
            to="/logs"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <ScrollText size={18} />
            Log Viewer
          </NavLink>

          <NavLink
            to="/externe-lagen"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Globe size={18} />
            Externe Lagen
          </NavLink>

          <NavLink
            to="/organisatie"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Building2 size={18} />
            Organisatie
          </NavLink>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {authConfig.noodtoegang && user?.bron === 'lokaal' && (
          <div className="noodtoegang-balk hide-on-print" role="status">
            Noodtoegang: je bent ingelogd met een lokaal account terwijl Keycloak aan staat
            (<code>LOKAAL_INLOGGEN=true</code>). Zet dit uit zodra Keycloak weer werkt.
          </div>
        )}
        <header className="header hide-on-print" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'relative', zIndex: 50 }}>
          <h2>
            <Routes>
              <Route path="/dashboard" element={<>Dashboard</>} />
              <Route path="/indicatoren" element={<>Indicatoren</>} />
              <Route path="/data-kwaliteit" element={<>Data Kwaliteit</>} />
              <Route path="/hierarchie" element={<>Hiërarchie</>} />
              <Route path="/kleurschemas" element={<>Kleurschema's</>} />
              <Route path="/rapport/thema-analyse" element={<>Thema-Analyse</>} />
              <Route path="/rapport/*" element={<>AI Rapportage</>} />
              <Route path="/llm" element={<>AI Configuratie</>} />
              <Route path="/logs" element={<>Log Viewer</>} />
              <Route path="/externe-lagen" element={<>Externe Kaartlagen</>} />
              <Route path="/organisatie" element={<>Organisatie en thema</>} />
              <Route path="/account" element={<>Mijn Account</>} />
            </Routes>
          </h2>

          <div
            style={{ position: 'relative', zIndex: 51 }}
            onKeyDown={(e) => { if (e.key === 'Escape' && dropdownOpen) setDropdownOpen(false); }}
          >
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              aria-expanded={dropdownOpen}
              aria-haspopup="true"
              aria-controls="gebruikersmenu"
              className="user-dropdown-btn"
              style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                background: 'var(--color-surface-light)', border: '1px solid var(--color-border)',
                color: 'var(--color-text-primary)', padding: '0.5rem 1rem',
                borderRadius: 'var(--radius-md)', cursor: 'pointer',
                fontSize: '0.875rem', fontWeight: 500,
                boxShadow: 'none', WebkitTapHighlightColor: 'transparent',
                position: 'relative'
              }}
            >
              <div style={{ background: 'var(--merk-bg)', borderRadius: '50%', width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <User size={14} color="var(--merk-tekst)" />
              </div>
              {user?.username || 'Beheerder'}
              <ChevronDown size={16} color="var(--color-text-muted)" />
            </button>

            {dropdownOpen && (
              <div id="gebruikersmenu" style={{
                position: 'absolute', top: '100%', right: 0, marginTop: '0.5rem',
                background: 'var(--color-surface)', border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)', width: '280px',
                boxShadow: 'var(--shadow-md)', zIndex: 100, overflow: 'hidden'
              }}>
                {viaKeycloak && authConfig.account_url ? (
                  <a href={authConfig.account_url} target="_blank" rel="noopener noreferrer" style={menuStijl}>
                    <User size={16} /> Mijn account (Keycloak) <ExternalLink size={14} aria-label="opent in nieuw venster" />
                  </a>
                ) : !viaKeycloak && (
                  <NavLink to="/account" onClick={() => setDropdownOpen(false)} style={menuStijl}>
                    <User size={16} /> Profiel & Wachtwoord
                  </NavLink>
                )}
                {authConfig.gebruikersbeheer_url && (
                  <a href={authConfig.gebruikersbeheer_url} target="_blank" rel="noopener noreferrer" style={menuStijl}>
                    <Users size={16} /> Gebruikers en rollen beheren <ExternalLink size={14} aria-label="opent in nieuw venster" />
                  </a>
                )}
                <button
                  onClick={() => { setDropdownOpen(false); handleLogout(); }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.5rem',
                    padding: '0.75rem 1rem', background: 'none', border: 'none',
                    width: '100%', textAlign: 'left', cursor: 'pointer',
                    color: 'var(--color-error)', fontSize: '0.875rem'
                  }}
                >
                  <LogOut size={16} /> Uitloggen
                </button>
              </div>
            )}
          </div>
        </header>

        <div className="content">
          {children}
        </div>
      </main>
    </div>
  );
};

// Protected route wrapper
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAdminStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
};

// Publiek bereikbare rapportroutes: met menu als beheerder is ingelogd, anders standalone
const OptionalLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAdminStore();

  if (!isAuthenticated) {
    return <>{children}</>;
  }

  return <AppLayout>{children}</AppLayout>;
};

// KleurschemasPage is now imported from ./pages/KleurschemasPage

function App() {
  const { isAuthenticated, setAuthenticated, setAuthConfig, authConfig } = useAdminStore();
  const [isInitializing, setIsInitializing] = React.useState(true);

  React.useEffect(() => {
    const checkAuthStatus = async () => {
      // Welke manieren van inloggen aan staan (Keycloak, lokaal); zonder antwoord: lokaal
      try {
        setAuthConfig((await authAPI.getConfig()).data);
      } catch {
        // standaardconfiguratie blijft staan
      }
      try {
        const res = await authAPI.getMe();
        // Alleen beheerders; de backend dwingt dit ook af (#65)
        if (res.data.authenticated && res.data.user?.is_admin) {
          setAuthenticated(true, res.data.user);
        } else {
          setAuthenticated(false);
        }
      } catch (e) {
        setAuthenticated(false);
      } finally {
        setIsInitializing(false);
      }
    };
    checkAuthStatus();
  }, [setAuthenticated, setAuthConfig]);

  if (isInitializing) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: 'var(--color-text)' }}>Bezig met laden...</div>;
  }

  return (
    <QueryClientProvider client={queryClient}>
      {authConfig.demo && (
        <div className="demo-balk hide-on-print" role="status">
          Demo-omgeving — standaardwachtwoorden, niet voor productie
        </div>
      )}
      <BrowserRouter basename="/admin">
        <Routes>
          <Route
            path="/login"
            element={
              isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />
            }
          />

          <Route path="/dashboard" element={
            <ProtectedRoute><DashboardPage /></ProtectedRoute>
          } />

          <Route path="/indicatoren" element={
            <ProtectedRoute><IndicatorsPage /></ProtectedRoute>
          } />

          <Route path="/data-kwaliteit" element={
            <ProtectedRoute><DataKwaliteitPage /></ProtectedRoute>
          } />

          <Route path="/hierarchie" element={
            <ProtectedRoute><HierarchiePage /></ProtectedRoute>
          } />

          <Route path="/kleurschemas" element={
            <ProtectedRoute><KleurschemasPage /></ProtectedRoute>
          } />

          <Route path="/rapport/benchmark" element={
            <OptionalLayout><BenchmarkPage /></OptionalLayout>
          } />

          <Route path="/rapport/multi-gebied" element={
            <OptionalLayout><MultiGebiedPage /></OptionalLayout>
          } />

          <Route path="/rapport/thema-analyse" element={
            <OptionalLayout><ThemaAnalysePage /></OptionalLayout>
          } />

          <Route path="/rapport/deelgebied" element={
            <OptionalLayout><DeelgebiedPage /></OptionalLayout>
          } />

          <Route path="/rapport/:gebied_id?" element={
            <OptionalLayout><ReportPage /></OptionalLayout>
          } />

          {/* Publieke Report Route outside of ProtectedRoute (als alias) */}
          <Route path="/publiek-rapport/:gebied_id?" element={
            <ReportPage />
          } />

          <Route path="/llm" element={
            <ProtectedRoute><LLMConfigPage /></ProtectedRoute>
          } />

          <Route path="/account" element={
            <ProtectedRoute><AccountPage /></ProtectedRoute>
          } />

          <Route path="/logs" element={
            <ProtectedRoute><LogViewerPage /></ProtectedRoute>
          } />

          <Route path="/externe-lagen" element={
            <ProtectedRoute><ExterneKaartlagenPage /></ProtectedRoute>
          } />

          <Route path="/organisatie" element={
            <ProtectedRoute><OrganisatiePage /></ProtectedRoute>
          } />

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
