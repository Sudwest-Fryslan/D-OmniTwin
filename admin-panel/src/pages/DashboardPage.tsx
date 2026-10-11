import React, { useEffect, useState } from 'react';
import { dashboardAPI, indicatorenAPI } from '../services/api';
import { StatsCard } from '../components/dashboard/StatsCard';
import { QuadrantChart } from '../components/dashboard/QuadrantChart';
import { IndicatorsTable } from '../components/dashboard/IndicatorsTable';
import { Database, Layers, FileText, TrendingUp, Search, Filter, RefreshCw, Download, AlertCircle, Clock } from 'lucide-react';
import type { DashboardStats, QuadrantCoverage, IndicatorDashboardItem, OntologieValidatieStatusResponse } from '../types';

export const DashboardPage: React.FC = () => {
    // State
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [statsError, setStatsError] = useState(false);
    const [quadrants, setQuadrants] = useState<QuadrantCoverage[]>([]);
    const [indicators, setIndicators] = useState<IndicatorDashboardItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [tableLoading, setTableLoading] = useState(false);
    const [ontologieStatus, setOntologieStatus] = useState<OntologieValidatieStatusResponse | null>(null);
    const tableRef = React.useRef<HTMLDivElement>(null);

    // Filters & Sorting
    const [search, setSearch] = useState('');
    const [filterStatus, setFilterStatus] = useState('all'); // all, no_data, outdated_meta
    const [sort, setSort] = useState('naam');
    const [direction, setDirection] = useState('asc');

    // Initial Load
    const fetchInitialData = async () => {
        setLoading(true);
        setStatsError(false);
        try {
            const [statsRes, quadrantsRes] = await Promise.all([
                dashboardAPI.getStats(),
                dashboardAPI.getQuadrants(1)
            ]);
            setStats(statsRes.data);
            setQuadrants(quadrantsRes.data);
            // Ontologie validatie status
            try {
                const ontRes = await indicatorenAPI.getOntologieStatus();
                setOntologieStatus(ontRes.data);
            } catch (e) {
                console.warn('Ontologie status not available:', e);
            }
        } catch (error) {
            console.error('Error fetching dashboard stats:', error);
            setStatsError(true);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchInitialData();
    }, []);

    // Fetch Indicators when filters/sort change
    useEffect(() => {
        const fetchIndicators = async () => {
            setTableLoading(true);
            try {
                const res = await dashboardAPI.getIndicators({
                    search,
                    filter_status: filterStatus === 'all' ? undefined : filterStatus,
                    limit: 50,
                    sort,
                    direction
                });
                setIndicators(res.data.indicators);
            } catch (error) {
                console.error('Error fetching indicators:', error);
            } finally {
                setTableLoading(false);
            }
        };

        const debounce = setTimeout(fetchIndicators, 300);
        return () => clearTimeout(debounce);
    }, [search, filterStatus, sort, direction]);

    // Handlers
    const handleTrendIssue = () => {
        setFilterStatus('all');
        setSort('years_count');
        setDirection('asc');
        // Scroll to table
        tableRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleMetaIssue = () => {
        setFilterStatus('outdated_meta');
        setSort('naam');
        setDirection('asc');
        // Scroll to table
        tableRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleSort = (field: string) => {
        if (sort === field) {
            setDirection(direction === 'asc' ? 'desc' : 'asc');
        } else {
            setSort(field);
            setDirection('asc');
        }
    };

    const handleExport = async () => {
        try {
            const response = await dashboardAPI.getExport();
            // Create blob link to download
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            const date = new Date().toISOString().split('T')[0];
            link.setAttribute('download', `dashboard_export_${date}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            console.error('Export failed:', error);
            alert('Export mislukt. Probeer het later opnieuw.');
        }
    };

    if (loading) {
        return <div className="p-8 text-center flex flex-col items-center gap-4">
            <RefreshCw size={32} className="spin text-primary" />
            <span>Laden dashboard...</span>
        </div>;
    }

    return (
        <div style={{ maxWidth: '1600px', margin: '0 auto' }}>
            {/* 1. Header & Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h2 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>Beheer Dashboard</h2>
                    <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>Overzicht van data kwaliteit en compleetheid</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="btn btn-secondary" onClick={handleExport}>
                        <Download size={16} /> Export
                    </button>
                    <button className="btn btn-primary" onClick={fetchInitialData}>
                        <RefreshCw size={16} /> Sync Nu
                    </button>
                </div>
            </div>

            {/* Error Banner */}
            {statsError && (
                <div className="card" style={{
                    marginBottom: '2rem',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid #ef4444',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    padding: '1rem'
                }}>
                    <AlertCircle size={24} color="#ef4444" />
                    <div style={{ flex: 1 }}>
                        <h4 style={{ margin: 0, color: '#ef4444' }}>Fout bij laden statistieken</h4>
                        <p style={{ margin: 0, fontSize: '0.875rem' }}>Controleer uw verbinding of probeer opnieuw.</p>
                    </div>
                    <button className="btn btn-secondary" onClick={fetchInitialData}>Probeer opnieuw</button>
                </div>
            )}

            {/* 2. Stats Cards */}
            <div className="stats-grid" style={{ marginBottom: '2rem' }}>
                <StatsCard
                    label="Totaal Indicatoren"
                    value={stats?.total_indicators || 0}
                    subValue="Actieve definities"
                    icon={Database}
                    color="#3b82f6"
                />
                <StatsCard
                    label="Data Dekking"
                    value={`${stats?.with_data_pct || 0}%`}
                    subValue={`${stats?.with_data_count || 0} met data`}
                    icon={Layers}
                    color="#10b981"
                />
                <StatsCard
                    label="Metadata Voltooid"
                    value={`${stats?.metadata_complete_met_data_pct ?? stats?.metadata_complete_pct ?? 0}%`}
                    subValue={`Van de indicatoren met data (alle definities: ${stats?.metadata_complete_pct || 0}%)`}
                    icon={FileText}
                    color="#8b5cf6"
                />
                <StatsCard
                    label="Trending (5j+)"
                    value={stats?.trending_count || 0}
                    subValue="Langdurige reeksen"
                    icon={TrendingUp}
                    color="#f59e0b"
                />
            </div>

            {/* 2b. Ontologie Validatie Voortgang */}
            {ontologieStatus && (
                <div className="card" style={{ marginBottom: '2rem' }}>
                    <div className="card-header">
                        <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            🧠 AI Ontologie Validatie
                        </h3>
                        <span style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                            {ontologieStatus.goedgekeurd} / {ontologieStatus.totaal} goedgekeurd ({ontologieStatus.percentage_gereed}%)
                        </span>
                    </div>
                    {/* Progress bar */}
                    <div style={{ width: '100%', height: '8px', borderRadius: '4px', background: 'var(--color-surface-light, #1E293B)', marginTop: '0.75rem', overflow: 'hidden' }}>
                        <div style={{
                            height: '100%', borderRadius: '4px',
                            background: 'linear-gradient(90deg, #22C55E, #4ADE80)',
                            width: `${ontologieStatus.percentage_gereed}%`,
                            transition: 'width 0.5s ease',
                        }} />
                    </div>
                    {/* Status breakdown */}
                    <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.75rem', fontSize: '0.8rem' }}>
                        {Object.entries(ontologieStatus.statussen).map(([status, count]) => {
                            const icons: Record<string, string> = { 'draft': '🤖', 'beoordeeld_ai': '⏳', 'goedgekeurd_mens': '✅' };
                            const labels: Record<string, string> = { 'draft': 'Draft', 'beoordeeld_ai': 'AI Beoordeeld', 'goedgekeurd_mens': 'Goedgekeurd' };
                            return (
                                <span key={status} style={{ color: 'var(--color-text-secondary)' }}>
                                    {icons[status] || '❓'} {labels[status] || status}: <strong>{count as number}</strong>
                                </span>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* 3. Quadrant Overview */}
            <div className="card" style={{ marginBottom: '2rem' }}>
                <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <h3 className="card-title">Data Dekking per Kompas Kwadrant</h3>
                    <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }}></div>
                            Waarde Data
                        </div>
                    </div>
                </div>

                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                    gap: '2rem',
                    marginTop: '1rem'
                }}>
                    {quadrants.map((q, i) => (
                        <QuadrantChart
                            key={q.name}
                            name={q.name}
                            percentage={q.coverage_pct}
                            color={['#10b981', '#f59e0b', '#3b82f6', '#ef4444'][i % 4]}
                            detail={`${q.with_data} / ${q.total} indicatoren`}
                        />
                    ))}
                </div>
            </div>

            {/* 4. Detailed Table with Filters */}
            <div className="card" ref={tableRef}>
                <div className="card-header" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                    <h3 className="card-title">Gedetailleerd Beheer Overzicht</h3>

                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                        {/* Search */}
                        <div style={{ position: 'relative' }}>
                            <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
                            <input
                                type="text"
                                aria-label="Zoek indicator"
                                placeholder="Zoek indicator..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                style={{
                                    paddingLeft: '2.5rem',
                                    paddingRight: '1rem',
                                    height: '36px',
                                    borderRadius: '6px',
                                    border: '1px solid var(--color-border)',
                                    background: 'rgba(255,255,255,0.05)',
                                    color: 'var(--color-text)',
                                    width: '240px'
                                }}
                            />
                        </div>

                        {/* Filter Buttons */}
                        <div style={{ display: 'flex', gap: '0.5rem', background: 'rgba(255,255,255,0.05)', padding: '4px', borderRadius: '6px' }}>
                            <button
                                className={`btn-sm ${filterStatus === 'all' ? 'active' : ''}`}
                                onClick={() => setFilterStatus('all')}
                                style={{
                                    background: filterStatus === 'all' ? 'var(--color-primary)' : 'transparent',
                                    border: 'none',
                                    borderRadius: '4px',
                                    padding: '0.25rem 0.75rem',
                                    fontSize: '0.875rem',
                                    cursor: 'pointer',
                                    color: 'white'
                                }}
                            >
                                Alles
                            </button>
                            <button
                                className={`btn-sm ${filterStatus === 'no_data' ? 'active' : ''}`}
                                onClick={() => setFilterStatus('no_data')}
                                style={{
                                    background: filterStatus === 'no_data' ? 'var(--color-primary)' : 'transparent',
                                    border: 'none',
                                    borderRadius: '4px',
                                    padding: '0.25rem 0.75rem',
                                    fontSize: '0.875rem',
                                    cursor: 'pointer',
                                    color: 'white'
                                }}
                            >
                                Zonder Data
                            </button>
                            <button
                                className={`btn-sm ${filterStatus === 'outdated_meta' ? 'active' : ''}`}
                                onClick={() => setFilterStatus('outdated_meta')}
                                style={{
                                    background: filterStatus === 'outdated_meta' ? 'var(--color-primary)' : 'transparent',
                                    border: 'none',
                                    borderRadius: '4px',
                                    padding: '0.25rem 0.75rem',
                                    fontSize: '0.875rem',
                                    cursor: 'pointer',
                                    color: 'white'
                                }}
                            >
                                Metadata Incompleet
                            </button>
                        </div>
                    </div>
                </div>

                <IndicatorsTable
                    indicators={indicators}
                    loading={tableLoading}
                    sort={sort}
                    direction={direction}
                    onSort={handleSort}
                />

                {/* Pagination (Visual only for now) */}
                <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'center', gap: '0.5rem' }}>
                    <button className="btn btn-secondary" disabled>Vorige</button>
                    <span style={{ display: 'flex', alignItems: 'center', fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>Pagina 1</span>
                    <button className="btn btn-secondary">Volgende</button>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '2rem' }}>
                <div className="card" style={{ border: '1px solid #7f1d1d', background: 'rgba(127, 29, 29, 0.1)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <AlertCircle size={24} color="#ef4444" />
                            <div>
                                <h4 style={{ margin: 0, fontWeight: 600 }}>Missende Trendline Data</h4>
                                <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>Indicatoren met minimale historische data.</p>
                            </div>
                        </div>
                        <button
                            className="btn"
                            style={{ background: '#7f1d1d', color: 'white', border: 'none', cursor: 'pointer' }}
                            onClick={handleTrendIssue}
                        >
                            Bekijk
                        </button>
                    </div>
                </div>

                <div className="card" style={{ border: '1px solid #713f12', background: 'rgba(113, 63, 18, 0.1)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <Clock size={24} color="#f59e0b" />
                            <div>
                                <h4 style={{ margin: 0, fontWeight: 600 }}>Incomplete Metadata</h4>
                                <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>Indicatoren die documentatie missen.</p>
                            </div>
                        </div>
                        <button
                            className="btn"
                            style={{ background: '#713f12', color: 'white', border: 'none', cursor: 'pointer' }}
                            onClick={handleMetaIssue}
                        >
                            Update
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};


