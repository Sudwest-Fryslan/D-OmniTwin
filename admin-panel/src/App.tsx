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
import { AIUsecasesPage } from './pages/AIUsecasesPage';
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
  Building2,
  Moon,
  Sun,
  ShieldCheck
} from 'lucide-react';
import { authAPI } from './services/api';
import Beeldmerk from './components/Beeldmerk';
import { huidigeModus, kiesModus } from './thema';
import './styles/admin.css';

const queryClient = new QueryClient();

// Layout component for authenticated pages
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, logout: storeLogout, authConfig } = useAdminStore();
  // Ingelogd via Keycloak: wachtwoord en gebruikers beheer je daar (#251)
  const viaKeycloak = user?.bron === 'oidc';
  // Lichte of donkere weergave (#284): standaard volgens het thema, eigen keuze onthouden
  const [, setModus] = React.useState(huidigeModus);
  const wisselModus = () => {
    const nieuw = huidigeModus() === 'licht' ? 'donker' : 'licht';
    kiesModus(nieuw);
    setModus(nieuw);
  };
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
            to="/admin/dashboard"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <LayoutDashboard size={18} />
            Dashboard
          </NavLink>

          <NavLink
            to="/admin/indicatoren"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Database size={18} />
            Indicatoren
          </NavLink>

          <NavLink
            to="/admin/data-kwaliteit"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Activity size={18} />
            Data Kwaliteit
          </NavLink>

          <NavLink
            to="/admin/hierarchie"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <GitBranch size={18} />
            Hiërarchie
          </NavLink>

          <NavLink
            to="/admin/kleurschemas"
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
            to="/admin/llm"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Settings size={18} />
            AI Configuratie
          </NavLink>

          <NavLink
            to="/admin/ai-usecases"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <ShieldCheck size={18} />
            AI-usecases
          </NavLink>

          <NavLink
            to="/admin/logs"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <ScrollText size={18} />
            Log Viewer
          </NavLink>

          <NavLink
            to="/admin/externe-lagen"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Globe size={18} />
            Externe Lagen
          </NavLink>

          <NavLink
            to="/admin/organisatie"
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
              <Route path="/admin/dashboard" element={<>Dashboard</>} />
              <Route path="/admin/indicatoren" element={<>Indicatoren</>} />
              <Route path="/admin/data-kwaliteit" element={<>Data Kwaliteit</>} />
              <Route path="/admin/hierarchie" element={<>Hiërarchie</>} />
              <Route path="/admin/kleurschemas" element={<>Kleurschema's</>} />
              <Route path="/admin/llm" element={<>AI Configuratie</>} />
              <Route path="/admin/ai-usecases" element={<>AI-usecases</>} />
              <Route path="/admin/logs" element={<>Log Viewer</>} />
              <Route path="/admin/externe-lagen" element={<>Externe Kaartlagen</>} />
              <Route path="/admin/organisatie" element={<>Organisatie en thema</>} />
              <Route path="/admin/account" element={<>Mijn Account</>} />
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
                <button type="button" onClick={wisselModus} style={{ ...menuStijl, background: 'none', border: 'none',
                  borderBottom: '1px solid var(--color-border)', width: '100%', textAlign: 'left', cursor: 'pointer' }}>
                  {huidigeModus() === 'licht' ? <Moon size={16} /> : <Sun size={16} />}
                  {huidigeModus() === 'licht' ? 'Donkere weergave' : 'Lichte weergave'}
                </button>
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
    return <Navigate to="/admin/login" replace />;
  }

  return <AppLayout>{children}</AppLayout>;
};

// Standalone rapportage layout (#290): altijd zonder beheer-zijbalk of beheerheader,
// voor zowel anonieme bezoekers als ingelogde beheerders.
const ReportLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="report-standalone-container">
      <header className="report-standalone-header hide-on-print">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <a
            href="/"
            className="btn btn-secondary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', textDecoration: 'none' }}
            aria-label="Terug naar kaart"
          >
            ← Terug naar kaart
          </a>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Beeldmerk size={28} />
            <span style={{ fontWeight: 600, fontSize: '1.1rem', color: 'var(--color-text-primary)' }}>D-OmniTwin</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <a
            href="/#melden"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ textDecoration: 'none' }}
            title="Meld een data-afwijking of geef feedback (#311)"
          >
            Afwijking melden
          </a>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => window.print()}
            title="Afdrukken of opslaan als PDF"
          >
            Afdrukken
          </button>
        </div>
      </header>
      <div className="report-standalone-body">
        {children}
      </div>
    </div>
  );
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
      <BrowserRouter>
        <Routes>
          {/* Beheerscherm routes */}
          <Route
            path="/admin/login"
            element={
              isAuthenticated ? <Navigate to="/admin/dashboard" replace /> : <LoginPage />
            }
          />

          <Route path="/admin/dashboard" element={
            <ProtectedRoute><DashboardPage /></ProtectedRoute>
          } />

          <Route path="/admin/indicatoren" element={
            <ProtectedRoute><IndicatorsPage /></ProtectedRoute>
          } />

          <Route path="/admin/data-kwaliteit" element={
            <ProtectedRoute><DataKwaliteitPage /></ProtectedRoute>
          } />

          <Route path="/admin/hierarchie" element={
            <ProtectedRoute><HierarchiePage /></ProtectedRoute>
          } />

          <Route path="/admin/kleurschemas" element={
            <ProtectedRoute><KleurschemasPage /></ProtectedRoute>
          } />

          <Route path="/admin/llm/*" element={
            <ProtectedRoute><LLMConfigPage /></ProtectedRoute>
          } />

          <Route path="/admin/ai-usecases" element={
            <ProtectedRoute><AIUsecasesPage /></ProtectedRoute>
          } />

          <Route path="/admin/account" element={
            <ProtectedRoute><AccountPage /></ProtectedRoute>
          } />

          <Route path="/admin/logs" element={
            <ProtectedRoute><LogViewerPage /></ProtectedRoute>
          } />

          <Route path="/admin/externe-lagen" element={
            <ProtectedRoute><ExterneKaartlagenPage /></ProtectedRoute>
          } />

          <Route path="/admin/organisatie" element={
            <ProtectedRoute><OrganisatiePage /></ProtectedRoute>
          } />

          {/* Standalone Rapportage Routes (#290) - Altijd zonder beheer-sidebar */}
          <Route path="/rapport/benchmark" element={
            <ReportLayout><BenchmarkPage /></ReportLayout>
          } />

          <Route path="/rapport/multi-gebied" element={
            <ReportLayout><MultiGebiedPage /></ReportLayout>
          } />

          <Route path="/rapport/thema-analyse" element={
            <ReportLayout><ThemaAnalysePage /></ReportLayout>
          } />

          <Route path="/rapport/deelgebied" element={
            <ReportLayout><DeelgebiedPage /></ReportLayout>
          } />

          <Route path="/rapport/:gebied_id?" element={
            <ReportLayout><ReportPage /></ReportLayout>
          } />

          {/* Backwards compatibility & redirects */}
          <Route path="/admin/rapport/*" element={<Navigate to="/rapport" replace />} />
          <Route path="/publiek-rapport/:gebied_id?" element={<Navigate to="/rapport" replace />} />
          <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="/admin/" element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="/login" element={<Navigate to="/admin/login" replace />} />
          <Route path="/dashboard" element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
