import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import {
  Activity, AlertTriangle, AlertCircle, Users, Clock,
  Search, RefreshCw, ChevronLeft, ChevronRight, Settings
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
  by_category: { category: string; count: number }[];
  by_hour: { hour: number; count: number }[];
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
  const [showConfig, setShowConfig] = useState(false);

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

  const stats: LogStats = statsData?.data || {
    total_today: 0, errors_today: 0, warnings_today: 0,
    active_users: 0, unique_ips: 0, avg_response_ms: 0,
    by_category: [], by_hour: [],
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
      </div>

      {/* Filters */}
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
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <button className="btn btn-secondary" onClick={handleSearch}>
              <Search size={16} />
            </button>
          </div>

          {/* Config toggle */}
          <button
            className={`btn ${showConfig ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setShowConfig(!showConfig)}
          >
            <Settings size={16} /> Config
          </button>

          {/* Refresh */}
          <button
            className="btn btn-secondary"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['logs'] })}
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
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
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
