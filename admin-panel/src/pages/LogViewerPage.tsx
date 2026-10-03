import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import {
  Activity, AlertTriangle, AlertCircle, Users, Clock,
  Search, RefreshCw, ChevronLeft, ChevronRight, Settings,
  Trash2
} from 'lucide-react';

// ============================================================================
// Types
// ============================================================================
interface LogEntry {
  id: number;
  timestamp: string;
  level: string;
  category: string;
  message: string;
  user_id: string | null;
  ip_address: string | null;
  endpoint: string | null;
  response_time_ms: number | null;
  extra: any;
}

interface LogStats {
  total_today: number;
  errors_today: number;
  warnings_today: number;
  active_users: number;
  unique_ips: number;
  avg_response_ms: number;
  p95_response_ms: number;
  by_category: { category: string; count: number }[];
  by_hour: { hour: number; count: number }[];
  top_endpoints: { endpoint: string; hits: number; avg_ms: number; p95_ms: number }[];
  error_trend: { dag: string; errors: number }[];
}

interface LogConfig {
  category: string;
  level: string;
  enabled: boolean;
  updated_at: string | null;
  updated_by: string | null;
}

// ============================================================================
// API calls
// ============================================================================
const logAPI = {
  getLogs: (params: Record<string, any>) => api.get('/logs', { params }),
  getStats: () => api.get('/logs/stats'),
  getConfig: () => api.get('/log-config'),
  updateConfig: (category: string, data: { level: string; enabled: boolean }) =>
    api.put(`/log-config/${category}`, data),
  runCleanup: () => api.post('/logs/cleanup'),
};

// ============================================================================
// Constants
// ============================================================================
const LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
const CATEGORIES = ['SERVER', 'API', 'AUTH', 'KOMPAS', 'KAART', 'RAPPORT', 'LLM_CHAT', 'DATABASE', 'ADMIN'];
const PERIODS = [
  { value: 'today', label: 'Vandaag' },
  { value: 'week', label: 'Week' },
  { value: 'month', label: 'Maand' },
  { value: 'all', label: 'Alles' },
];

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: '#94a3b8',
  INFO: '#3b82f6',
  WARNING: '#f97316',
  ERROR: '#ef4444',
  CRITICAL: '#dc2626',
};

