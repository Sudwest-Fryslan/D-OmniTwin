import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { reportAPI, hierarchyAPI, aiAPI } from '../services/api';
import { provincieNaam, useBenchmarkProvincie } from '../hooks/useBenchmarkProvincie';
import { X, Layers, RefreshCw, Download, ArrowUpDown, Map, BarChart2, List, ChevronRight, ChevronDown } from 'lucide-react';
import * as d3 from 'd3';
import { DivergingBarChart } from '../components/charts/DivergingBarChart';
import type { HierarchyNode } from '../types';
import { ExportPrintModal } from '../components/ExportPrintModal';
import { AILabel } from '../components/AILabel';

// ─── Types ─────────────────────────────────────────────────────────────────

interface IndicatorEntry {
    indicator_naam: string;
    eenheid: string;
    thema: string;
    onderdeel: string;
    score_type: string;
    z_score: number;
    z_score_abs: number;
    impact: string;
    kleur_hex: string;
    waarde: number;
    ref_gemiddelde: number;
    ref_min: number;
    ref_max: number;
}

interface BuurtAnalyse {
    buurt_id: string;
    buurt_naam: string;
    max_z_score: number;
    max_z_score_abs: number;
    indicatoren: IndicatorEntry[];
}

interface ThemaAnalyseData {
    rapport_type: string;
    filter_beschrijving: string;
    deelgebied_naam: string;
    referentie_label: string;
    referentie_modus: string;
    totaal_buurten: number;
    buurten_met_data: number;
    buurten_analyse: BuurtAnalyse[];
}

interface GeoJSONFeature {
    type: 'Feature';
    geometry: any;
    properties: {
        buurt_id: string;
        buurt_naam: string;
        max_z_score: number;
        max_z_score_abs: number;
        kleur_hex: string;
        indicatoren: IndicatorEntry[];
    };
}

interface GeoJSONCollection {
    type: 'FeatureCollection';
    metadata: { referentie_label: string; totaal_buurten: number; filter_beschrijving: string };
    features: GeoJSONFeature[];
}

// ─── Component ─────────────────────────────────────────────────────────────

export const ThemaAnalysePage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const benchmarkProvincie = useBenchmarkProvincie();  // referentie 'provincie' (#324)

    // State
    const [referentie, setReferentie] = useState<'gemeente' | 'fryslan'>(
        (searchParams.get('ref') as 'gemeente' | 'fryslan') || 'gemeente'
    );
    const [showPrintModal, setShowPrintModal] = useState(false);
    const originalTitleRef = useRef(document.title);
    
    // Cascading filters
    const [filterMode, setFilterMode] = useState<'hierarchy' | 'ai'>('hierarchy');
    const [tree, setTree] = useState<HierarchyNode[]>([]);
    const [selectedCategorie, setSelectedCategorie] = useState<string>('');
    const [selectedThema, setSelectedThema] = useState<string>('');
    const [selectedOnderdeel, setSelectedOnderdeel] = useState<string>('');
    
    // AI Search state
    const [aiQuery, setAiQuery] = useState('');
    const [aiSuggestions, setAiSuggestions] = useState<any[]>([]);
    const [isSearchingAI, setIsSearchingAI] = useState(false);
    const aiSearchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const [data, setData] = useState<ThemaAnalyseData | null>(null);
    const [geoData, setGeoData] = useState<GeoJSONCollection | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    const [sortField, setSortField] = useState<'z_score' | 'buurt' | 'thema'>('z_score');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
    const [hoveredBuurt, setHoveredBuurt] = useState<string | null>(null);
    const [selectedChartBuurt, setSelectedChartBuurt] = useState<string | null>(null);
    const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
    const [showWoonplaatsGrenzen, setShowWoonplaatsGrenzen] = useState(true);
    const [woonplaatsGeo, setWoonplaatsGeo] = useState<any>(null);

    const svgRef = useRef<SVGSVGElement>(null);

    const gebiedIds = searchParams.get('gebieden')?.split(',').filter(Boolean) || [];
    const deelgebiedNaam = searchParams.get('naam') || `${gebiedIds.length} buurten`;
    // Zonder gemeente in de URL kiest de backend die van de eigen organisatie (#231)
    const gemeenteCode = searchParams.get('gemeente') || undefined;
    const laagId = searchParams.get('laag_id');
    const woonplaatsenParam = searchParams.get('woonplaatsen') || '';
    const woonplaatsen = useMemo(() => {
        return woonplaatsenParam ? woonplaatsenParam.split(',').map(decodeURIComponent).filter(Boolean) : [];
    }, [woonplaatsenParam]);

    // ─── Data Fetching ──────────────────────────────────────────────────────

    // Fetch Hierarchy
    useEffect(() => {
        const fetchTree = async () => {
            try {
                const res = await hierarchyAPI.getTree(1);
                if (res.data.tree && res.data.tree.length > 0) {
                    setTree(res.data.tree);
                }
            } catch (err) {
                console.error("Failed to load hierarchy tree", err);
            }
        };
        fetchTree();
    }, []);

    // Fetch Woonplaatsen GeoJSON
    useEffect(() => {
        if (laagId && woonplaatsen.length > 0) {
            fetch(`/api/externe-lagen/${laagId}/features?features=${encodeURIComponent(woonplaatsen.join(','))}`, {
                credentials: 'same-origin'
            })
                .then(r => r.json())
                .then(data => setWoonplaatsGeo(data))
                .catch(console.error);
        }
    }, [laagId, woonplaatsen]);

    const handleAiQueryChange = (query: string) => {
        setAiQuery(query);
        
        if (aiSearchTimeoutRef.current) {
            clearTimeout(aiSearchTimeoutRef.current);
        }
        
        if (query.trim().length > 2) {
            setIsSearchingAI(true);
            aiSearchTimeoutRef.current = setTimeout(async () => {
                try {
                    const response = await aiAPI.searchKompas(query, 5);
                    setAiSuggestions(response.data);
                } catch (e) {
                    console.error("Fout bij AI zoeken:", e);
                    setAiSuggestions([{ error: "Kan geen verbinding maken met AI service." }]);
                } finally {
                    setIsSearchingAI(false);
                }
            }, 300);
        } else {
            setAiSuggestions([]);
        }
    };

    const handleAiResultClick = (result: any) => {
        if (result.error) return;
        
        if (result.categorie) setSelectedCategorie(result.categorie);
        if (result.thema_naam) setSelectedThema(result.thema_naam);
        if (result.onderdeel_naam) setSelectedOnderdeel(result.onderdeel_naam);
        
        setFilterMode('hierarchy');
        setAiQuery('');
        setAiSuggestions([]);
    };

    const fetchData = async () => {
        if (gebiedIds.length === 0) return;
        setLoading(true);
        setError(null);

        const basePayload = {
            gebied_ids: gebiedIds,
            referentie: referentie,
            gemeente_code: gemeenteCode,
            categorie: selectedCategorie || undefined,
            thema_naam: selectedThema || undefined,
            onderdeel_naam: selectedOnderdeel || undefined,
            deelgebied_naam: deelgebiedNaam
        };

        try {
            const [dataRes, geoRes] = await Promise.all([
                reportAPI.getThemaAnalyse(basePayload),
                reportAPI.getThemaAnalyseGeoJSON(basePayload)
            ]);
            setData(dataRes.data);
            setGeoData(geoRes.data);
            
            // Auto-expand if only 1 buurt is selected
            if (dataRes.data.buurten_analyse && dataRes.data.buurten_analyse.length === 1) {
                setExpandedRows(new Set([dataRes.data.buurten_analyse[0].buurt_id]));
            } else {
                setExpandedRows(new Set());
            }
            
        } catch (err: any) {
            setError(err?.response?.data?.detail || err.message || 'Fout bij laden data');
        } finally {
            setLoading(false);
        }
    };

    // Geen auto-fetch on mount meer; de gebruiker moet expliciet op 'Pas Filters Toe' klikken.

    // ─── Helpers ────────────────────────────────────────────────────────────

    const toggleRowExpand = (id: string) => {
        setExpandedRows(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const toggleSort = (field: 'z_score' | 'buurt' | 'thema') => {
        if (sortField === field) {
            setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDir('desc');
        }
    };

    // Derived Options
    const categorieOptions = tree || [];
    const themaOptions = categorieOptions.find(c => c.naam === selectedCategorie)?.children || [];
    const onderdeelOptions = themaOptions.find(t => t.naam === selectedThema)?.children || [];

    // Handlers voor cascade reset
    const handleCategorieChange = (val: string) => {
        setSelectedCategorie(val);
        setSelectedThema('');
        setSelectedOnderdeel('');
    };

    const handleThemaChange = (val: string) => {
        setSelectedThema(val);
        setSelectedOnderdeel('');
    };

    const sortedBuurten = data ? [...data.buurten_analyse].sort((a, b) => {
        const m = sortDir === 'asc' ? 1 : -1;
        if (sortField === 'z_score') return (a.max_z_score_abs - b.max_z_score_abs) * m;
        if (sortField === 'buurt') return a.buurt_naam.localeCompare(b.buurt_naam) * m;
        if (sortField === 'thema') {
            const tA = a.indicatoren[0]?.thema || '';
            const tB = b.indicatoren[0]?.thema || '';
            return tA.localeCompare(tB) * m;
        }
        return 0;
    }) : [];

    // ─── Kaart Render ───────────────────────────────────────────────────────

    const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
    const [isHoveringMap, setIsHoveringMap] = useState(false);

    useEffect(() => {
        if (!svgRef.current || !geoData) return;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const width = svgRef.current.clientWidth;
        const height = svgRef.current.clientHeight;

        // Bounding box berekenen (Sorteer grootste buurten eerst om gaten te voorkomen)
        const sortedFeatures = [...geoData.features].sort(
            (a, b) => d3.geoArea(b as any) - d3.geoArea(a as any)
        );

        const projection = d3.geoMercator().fitSize(
            [width - 40, height - 40],
            { type: 'FeatureCollection', features: sortedFeatures } as any
        );

        const pathGenerator = d3.geoPath().projection(projection);

        const g = svg.append('g').attr('transform', 'translate(20,20)');

        // Achtergrond / zee
        g.append('rect')
            .attr('width', width)
            .attr('height', height)
            .attr('fill', 'transparent')
            .attr('rx', 8)
            .attr('transform', 'translate(-20,-20)');

        // Buurten tekenen
        g.selectAll('path.buurt')
            .data(sortedFeatures)
            .enter()
            .append('path')
            .attr('class', 'buurt')
            .attr('d', pathGenerator as any)
            .attr('fill', d => d.properties.kleur_hex || 'var(--color-bg-alt)')
            .attr('stroke', 'var(--color-border)')
            .attr('stroke-width', 1)
            .attr('opacity', d => hoveredBuurt === d.properties.buurt_id ? 1 : 0.85)
            .style('transition', 'all 0.2s ease')
            .style('cursor', 'pointer')
            .on('mouseenter', (event, d) => setHoveredBuurt(d.properties.buurt_id))
            .on('mouseleave', () => setHoveredBuurt(null));

        // Labels
        g.selectAll('text.buurt-label')
            .data(sortedFeatures)
            .enter()
            .append('text')
            .attr('class', 'buurt-label')
            .attr('transform', d => {
                const centroid = pathGenerator.centroid(d as any);
                return `translate(${centroid[0]},${centroid[1]})`;
            })
            .attr('text-anchor', 'middle')
            .attr('dy', '.35em')
            .text(d => d.properties.buurt_naam)
            .style('font-size', '8px')
            .style('font-weight', '600')
            .style('fill', '#1e293b')
            .style('pointer-events', 'none')
            .style('text-shadow', '1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white')
            .style('opacity', d => {
                const bounds = pathGenerator.bounds(d as any);
                const w = bounds[1][0] - bounds[0][0];
                return w > 40 ? 1 : 0; // Alleen label in grote buurten
            });

        // Woonplaatsgrenzen (Sprint 18)
        if (woonplaatsGeo && showWoonplaatsGrenzen) {
            g.append('path')
                .datum(woonplaatsGeo)
                .attr('d', pathGenerator as any)
                .attr('fill', 'none')
                .attr('stroke', '#8b5cf6')
                .attr('stroke-width', 2.5)
                .attr('stroke-dasharray', '4 4')
                .attr('pointer-events', 'none')
                .style('filter', 'drop-shadow(0px 0px 2px rgba(139, 92, 246, 0.4))');
        }

    }, [geoData, hoveredBuurt, showWoonplaatsGrenzen, woonplaatsGeo]);

    const renderChoropleth = () => {
        return (
            <div 
                style={{ width: '100%', height: '400px', position: 'relative', borderRadius: '8px', overflow: 'hidden', background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
                onMouseMove={(e) => setMousePos({ x: e.clientX, y: e.clientY })}
                onMouseEnter={() => setIsHoveringMap(true)}
                onMouseLeave={() => setIsHoveringMap(false)}
            >
                <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />
                {renderHoverPanel()}
            </div>
        );
    };

    const renderHoverPanel = () => {
        if (!hoveredBuurt || !data || !isHoveringMap) return null;
        const b = data.buurten_analyse.find(x => x.buurt_id === hoveredBuurt);
        if (!b) return null;

        return (
            <div style={{
                position: 'fixed', 
                top: mousePos.y + 15, 
                left: mousePos.x + 15, 
                width: '260px',
                background: 'rgba(30, 41, 59, 0.95)',
                backdropFilter: 'blur(4px)',
                border: '1px solid var(--color-border)', 
                borderRadius: '8px',
                padding: '1rem', 
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)', 
                zIndex: 9999,
                pointerEvents: 'none',
                color: 'white'
            }}>
                <div style={{ fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                    {b.buurt_naam}
                </div>
                {b.indicatoren.slice(0, 3).map((ind, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', padding: '0.2rem 0', borderBottom: i < 2 ? '1px solid var(--color-border)' : 'none' }}>
                        <span style={{ color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px' }} title={ind.indicator_naam}>
                            {ind.indicator_naam}
                        </span>
                        <span style={{ fontWeight: 600, color: ind.z_score_abs >= 1.5 ? '#60a5fa' : 'var(--color-text-muted)' }}>
                            {ind.z_score > 0 ? '+' : ''}{ind.z_score}
                        </span>
                    </div>
                ))}
                {b.indicatoren.length > 3 && (
                    <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: '0.25rem', fontStyle: 'italic' }}>
                        + {b.indicatoren.length - 3} andere indicatoren
                    </div>
                )}
            </div>
        );
    };

    const renderBarChart = () => {
        if (!data) return null;
        
        const buurten = data.buurten_analyse;
        const activeBuurtId = selectedChartBuurt || hoveredBuurt || buurten[0]?.buurt_id;
        const activeBuurt = buurten.find(b => b.buurt_id === activeBuurtId) || buurten[0];
        if (!activeBuurt) return null;
        
        return (
            <div style={{ width: '100%' }}>
                {buurten.length > 1 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '1rem', maxHeight: '80px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                        {buurten.map(b => (
                            <button key={b.buurt_id}
                                onClick={() => setSelectedChartBuurt(b.buurt_id)}
                                style={{
                                    background: activeBuurtId === b.buurt_id ? 'var(--color-primary)' : 'var(--color-bg-alt)',
                                    color: activeBuurtId === b.buurt_id ? '#fff' : 'var(--color-text-primary)',
                                    border: '1px solid var(--color-border)',
                                    borderRadius: '12px',
                                    padding: '0.25rem 0.6rem',
                                    fontSize: '0.75rem',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease'
                                }}
                                aria-pressed={activeBuurtId === b.buurt_id}>
                                {b.buurt_naam}
                            </button>
                        ))}
                    </div>
                )}
                <div style={{ width: '100%', background: 'var(--color-bg-alt)', borderRadius: '8px', padding: '1rem 0', minHeight: '350px' }}>
                    <DivergingBarChart indicatoren={activeBuurt.indicatoren} maxBars={15} />
                </div>
            </div>
        );
    };

    // ─── Render ─────────────────────────────────────────────────────────────

    const legendItems = [
        { color: '#1a3d5c', label: 'Zwaar Positief Afwijkend' },
        { color: '#2b6ca3', label: 'Positief Afwijkend' },
        { color: '#8c96a0', label: 'Rond Gemiddelde' },
        { color: '#d4b483', label: 'Negatief Afwijkend' },
        { color: '#c17c3e', label: 'Zwaar Negatief Afwijkend' },
    ];

    return (
        <div className="report-page" style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ margin: 0, fontSize: '1.75rem', color: 'var(--color-text-primary)' }}>
                        📊 Thema-Analyse
                    </h1>
                    <p style={{ margin: '0.5rem 0 0', color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
                        {deelgebiedNaam} — {gebiedIds.length} buurten geselecteerd
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <select
                        className="select-input"
                        aria-label="Referentie"
                        value={referentie}
                        onChange={(e) => setReferentie(e.target.value as any)}
                        style={{ padding: '0.5rem', borderRadius: 'var(--radius-md)' }}
                    >
                        <option value="gemeente">Vergelijk met Gemeente</option>
                        <option value="fryslan">Vergelijk met {provincieNaam(benchmarkProvincie)}</option>
                    </select>
                    <button className="btn btn-secondary" onClick={() => {
                        originalTitleRef.current = document.title;
                        const dateStr = new Date().toISOString().replace(/T/, '_').replace(/:/g, '').split('.')[0];
                        document.title = `ThemaAnalyse_${selectedThema || 'Alle'}_${dateStr}`;
                        setShowPrintModal(true);
                    }}>
                        <Download size={16} /> Exporteer PDF
                    </button>
                    <button className="btn btn-outline" onClick={() => window.close()}>
                        <X size={16} /> Sluiten
                    </button>
                </div>
            </div>

            {/* Cascading Filters */}
            <div className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center', position: 'relative' }}>
                <button 
                    onClick={() => setFilterMode(m => m === 'hierarchy' ? 'ai' : 'hierarchy')}
                    style={{
                        background: filterMode === 'ai' ? 'rgba(59, 130, 246, 0.15)' : 'var(--color-bg-alt)',
                        color: filterMode === 'ai' ? 'var(--color-primary)' : 'var(--color-text)',
                        border: `1px solid ${filterMode === 'ai' ? 'rgba(59, 130, 246, 0.3)' : 'var(--color-border)'}`,
                        padding: '0.4rem 0.8rem',
                        borderRadius: '999px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        fontWeight: 500,
                        transition: 'all 0.2s ease'
                    }}
                >
                    {filterMode === 'ai' ? '🤖 Stel een vraag aan AI' : '▾ Filter op Hiërarchie'}
                </button>

                {filterMode === 'hierarchy' ? (
                    <>
                        {/* Niveau 0: Categorie */}
                        <select 
                            className="select-input" 
                            aria-label="Categorie"
                            value={selectedCategorie} 
                            onChange={e => handleCategorieChange(e.target.value)}
                            style={{ minWidth: '200px' }}
                        >
                            <option value="">-- Alle Categorieën --</option>
                            {categorieOptions.map(c => (
                                <option key={c.id} value={c.naam}>{c.naam}</option>
                            ))}
                        </select>

                        {/* Niveau 1: Thema */}
                        <select 
                            className="select-input" 
                            aria-label="Thema"
                            value={selectedThema} 
                            onChange={e => handleThemaChange(e.target.value)}
                            disabled={!selectedCategorie}
                            style={{ minWidth: '200px' }}
                        >
                            <option value="">-- Alle Thema's --</option>
                            {themaOptions.map(t => (
                                <option key={t.id} value={t.naam}>{t.naam}</option>
                            ))}
                        </select>

                        {/* Niveau 2: Onderdeel */}
                        <select 
                            className="select-input" 
                            aria-label="Onderdeel"
                            value={selectedOnderdeel} 
                            onChange={e => setSelectedOnderdeel(e.target.value)}
                            disabled={!selectedThema}
                            style={{ minWidth: '200px' }}
                        >
                            <option value="">-- Alle Onderdelen --</option>
                            {onderdeelOptions.map(o => (
                                <option key={o.id} value={o.naam}>{o.naam}</option>
                            ))}
                        </select>
                    </>
                ) : (
                    <div style={{ position: 'relative', flex: 1, minWidth: '300px' }}>
                        <input
                            type="text"
                            className="text-input"
                            aria-label="Vraag aan AI: op welk thema wil je focussen?"
                            placeholder="Op welk thema wil je focussen? (bijv. veiligheid, groen)"
                            value={aiQuery}
                            onChange={e => handleAiQueryChange(e.target.value)}
                            style={{ width: '100%', padding: '0.5rem 1rem', borderRadius: '4px' }}
                        />
                        {isSearchingAI && (
                            <div style={{ position: 'absolute', right: '1rem', top: '50%', transform: 'translateY(-50%)' }}>
                                <RefreshCw size={16} className="spin" color="var(--color-primary)" />
                            </div>
                        )}
                        {aiSuggestions.length > 0 && (
                            <div style={{
                                position: 'absolute',
                                top: '100%',
                                left: 0,
                                right: 0,
                                background: 'white',
                                border: '1px solid var(--color-border)',
                                borderRadius: '4px',
                                boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                                zIndex: 10,
                                marginTop: '4px',
                                maxHeight: '300px',
                                overflowY: 'auto'
                            }}>
                                {aiSuggestions.map((s, i) => (
                                    <div 
                                        key={i}
                                        onClick={() => handleAiResultClick(s)}
                                        style={{
                                            padding: '0.75rem 1rem',
                                            cursor: s.error ? 'default' : 'pointer',
                                            borderBottom: i < aiSuggestions.length - 1 ? '1px solid var(--color-border)' : 'none',
                                            backgroundColor: 'white'
                                        }}
                                        onMouseEnter={e => { if(!s.error) e.currentTarget.style.backgroundColor = 'var(--color-bg-alt)'; }}
                                        onMouseLeave={e => { if(!s.error) e.currentTarget.style.backgroundColor = 'white'; }}
                                    >
                                        {s.error ? (
                                            <span style={{ color: '#dc2626' }}>{s.error}</span>
                                        ) : (
                                            <>
                                                <div style={{ fontWeight: 600, color: 'var(--color-primary)', fontSize: '0.9rem' }}>{s.naam}</div>
                                                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '0.2rem' }}>
                                                    {s.categorie} {s.thema_naam ? `› ${s.thema_naam}` : ''} {s.onderdeel_naam ? `› ${s.onderdeel_naam}` : ''}
                                                </div>
                                                {s.beschrijving && (
                                                    <div style={{ fontSize: '0.8rem', marginTop: '0.3rem', color: 'var(--color-text)' }}>
                                                        {s.beschrijving.length > 100 ? s.beschrijving.substring(0, 100) + '...' : s.beschrijving}
                                                    </div>
                                                )}
                                            </>
                                        )}
                                    </div>
                                ))}
                                {aiSuggestions.some(s => s.ai) && (
                                    <div style={{ padding: '0 1rem 0.75rem' }}>
                                        <AILabel usecase="C" pagina="Beheer: thema-analyse, zoeken" vraag={aiQuery}
                                            bronnen={aiSuggestions.filter(s => !s.error).map(s => s.naam)} />
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Actie knop en Actieve Filter Pill */}
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                    <button 
                        onClick={fetchData}
                        disabled={loading}
                        aria-label={loading ? 'Filters worden toegepast' : undefined}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '0.5rem',
                            padding: '0.4rem 1rem', borderRadius: '4px',
                            background: 'var(--color-primary)', color: 'white',
                            border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
                            fontSize: '0.9rem', fontWeight: 500, transition: 'all 0.2s'
                        }}
                    >
                        {loading ? <RefreshCw className="spin" size={16} /> : 'Pas Filters Toe'}
                    </button>
                    
                    {data && (
                        <span style={{
                            background: 'rgba(59, 130, 246, 0.15)',
                            color: 'var(--color-primary)',
                            padding: '0.35rem 0.75rem',
                            borderRadius: '999px',
                            fontSize: '0.8rem',
                            fontWeight: 500,
                            whiteSpace: 'nowrap',
                            border: '1px solid rgba(59, 130, 246, 0.3)'
                        }}>
                            ● {data.filter_beschrijving} ({data.buurten_analyse[0]?.indicatoren.length || 0})
                        </span>
                    )}
                </div>
            </div>

            {loading && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4rem', color: 'var(--color-text-muted)' }}>
                    <RefreshCw className="spin" size={24} style={{ marginRight: '0.5rem' }} /> Analyse wordt gegenereerd...
                </div>
            )}

            {error && (
                <div style={{ padding: '1.5rem', background: '#fee2e2', color: '#991b1b', borderRadius: 'var(--radius-md)', marginBottom: '1rem' }}>
                    <strong>Fout:</strong> {error}
                </div>
            )}

            {!loading && !error && !data && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '5rem 2rem', color: 'var(--color-text-muted)', background: 'var(--color-bg-alt)', borderRadius: '8px', border: '1px dashed var(--color-border)', marginTop: '1.5rem' }}>
                    <Layers size={48} style={{ opacity: 0.2, marginBottom: '1rem' }} />
                    <h3 style={{ margin: '0 0 0.5rem', color: 'var(--color-text-primary)', fontSize: '1.2rem' }}>Klaar om te analyseren</h3>
                    <p style={{ margin: 0, maxWidth: '450px', textAlign: 'center', fontSize: '0.9rem', lineHeight: 1.5 }}>
                        Stel je filters in en klik op <strong>Pas Filters Toe</strong> om de data voor deze buurten op te halen en uit te rekenen.
                    </p>
                </div>
            )}

            {!loading && !error && data && (
                <>
                    {/* Kaart + Grafiek grid */}
                    <div className="rapport-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
                        
                        {/* Choropleth Kaart */}
                        <div className="card" style={{ padding: '1.25rem' }}>
                            <h3 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary)' }}>
                                <Map size={18} /> Z-score Afwijkingskaart
                            </h3>
                            {woonplaatsGeo && (
                                <label style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem', cursor: 'pointer', color: 'var(--color-text-muted)' }}>
                                    <input type="checkbox" checked={showWoonplaatsGrenzen}
                                           onChange={e => setShowWoonplaatsGrenzen(e.target.checked)} />
                                    Toon woonplaatsgrenzen
                                    <span style={{ color: '#8b5cf6', fontWeight: 600 }}>━ ━</span>
                                </label>
                            )}
                            {renderChoropleth()}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginTop: '1rem', fontSize: '0.75rem' }}>
                                {legendItems.map(l => (
                                    <div key={l.color} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                        <div style={{ width: '12px', height: '12px', borderRadius: '2px', background: l.color }} />
                                        <span style={{ color: 'var(--color-text-muted)' }}>{l.label}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Grafiek Verkenning */}
                        <div className="card" style={{ padding: '1.25rem' }}>
                            <h3 style={{ margin: '0 0 1rem', color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <BarChart2 size={18} /> Detail Verkenning
                            </h3>
                            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
                                Visuele analyse van de geselecteerde indicatoren
                            </p>
                            {renderBarChart()}
                        </div>
                    </div>

                    {/* Volledige Indicatoren Tabel */}
                    <div className="card" style={{ marginBottom: '1.5rem' }}>
                        <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <h3 style={{ margin: 0, color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <List size={18} /> Indicatoren per Buurt
                            </h3>
                            <span style={{
                                background: 'var(--color-bg-alt)', padding: '0.35rem 0.75rem',
                                borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', color: 'var(--color-text-muted)'
                            }}>
                                {sortedBuurten.length} buurten
                            </span>
                        </div>
                        <table className="table" style={{ width: '100%' }}>
                            <thead>
                                <tr>
                                    <th style={{ textAlign: 'center', padding: '0.75rem 0.5rem', width: '50px' }}>#</th>
                                    <th style={{ textAlign: 'center', padding: '0.75rem 0.25rem', width: '30px' }}></th>
                                    <th style={{ textAlign: 'left', padding: '0.75rem 1rem', cursor: 'pointer' }}
                                        onClick={() => toggleSort('buurt')}>
                                        Buurt <ArrowUpDown size={12} style={{ opacity: sortField === 'buurt' ? 1 : 0.3 }} />
                                    </th>
                                    <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', cursor: 'pointer' }}
                                        onClick={() => toggleSort('thema')}>
                                        Thema / Onderdeel <ArrowUpDown size={12} style={{ opacity: sortField === 'thema' ? 1 : 0.3 }} />
                                    </th>
                                    <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Indicator</th>
                                    <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Waarde</th>
                                    <th style={{ textAlign: 'center', padding: '0.75rem 0.5rem' }}>Bereik (min–max)</th>
                                    <th style={{ textAlign: 'right', padding: '0.75rem 0.5rem', cursor: 'pointer' }}
                                        onClick={() => toggleSort('z_score')}>
                                        Z-score <ArrowUpDown size={12} style={{ opacity: sortField === 'z_score' ? 1 : 0.3 }} />
                                    </th>
                                    <th style={{ textAlign: 'right', padding: '0.75rem 1rem' }}>Impact</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortedBuurten.map((b, i) => {
                                    const isExpanded = expandedRows.has(b.buurt_id);
                                    const hasSubRows = b.indicatoren && b.indicatoren.length > 1;

                                    return (
                                        <React.Fragment key={b.buurt_id}>
                                            <tr
                                                style={{ background: hoveredBuurt === b.buurt_id ? 'var(--color-bg-alt)' : 'transparent' }}
                                                onMouseEnter={() => setHoveredBuurt(b.buurt_id)}
                                                onMouseLeave={() => setHoveredBuurt(null)}>
                                                <td style={{ textAlign: 'center', padding: '0.6rem 0.5rem', color: 'var(--color-text-muted)' }}>{i + 1}</td>
                                                <td style={{ textAlign: 'center', padding: '0.6rem 0.25rem' }}>
                                                    {hasSubRows && (
                                                        <button
                                                            onClick={() => toggleRowExpand(b.buurt_id)}
                                                            style={{
                                                                background: 'none', border: 'none', cursor: 'pointer',
                                                                color: 'var(--color-text-muted)', padding: '0.1rem',
                                                                display: 'flex', alignItems: 'center'
                                                            }}
                                                            title="Toon alle indicatoren"
                                                            aria-label={`Toon alle indicatoren voor ${b.buurt_naam}`}
                                                            aria-expanded={isExpanded}
                                                        >
                                                            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                                        </button>
                                                    )}
                                                </td>
                                                <td style={{ padding: '0.6rem 1rem' }}>
                                                    <strong>{b.buurt_naam}</strong>
                                                </td>
                                                <td style={{ padding: '0.6rem 0.5rem', fontSize: '0.85rem' }}>{b.indicatoren[0]?.thema}</td>
                                                <td style={{ padding: '0.6rem 0.5rem', fontSize: '0.85rem' }}>{b.indicatoren[0]?.indicator_naam}</td>
                                                <td style={{ textAlign: 'left', padding: '0.6rem 0.5rem', fontWeight: 'bold' }}>
                                                    {b.indicatoren[0]?.waarde} <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontWeight: 'normal' }}>{b.indicatoren[0]?.eenheid}</span>
                                                </td>
                                                <td style={{ textAlign: 'center', padding: '0.6rem 0.5rem', fontSize: '0.8rem', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                                                    {b.indicatoren[0]?.ref_min}–{b.indicatoren[0]?.ref_max}
                                                </td>
                                                <td style={{
                                                    textAlign: 'right', padding: '0.6rem 0.5rem', fontWeight: 'bold',
                                                    color: (b.indicatoren[0]?.impact || '').includes('positief') ? 'var(--color-success)' : (b.indicatoren[0]?.impact || '').includes('negatief') ? 'var(--color-danger)' : 'var(--color-text)'
                                                }}>
                                                    {(b.indicatoren[0]?.z_score || 0) > 0 ? '+' : ''}{b.indicatoren[0]?.z_score}
                                                </td>
                                                <td style={{ textAlign: 'right', padding: '0.6rem 1rem' }}>
                                                    <span className={`badge ${(b.indicatoren[0]?.impact || '').includes('positief') ? 'badge-positive' : (b.indicatoren[0]?.impact || '').includes('negatief') ? 'badge-negative' : 'badge-neutral'}`}>
                                                        {b.indicatoren[0]?.impact}
                                                    </span>
                                                </td>
                                            </tr>

                                            {isExpanded && b.indicatoren.slice(1).map((sub, si) => (
                                                <tr key={`${b.buurt_id}-sub-${si}`}
                                                    style={{ background: 'rgba(255,255,255,0.02)' }}>
                                                    <td></td>
                                                    <td style={{ textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '0.75rem', padding: '0.4rem 0.25rem' }}>
                                                        {si + 2}.
                                                    </td>
                                                    <td style={{ padding: '0.4rem 1rem', color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
                                                        ↳
                                                    </td>
                                                    <td style={{ padding: '0.4rem 0.5rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{sub.thema} / {sub.onderdeel}</td>
                                                    <td style={{ padding: '0.4rem 0.5rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{sub.indicator_naam}</td>
                                                    <td style={{ textAlign: 'left', padding: '0.4rem 0.5rem', fontWeight: 'bold', fontSize: '0.8rem', color: 'var(--color-text-primary)' }}>
                                                        {sub.waarde} <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', fontWeight: 'normal' }}>{sub.eenheid}</span>
                                                    </td>
                                                    <td style={{ textAlign: 'center', padding: '0.4rem 0.5rem', fontSize: '0.75rem', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                                                        {sub.ref_min}–{sub.ref_max}
                                                    </td>
                                                    <td style={{
                                                        textAlign: 'right', padding: '0.4rem 0.5rem', fontWeight: 'bold', fontSize: '0.8rem',
                                                        color: (sub.impact || '').includes('positief') ? 'var(--color-success)' : (sub.impact || '').includes('negatief') ? 'var(--color-danger)' : 'var(--color-text)'
                                                    }}>
                                                        {sub.z_score > 0 ? '+' : ''}{sub.z_score}
                                                    </td>
                                                    <td style={{ textAlign: 'right', padding: '0.4rem 1rem' }}>
                                                        <span className={`badge ${(sub.impact || '').includes('positief') ? 'badge-positive' : (sub.impact || '').includes('negatief') ? 'badge-negative' : 'badge-neutral'}`}>
                                                            {sub.impact}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </React.Fragment>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            <ExportPrintModal 
                isOpen={showPrintModal} 
                onClose={() => { 
                    setShowPrintModal(false); 
                    document.title = originalTitleRef.current; 
                }} 
            />
        </div>
    );
};