// ============================================================================
// Component
// ============================================================================
export const LogViewerPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'logs' | 'gebruik'>('logs');
  const [showConfig, setShowConfig] = useState(false);
  const [cleanupMsg, setCleanupMsg] = useState('');

  // Filters
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState('');
  const [level, setLevel] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [period, setPeriod] = useState('today');

  // Queries
  const { data: statsData } = useQuery({
    queryKey: ['logStats'],
    queryFn: () => logAPI.getStats(),
    refetchInterval: 30000,
  });

  const { data: logsData, isLoading } = useQuery({
    queryKey: ['logs', page, category, level, search, period],
    queryFn: () => logAPI.getLogs({ page, category: category || undefined, level: level || undefined, search: search || undefined, period }),
    refetchInterval: 10000,
  });

  const { data: configData } = useQuery({
    queryKey: ['logConfig'],
    queryFn: () => logAPI.getConfig(),
  });

  const configMutation = useMutation({
    mutationFn: ({ cat, data }: { cat: string; data: { level: string; enabled: boolean } }) =>
      logAPI.updateConfig(cat, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['logConfig'] });
    },
  });

  const cleanupMutation = useMutation({
    mutationFn: () => logAPI.runCleanup(),
    onSuccess: (res) => {
      setCleanupMsg(res.data.message);
      setTimeout(() => setCleanupMsg(''), 5000);
    },
  });

  const stats: LogStats = statsData?.data || {
    total_today: 0, errors_today: 0, warnings_today: 0,
    active_users: 0, unique_ips: 0, avg_response_ms: 0, p95_response_ms: 0,
    by_category: [], by_hour: [], top_endpoints: [], error_trend: [],
  };

  const logs: LogEntry[] = logsData?.data?.logs || [];
  const totalPages = logsData?.data?.total_pages || 1;
  const totalLogs = logsData?.data?.total || 0;
  const configs: LogConfig[] = configData?.data || [];

  const handleSearch = useCallback(() => {
    setSearch(searchInput);
    setPage(1);
  }, [searchInput]);

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatDate = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleDateString('nl-NL', { day: '2-digit', month: '2-digit' });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
      {/* Stats Cards */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        <StatCard icon={<Activity size={20} />} value={stats.total_today} label="Logs vandaag" color="var(--color-primary)" />
        <StatCard icon={<AlertCircle size={20} />} value={stats.errors_today} label="Errors" color="var(--color-error)" />
        <StatCard icon={<AlertTriangle size={20} />} value={stats.warnings_today} label="Warnings" color="var(--color-warning)" />
        <StatCard icon={<Users size={20} />} value={stats.active_users} label="Actieve users" color="var(--color-secondary)" />
        <StatCard icon={<Clock size={20} />} value={`${stats.avg_response_ms}ms`} label="Gem. response" color="var(--color-accent)" />
        <StatCard icon={<Clock size={20} />} value={`${stats.p95_response_ms}ms`} label="P95 response" color="var(--color-text-secondary)" />
      </div>

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--color-border)', paddingBottom: '0' }}>
        {(['logs', 'gebruik'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '0.5rem 1.25rem', border: 'none', cursor: 'pointer',
              background: 'none', fontSize: '0.875rem', fontWeight: 600,
              color: activeTab === tab ? 'var(--color-primary)' : 'var(--color-text-muted)',
              borderBottom: activeTab === tab ? '2px solid var(--color-primary)' : '2px solid transparent',
              marginBottom: '-1px',
            }}
          >
            {tab === 'logs' ? '📋 Log Stream' : '📊 Gebruik & Gezondheid'}
          </button>
        ))}
      </div>

      {/* === TAB: LOG STREAM === */}
      {activeTab === 'logs' && <>
      <div className="card" style={{ padding: 'var(--spacing-md)' }}>
        <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Period */}
          <div style={{ display: 'flex', gap: '2px', background: 'var(--color-surface-light)', borderRadius: 'var(--radius-md)', padding: '2px' }}>
            {PERIODS.map(p => (
              <button
                key={p.value}
                onClick={() => { setPeriod(p.value); setPage(1); }}
                style={{
                  padding: '0.35rem 0.75rem', fontSize: '0.8rem', border: 'none', cursor: 'pointer',
                  borderRadius: 'var(--radius-sm)', fontWeight: 500,
                  background: period === p.value ? 'var(--color-primary)' : 'transparent',
                  color: period === p.value ? 'white' : 'var(--color-text-secondary)',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Category */}
          <select
            className="form-select"
            aria-label="Categorie"
            value={category}
            onChange={e => { setCategory(e.target.value); setPage(1); }}
            style={{ width: '150px' }}
          >
            <option value="">Alle categorieën</option>
            {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>

          {/* Level */}
          <select
            className="form-select"
            aria-label="Niveau"
            value={level}
            onChange={e => { setLevel(e.target.value); setPage(1); }}
            style={{ width: '130px' }}
          >
            <option value="">Alle niveaus</option>
            {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
          </select>

          {/* Search */}
          <div style={{ display: 'flex', gap: '4px', flex: 1, minWidth: '200px' }}>
            <input
              className="form-input"
              placeholder="Zoek in berichten..."
              aria-label="Zoek in berichten"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <button className="btn btn-secondary" onClick={handleSearch} aria-label="Zoeken" title="Zoeken">
              <Search size={16} />
            </button>
          </div>

          {/* Config toggle */}
          <button
            className={`btn ${showConfig ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setShowConfig(!showConfig)}
            aria-expanded={showConfig}
          >
            <Settings size={16} /> Config
          </button>

          {/* Refresh */}
          <button
            className="btn btn-secondary"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['logs'] })}
            aria-label="Verversen"
            title="Verversen"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Config Panel (collapsible) */}
      {showConfig && (
        <div className="card">
          <h3 style={{ marginBottom: 'var(--spacing-md)', fontSize: '1rem' }}>Log Configuratie</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Categorie</th>
                <th>Niveau</th>
                <th>Actief</th>
                <th>Laatst gewijzigd</th>
              </tr>
            </thead>
            <tbody>
              {configs.map(cfg => (
                <tr key={cfg.category}>
                  <td>
                    <span style={{
                      padding: '0.15rem 0.5rem', borderRadius: 'var(--radius-sm)',
                      background: 'var(--color-surface-light)', fontSize: '0.8rem', fontWeight: 600,
                    }}>
                      {cfg.category}
                    </span>
                  </td>
                  <td>
                    <select
                      className="form-select"
                      aria-label={`Logniveau ${cfg.category}`}
                      value={cfg.level}
                      onChange={e => configMutation.mutate({
                        cat: cfg.category,
                        data: { level: e.target.value, enabled: cfg.enabled },
                      })}
                      style={{ width: '120px', padding: '0.25rem' }}
                    >
                      {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                    </select>
                  </td>
                  <td>
                    <button
                      onClick={() => configMutation.mutate({
                        cat: cfg.category,
                        data: { level: cfg.level, enabled: !cfg.enabled },
                      })}
                      style={{
                        padding: '0.25rem 0.75rem', borderRadius: 'var(--radius-sm)',
                        border: 'none', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600,
                        background: cfg.enabled ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)',
                        color: cfg.enabled ? 'var(--color-success)' : 'var(--color-error)',
                      }}
                    >
                      {cfg.enabled ? 'AAN' : 'UIT'}
                    </button>
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                    {cfg.updated_by && `${cfg.updated_by}`}
                    {cfg.updated_at && ` — ${new Date(cfg.updated_at).toLocaleString('nl-NL')}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Log Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{
          padding: 'var(--spacing-sm) var(--spacing-md)',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          fontSize: '0.8rem', color: 'var(--color-text-muted)',
        }}>
          <span>{totalLogs.toLocaleString()} resultaten</span>
          <span>Pagina {page} / {totalPages}</span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="table" style={{ fontSize: '0.8rem' }}>
            <thead>
              <tr>
                <th style={{ width: '130px' }}>Tijdstip</th>
                <th style={{ width: '80px' }}>Niveau</th>
                <th style={{ width: '100px' }}>Categorie</th>
                <th>Bericht</th>
                <th style={{ width: '100px' }}>IP / User</th>
                <th style={{ width: '70px' }}>ms</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 'var(--spacing-lg)' }}>Laden...</td></tr>
              ) : logs.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 'var(--spacing-lg)', color: 'var(--color-text-muted)' }}>Geen logs gevonden</td></tr>
              ) : logs.map(log => (
                <tr key={log.id}>
                  <td style={{ whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    <span style={{ color: 'var(--color-text-muted)' }}>{formatDate(log.timestamp)}</span>{' '}
                    {formatTime(log.timestamp)}
                  </td>
                  <td>
                    <span style={{
                      padding: '0.1rem 0.4rem', borderRadius: '3px',
                      fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.03em',
                      background: `${LEVEL_COLORS[log.level] || '#666'}22`,
                      color: LEVEL_COLORS[log.level] || '#999',
                    }}>
                      {log.level}
                    </span>
                  </td>
                  <td>
                    <span style={{
                      padding: '0.1rem 0.4rem', borderRadius: '3px',
                      background: 'var(--color-surface-light)', fontSize: '0.7rem',
                      fontWeight: 600,
                    }}>
                      {log.category}
                    </span>
                  </td>
                  <td style={{
                    maxWidth: '500px', overflow: 'hidden', textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {log.message}
                  </td>
                  <td style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                    {log.user_id || log.ip_address || '—'}
                  </td>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                    {log.response_time_ms != null ? `${log.response_time_ms}` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div style={{
          padding: 'var(--spacing-sm) var(--spacing-md)',
          borderTop: '1px solid var(--color-border)',
          display: 'flex', justifyContent: 'center', gap: 'var(--spacing-sm)',
        }}>
          <button
            className="btn btn-secondary"
            disabled={page <= 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
            aria-label="Vorige pagina"
          >
            <ChevronLeft size={16} />
          </button>
          {[...Array(Math.min(5, totalPages))].map((_, i) => {
            const pageNum = Math.max(1, Math.min(page - 2 + i, totalPages));
            return (
              <button
                key={pageNum}
                className={`btn ${pageNum === page ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setPage(pageNum)}
                style={{ minWidth: '36px' }}
              >
                {pageNum}
              </button>
            );
          })}
          <button
            className="btn btn-secondary"
            disabled={page >= totalPages}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            aria-label="Volgende pagina"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
      </> }

      {/* === TAB: GEBRUIK & GEZONDHEID === */}
      {activeTab === 'gebruik' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>

          {/* Uurverdeling */}
          <div className="card">
            <div className="card-header"><span className="card-title">Requests per uur (vandaag)</span></div>
            <HourBarChart data={stats.by_hour} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-lg)' }}>
            {/* Categorie verdeling */}
            <div className="card">
              <div className="card-header"><span className="card-title">Verdeling per categorie</span></div>
              <CategoryBar data={stats.by_category} />
            </div>

            {/* Error trend */}
            <div className="card">
              <div className="card-header"><span className="card-title">Errors afgelopen 7 dagen</span></div>
              <ErrorTrend data={stats.error_trend} />
            </div>
          </div>

          {/* Top endpoints */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Top endpoints (vandaag)</span>
            </div>
            <table className="table" style={{ fontSize: '0.8rem' }}>
              <thead>
                <tr>
                  <th>Endpoint</th>
                  <th style={{ width: '80px' }}>Hits</th>
                  <th style={{ width: '90px' }}>Gem. (ms)</th>
                  <th style={{ width: '90px' }}>P95 (ms)</th>
                </tr>
              </thead>
              <tbody>
                {stats.top_endpoints.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>Nog geen data</td></tr>
                ) : stats.top_endpoints.map(ep => (
                  <tr key={ep.endpoint}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{ep.endpoint}</td>
                    <td>{ep.hits}</td>
                    <td style={{ color: ep.avg_ms > 500 ? 'var(--color-warning)' : 'var(--color-text-secondary)' }}>{ep.avg_ms}</td>
                    <td style={{ color: ep.p95_ms > 1000 ? 'var(--color-error)' : 'var(--color-text-secondary)' }}>{ep.p95_ms}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Log Cleanup */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Log Retentie & Cleanup</span>
            </div>
            <div style={{ display: 'flex', gap: 'var(--spacing-lg)', alignItems: 'flex-start' }}>
              <div style={{ flex: 1, fontSize: '0.85rem', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                <p>Automatische cleanup draait dagelijks:</p>
                <ul style={{ paddingLeft: '1.25rem', marginTop: '0.5rem' }}>
                  <li><strong>Alle niveaus</strong> → verwijderd na <code>LOG_BEWAAR_DAGEN</code> (standaard 30 dagen; DEBUG na 7)</li>
                  <li><strong>IP-adressen</strong> → ingekort na <code>LOG_IP_BEWAAR_DAGEN</code> (standaard 7 dagen)</li>
                </ul>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)', alignItems: 'flex-end' }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => cleanupMutation.mutate()}
                  disabled={cleanupMutation.isPending}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  <Trash2 size={15} />
                  {cleanupMutation.isPending ? 'Bezig...' : 'Nu uitvoeren'}
                </button>
                {cleanupMsg && (
                  <span style={{ fontSize: '0.8rem', color: 'var(--color-success)' }}>✓ {cleanupMsg}</span>
                )}
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
};

// ============================================================================
// Stat Card Component
// ============================================================================
const StatCard: React.FC<{ icon: React.ReactNode; value: string | number; label: string; color: string }> = ({ icon, value, label, color }) => (
  <div className="stat-card" style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
    <div style={{ color, opacity: 0.8 }}>{icon}</div>
    <div>
      <div className="stat-value" style={{ color, fontSize: '1.5rem' }}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  </div>
);

// ============================================================================
// Chart: Requests per uur (SVG bar chart)
// ============================================================================
const HourBarChart: React.FC<{ data: { hour: number; count: number }[] }> = ({ data }) => {
  if (!data.length) return <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>Nog geen data voor vandaag.</p>;
  const max = Math.max(...data.map(d => d.count), 1);
  const hours = Array.from({ length: 24 }, (_, h) => ({
    hour: h,
    count: data.find(d => d.hour === h)?.count || 0,
  }));
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '2px', height: '80px', paddingTop: '8px' }}>
      {hours.map(({ hour, count }) => (
        <div key={hour} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
          <div
            title={`${hour}:00 — ${count} requests`}
            style={{
              width: '100%',
              height: `${Math.round((count / max) * 60)}px`,
              minHeight: count > 0 ? '3px' : '0',
              background: count > 0 ? 'var(--color-primary)' : 'var(--color-surface-light)',
              borderRadius: '2px 2px 0 0',
              opacity: count > 0 ? 0.85 : 0.3,
              transition: 'opacity 0.2s',
              cursor: count > 0 ? 'help' : 'default',
            }}
          />
          {hour % 4 === 0 && (
            <span style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)' }}>{hour}u</span>
          )}
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// Chart: Verdeling per categorie (horizontale bars)
// ============================================================================
const CategoryBar: React.FC<{ data: { category: string; count: number }[] }> = ({ data }) => {
  if (!data.length) return <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>Nog geen data.</p>;
  const max = Math.max(...data.map(d => d.count), 1);
  const CAT_COLORS: Record<string, string> = {
    API: '#3b82f6', SERVER: '#22c55e', AUTH: '#f97316',
    KAART: '#8b5cf6', KOMPAS: '#06b6d4', RAPPORT: '#eab308',
    LLM_CHAT: '#ec4899', DATABASE: '#ef4444', ADMIN: '#94a3b8',
  };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {data.map(({ category, count }) => (
        <div key={category} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '80px', fontSize: '0.72rem', fontWeight: 600, color: 'var(--color-text-secondary)', textAlign: 'right', flexShrink: 0 }}>
            {category}
          </span>
          <div style={{ flex: 1, background: 'var(--color-surface-light)', borderRadius: '3px', height: '14px', overflow: 'hidden' }}>
            <div style={{
              width: `${Math.round((count / max) * 100)}%`,
              height: '100%',
              background: CAT_COLORS[category] || '#64748b',
              borderRadius: '3px',
              opacity: 0.8,
            }} />
          </div>
          <span style={{ width: '36px', fontSize: '0.72rem', color: 'var(--color-text-muted)', textAlign: 'right', flexShrink: 0 }}>{count}</span>
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// Chart: Error trend 7 dagen
// ============================================================================
const ErrorTrend: React.FC<{ data: { dag: string; errors: number }[] }> = ({ data }) => {
  if (!data.length) return <p style={{ color: 'var(--color-success)', fontSize: '0.85rem' }}>✓ Geen errors in de afgelopen 7 dagen.</p>;
  const max = Math.max(...data.map(d => d.errors), 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '6px', height: '80px', paddingTop: '8px' }}>
      {data.map(({ dag, errors }) => (
        <div key={dag} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
          <div
            title={`${dag}: ${errors} errors`}
            style={{
              width: '100%',
              height: `${Math.round((errors / max) * 60)}px`,
              minHeight: '4px',
              background: 'var(--color-error)',
              borderRadius: '2px 2px 0 0',
              opacity: 0.75,
              cursor: 'help',
            }}
          />
          <span style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)' }}>
            {new Date(dag).toLocaleDateString('nl-NL', { day: '2-digit', month: '2-digit' })}
          </span>
        </div>
      ))}
    </div>
  );
};
