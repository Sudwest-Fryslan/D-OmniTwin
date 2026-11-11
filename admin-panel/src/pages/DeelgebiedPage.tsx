import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import * as d3 from 'd3';
import { reportAPI } from '../services/api';
import { provincieNaam, useBenchmarkProvincie } from '../hooks/useBenchmarkProvincie';
import {
    ChevronDown,
    ChevronRight,
    Download,
    Printer,
    ArrowLeft,
    AlertTriangle,
    Sparkles,
    Info,
    HelpCircle,
    Building2,
    Users,
    Layers,
    FileText,
    ExternalLink,
    Map
} from 'lucide-react';

// ─── Interfaces ────────────────────────────────────────────────────────────

interface BuurtDrilldown {
    buurt_id: string;
    buurt_naam: string;
    waarde: number;
    inwoners: number;
    gewicht: number;
    buurt_z_score: number;
    verschil: number;
    verschil_pct: number;
}

interface IndicatorItem {
    indicator_uuid: string;
    indicator_naam: string;
    eenheid: string;
    score_type: string;
    gewogen_waarde: number;
    ref_gemiddelde: number;
    ref_std: number;
    ref_min: number;
    ref_max: number;
    z_score: number;
    z_score_abs: number;
    verschil: number;
    verschil_pct: number;
    impact: string;
    is_ongunstig: boolean;
    kleur_hex: string;
    omschrijving: string;
    ontologische_beschrijving: string;
    bron: string;
    n_buurten_met_data: number;
    buurten_drilldown: BuurtDrilldown[];
}

interface ThemaGroup {
    thema_naam: string;
    totaal_indicatoren: number;
    totaal_aandachtspunten: number;
    totaal_kansen: number;
    top10_aandachtspunten: IndicatorItem[];
    top10_kansen: IndicatorItem[];
}

interface KwadrantGroup {
    kwadrant_naam: string;
    kwadrant_kleur: string;
    gem_zscore: number | null;
    n_indicatoren: number;
    n_uitschieters: number;
    n_aandachtspunten: number;
    n_kansen: number;
    totaal_aandachtspunten?: number;
    totaal_kansen?: number;
    n_aandachtspunten_sterk?: number;
    n_kansen_sterk?: number;
    themas: ThemaGroup[];
}

interface BuurtWeight {
    id: string;
    naam: string;
    inwoners: number;
    gewicht: number;
    is_fallback: boolean;
}

interface MethodologieData {
    aggregatie: string;
    gewicht_bron: string;
    referentie: string;
    referentie_modus: string;
    gemeente_code: string;
    gemeente_naam: string;
    totaal_geselecteerde_buurten: number;
    waterbuurten_uitgesloten: { id: string; naam: string }[];
    actieve_buurten_telling: number;
    fallback_buurten: { id: string; naam: string }[];
    nul_inwoners_buurten: { id: string; naam: string }[];
    totaal_inwoners_gebied: number;
    z_score_formule: string;
    statistisch_effect: string;
    scoringtype_disclaimer: string;
}

interface BronItem {
    indicator_uuid: string;
    indicator_naam: string;
    bron: string;
    bron_systeem_api?: string;
    bron_tabel_referentie?: string;
    bron_url?: string;
    peildata?: string;
    laatste_controle?: string;
}

interface DeelgebiedPayload {
    deelgebied_naam: string;
    referentie_label: string;
    referentie_modus: string;
    gemeente_code: string;
    gemeente_naam: string;
    totaal_buurten: number;
    buurten_met_data: number;
    geselecteerde_buurten: BuurtWeight[];
    kwadranten: KwadrantGroup[];
    methodologie: MethodologieData;
    bronverantwoording: BronItem[];
}

// ─── Component ─────────────────────────────────────────────────────────────

export const DeelgebiedPage: React.FC = () => {
    const [searchParams, setSearchParams] = useSearchParams();
    const navigate = useNavigate();

    // Query parameters
    const gebiedIds = useMemo(
        () => searchParams.get('gebieden')?.split(',').filter(Boolean) || [],
        [searchParams]
    );
    const deelgebiedNaamParam = searchParams.get('naam') || '';
    const initialRef = (searchParams.get('ref') as 'gemeente' | 'fryslan') || 'gemeente';
    const gemeenteCode = searchParams.get('gemeente') || undefined;
    const benchmarkProvincie = useBenchmarkProvincie();  // referentie 'provincie' (#324)

    // State
    const [referentie, setReferentie] = useState<'gemeente' | 'fryslan'>(initialRef);
    const [data, setData] = useState<DeelgebiedPayload | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [geoData, setGeoData] = useState<any>(null);
    const [geoLoading, setGeoLoading] = useState(false);
    const [woonplaatsGeo, setWoonplaatsGeo] = useState<any>(null);
    const [showWoonplaatsGrenzen, setShowWoonplaatsGrenzen] = useState(true);
    const [hoveredBuurt, setHoveredBuurt] = useState<string | null>(null);
    const mapSvgRef = useRef<SVGSVGElement>(null);

    // Per thema view mode: 'aandacht' | 'kansen' (default 'aandacht')
    const [themaMode, setThemaMode] = useState<Record<string, 'aandacht' | 'kansen'>>({});

    // Accordion state
    const [expandedThemas, setExpandedThemas] = useState<Set<string>>(new Set());
    const [expandedDrilldowns, setExpandedDrilldowns] = useState<Set<string>>(new Set());
    const [expandedOntologie, setExpandedOntologie] = useState<Set<string>>(new Set());
    const [isMethodologieOpen, setIsMethodologieOpen] = useState(false);
    const [isBronverantwoordingOpen, setIsBronverantwoordingOpen] = useState(false);

    // Fetch data
    useEffect(() => {
        if (!gebiedIds.length) {
            setError('Geen buurten geselecteerd voor het rapport.');
            return;
        }

        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const res = await reportAPI.getDeelgebied({
                    gebied_ids: gebiedIds,
                    referentie,
                    gemeente_code: gemeenteCode,
                    deelgebied_naam: deelgebiedNaamParam || undefined
                });
                setData(res.data);

                // Default expand the first theme of each quadrant
                const initialExpandedThemas = new Set<string>();
                res.data.kwadranten?.forEach((kw: KwadrantGroup) => {
                    if (kw.themas && kw.themas.length > 0) {
                        initialExpandedThemas.add(`${kw.kwadrant_naam}::${kw.themas[0].thema_naam}`);
                    }
                });
                setExpandedThemas(initialExpandedThemas);
            } catch (err: any) {
                console.error('Fout bij ophalen deelgebied data:', err);
                setError(err.response?.data?.detail || 'Fout bij het ophalen van het deelgebiedsrapport.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [gebiedIds, referentie, gemeenteCode, deelgebiedNaamParam]);

    // Fetch GeoJSON voor kaart (parallel, non-blocking)
    useEffect(() => {
        if (!gebiedIds.length) return;
        setGeoLoading(true);
        reportAPI.getMultiGebiedGeoJSON({
            gebied_ids: gebiedIds,
            referentie,
            gemeente_code: gemeenteCode
        })
            .then(res => setGeoData(res.data))
            .catch(err => console.warn('Kaart GeoJSON kon niet worden geladen:', err))
            .finally(() => setGeoLoading(false));
    }, [gebiedIds, referentie, gemeenteCode]);

    // Fetch Woonplaats/Deelgebied contouren (paarse stippellijn)
    useEffect(() => {
        const laagId = searchParams.get('laag_id');
        const woonplaatsenParam = searchParams.get('woonplaatsen')?.split(',').map(decodeURIComponent).filter(Boolean) || [];

        if (laagId) {
            fetch(`/api/externe-lagen/${laagId}/features`)
                .then(r => r.ok ? r.json() : null)
                .then(allFeatures => {
                    if (allFeatures?.features) {
                        const filtered = allFeatures.features.filter((f: any) =>
                            woonplaatsenParam.includes(f.properties?.woonplaats || f.properties?.naam)
                        );
                        if (filtered.length > 0) {
                            setWoonplaatsGeo({ type: 'FeatureCollection', features: filtered });
                        }
                    }
                })
                .catch(err => console.warn('Woonplaatslaag niet beschikbaar:', err));
        } else {
            // Fallback via pg_featureserv: haal omgevingsvisie-deelgebied op
            fetch('/api/geo/collections/public.omgevingsvisie_deelgebieden/items?limit=100')
                .then(r => r.ok ? r.json() : null)
                .then(allFeatures => {
                    if (allFeatures?.features) {
                        const targetNaam = (deelgebiedNaamParam || '').toLowerCase();
                        const matched = allFeatures.features.filter((f: any) => {
                            const dName = (f.properties?.deelgebied || '').toLowerCase();
                            const nName = (f.properties?.naam || '').toLowerCase();
                            return dName === targetNaam || nName === targetNaam || nName.includes(targetNaam);
                        });
                        if (matched.length > 0) {
                            setWoonplaatsGeo({ type: 'FeatureCollection', features: matched });
                        }
                    }
                })
                .catch(err => console.warn('Omgevingsvisie deelgebieden niet beschikbaar:', err));
        }
    }, [deelgebiedNaamParam, searchParams]);

    // Legenda items (conform Multi-Gebiedsdossier)
    const legendItems = [
        { color: '#8c96a0', label: 'In lijn (|z| < 0.5)' },
        { color: '#d4b483', label: 'Licht (0.5–1.0)' },
        { color: '#c17c3e', label: 'Matig (1.0–1.5)' },
        { color: '#2b6ca3', label: 'Sterk (1.5–2.0)' },
        { color: '#1a3d5c', label: 'Extreem (> 2.0)' },
    ];

    // D3 Choropleth renderen
    const renderChoropleth = () => {
        if (geoLoading) {
            return (
                <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{
                        width: '24px',
                        height: '24px',
                        border: '2px solid var(--color-border)',
                        borderTopColor: 'var(--color-primary)',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite'
                    }} />
                </div>
            );
        }

        if (!geoData || !geoData.features || geoData.features.length === 0) {
            return (
                <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
                    Geen kaartdata beschikbaar
                </div>
            );
        }

        const width = 460;
        const height = 340;

        const sortedFeatures = [...geoData.features].sort((a: any, b: any) => {
            const aZ = a.properties?.max_z_score_abs || 0;
            const bZ = b.properties?.max_z_score_abs || 0;
            return aZ - bZ;
        });

        const projection = d3.geoMercator().fitSize(
            [width - 24, height - 24],
            { type: 'FeatureCollection', features: sortedFeatures } as any
        );

        projection.translate([
            (projection.translate()[0] || 0) + 12,
            (projection.translate()[1] || 0) + 12
        ]);

        const pathGenerator = d3.geoPath().projection(projection);

        return (
            <svg ref={mapSvgRef} viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
                {sortedFeatures.map((f: any) => {
                    const isHovered = hoveredBuurt === f.properties.buurt_id;
                    const d = pathGenerator(f as any) || '';

                    return (
                        <path
                            key={f.properties.buurt_id}
                            d={d}
                            fill={f.properties.kleur_hex}
                            stroke={isHovered ? '#fff' : '#334155'}
                            strokeWidth={isHovered ? 2 : 0.6}
                            opacity={isHovered ? 1 : 0.85}
                            style={{ cursor: 'pointer', transition: 'opacity 0.15s, stroke-width 0.15s' }}
                            onMouseEnter={() => setHoveredBuurt(f.properties.buurt_id)}
                            onMouseLeave={() => setHoveredBuurt(null)}
                        >
                            <title>{`${f.properties.buurt_naam}\n${f.properties.indicator_naam || 'Indicator'}: z=${f.properties.max_z_score}\n${f.properties.impact || ''}`}</title>
                        </path>
                    );
                })}
                {/* Woonplaatsgrenzen overlay (paarse stippellijn) */}
                {showWoonplaatsGrenzen && woonplaatsGeo?.features?.map((f: any, i: number) => (
                    <path
                        key={`wp-${i}`}
                        d={pathGenerator(f as any) || ''}
                        fill="none"
                        stroke="#8b5cf6"
                        strokeWidth={2.5}
                        strokeDasharray="6,3"
                        opacity={0.85}
                        pointerEvents="none"
                    >
                        <title>{f.properties?.woonplaats || f.properties?.deelgebied || f.properties?.naam}</title>
                    </path>
                ))}
            </svg>
        );
    };

    // Handle referentie change
    const handleReferentieChange = (newRef: 'gemeente' | 'fryslan') => {
        setReferentie(newRef);
        const newParams = new URLSearchParams(searchParams);
        newParams.set('ref', newRef);
        setSearchParams(newParams);
    };

    // Toggle theme accordion
    const toggleThema = (key: string) => {
        setExpandedThemas(prev => {
            const next = new Set(prev);
            if (next.has(key)) {
                next.delete(key);
            } else {
                next.add(key);
            }
            return next;
        });
    };

    // Toggle drilldown
    const toggleDrilldown = (uuid: string) => {
        setExpandedDrilldowns(prev => {
            const next = new Set(prev);
            if (next.has(uuid)) {
                next.delete(uuid);
            } else {
                next.add(uuid);
            }
            return next;
        });
    };

    // Toggle ontologie
    const toggleOntologie = (uuid: string) => {
        setExpandedOntologie(prev => {
            const next = new Set(prev);
            if (next.has(uuid)) {
                next.delete(uuid);
            } else {
                next.add(uuid);
            }
            return next;
        });
    };

    // Set view mode for a theme
    const setModeForThema = (themeKey: string, mode: 'aandacht' | 'kansen') => {
        setThemaMode(prev => ({ ...prev, [themeKey]: mode }));
    };

    // Scroll to quadrant
    const scrollToKwadrant = (kwadrantNaam: string) => {
        const id = `kwadrant-${kwadrantNaam.toLowerCase().replace(/[^a-z0-9]/g, '-')}`;
        const el = document.getElementById(id);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    // Export CSV
    const exportCSV = () => {
        if (!data) return;

        const headers = [
            'Kwadrant',
            'Thema',
            'Type',
            'Rang',
            'Indicator',
            'Gewogen Waarde',
            'Eenheid',
            'Referentie Gemiddelde',
            'Referentie Std',
            'Z-Score',
            'Impact',
            'Score Type',
            'Aantal Buurten met Data',
            'Bron'
        ];

        const rows: string[][] = [];

        data.kwadranten.forEach(kw => {
            kw.themas.forEach(th => {
                // Aandachtspunten
                th.top10_aandachtspunten.forEach((item, idx) => {
                    rows.push([
                        `"${kw.kwadrant_naam}"`,
                        `"${th.thema_naam}"`,
                        '"Aandachtspunt"',
                        `${idx + 1}`,
                        `"${item.indicator_naam.replace(/"/g, '""')}"`,
                        `${item.gewogen_waarde}`,
                        `"${item.eenheid}"`,
                        `${item.ref_gemiddelde}`,
                        `${item.ref_std}`,
                        `${item.z_score}`,
                        `"${item.impact}"`,
                        `"${item.score_type}"`,
                        `${item.n_buurten_met_data}`,
                        `"${item.bron.replace(/"/g, '""')}"`
                    ]);
                });

                // Kansen
                th.top10_kansen.forEach((item, idx) => {
                    rows.push([
                        `"${kw.kwadrant_naam}"`,
                        `"${th.thema_naam}"`,
                        '"Kans"',
                        `${idx + 1}`,
                        `"${item.indicator_naam.replace(/"/g, '""')}"`,
                        `${item.gewogen_waarde}`,
                        `"${item.eenheid}"`,
                        `${item.ref_gemiddelde}`,
                        `${item.ref_std}`,
                        `${item.z_score}`,
                        `"${item.impact}"`,
                        `"${item.score_type}"`,
                        `${item.n_buurten_met_data}`,
                        `"${item.bron.replace(/"/g, '""')}"`
                    ]);
                });
            });
        });

        const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(';'), ...rows.map(r => r.join(';'))].join('\n');
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute(
            'download',
            `deelgebiedsanalyse_${(data.deelgebied_naam || 'gebied').toLowerCase().replace(/\s+/g, '_')}_${referentie}.csv`
        );
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // Print
    const handlePrint = () => {
        try {
            if (window.opener) {
                window.opener = null;
            }
        } catch {
            // negeer mogelijke restricties
        }
        window.print();
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', gap: '1rem' }}>
                <div className="spinner" style={{ width: '40px', height: '40px', border: '3px solid var(--color-border)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.95rem' }}>
                    Deelgebiedsanalyse berekenen (gewogen gemiddelden & z-scores)...
                </p>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div style={{ maxWidth: '800px', margin: '3rem auto', padding: '2rem', background: 'var(--color-surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', textAlign: 'center' }}>
                <AlertTriangle size={48} color="#ef4444" style={{ margin: '0 auto 1rem' }} />
                <h2 style={{ color: 'var(--color-text-primary)', marginBottom: '0.5rem' }}>Analyse kon niet worden geladen</h2>
                <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem' }}>{error || 'Geen gegevens beschikbaar voor de geselecteerde buurten.'}</p>
                <button
                    onClick={() => navigate(-1)}
                    style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.6rem 1.2rem',
                        background: 'var(--color-primary)',
                        color: 'white',
                        border: 'none',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        fontWeight: 500
                    }}
                >
                    <ArrowLeft size={16} /> Terug naar kaart
                </button>
            </div>
        );
    }

    const { deelgebied_naam, referentie_label, kwadranten, methodologie, bronverantwoording } = data;

    return (
        <div className="deelgebied-report-container" style={{ maxWidth: '1400px', margin: '0 auto', padding: '2rem 1.5rem', color: 'var(--color-text-primary)' }}>
            {/* ─── HEADER ──────────────────────────────────────────────────────── */}
            <header className="report-header-banner no-print" style={{
                background: 'var(--color-surface)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--color-border)',
                padding: '1.75rem 2rem',
                marginBottom: '2rem',
                boxShadow: 'var(--shadow-sm)',
                display: 'grid',
                gridTemplateColumns: 'minmax(0, 1.05fr) minmax(440px, 0.95fr)',
                gap: '1.75rem',
                alignItems: 'start'
            }}>
                {/* Left column: metadata + controls */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                            <span style={{ fontSize: '1.5rem' }}>🏘️</span>
                            <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
                                {deelgebied_naam}
                            </h1>
                            <span style={{
                                fontSize: '0.8rem',
                                fontWeight: 600,
                                padding: '0.2rem 0.6rem',
                                borderRadius: '999px',
                                background: 'rgba(59, 130, 246, 0.1)',
                                color: '#3B82F6',
                                border: '1px solid rgba(59, 130, 246, 0.2)'
                            }}>
                                Woonplaats- & Deelgebiedsanalyse
                            </span>
                        </div>

                        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '1.25rem', color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                <Building2 size={15} /> <strong>{methodologie.actieve_buurten_telling}</strong> buurten
                                {methodologie.waterbuurten_uitgesloten?.length > 0 && (
                                    <span style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
                                        ({methodologie.waterbuurten_uitgesloten.length} watergebied{methodologie.waterbuurten_uitgesloten.length > 1 ? 'en' : ''} uitgesloten)
                                    </span>
                                )}
                            </span>
                            <span>•</span>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                <Users size={15} /> <strong>{methodologie.totaal_inwoners_gebied.toLocaleString('nl-NL')}</strong> inwoners (gewogen)
                            </span>
                            <span>•</span>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                <Layers size={15} /> Referentiekader: <strong style={{ color: 'var(--color-text-primary)' }}>{referentie_label}</strong>
                            </span>
                        </div>
                    </div>

                    {/* Controls & Exports */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                        {/* Referentie Toggle */}
                        <div style={{
                            display: 'flex',
                            background: 'var(--color-bg-alt)',
                            padding: '0.25rem',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--color-border)'
                        }}>
                            <button
                                onClick={() => handleReferentieChange('gemeente')}
                                style={{
                                    padding: '0.45rem 0.9rem',
                                    fontSize: '0.85rem',
                                    fontWeight: 500,
                                    border: 'none',
                                    borderRadius: 'calc(var(--radius-md) - 2px)',
                                    cursor: 'pointer',
                                    background: referentie === 'gemeente' ? 'var(--color-primary)' : 'transparent',
                                    color: referentie === 'gemeente' ? 'white' : 'var(--color-text-secondary)',
                                    transition: 'all 0.15s ease'
                                }}
                            >
                                ⌀ {methodologie.gemeente_naam || 'Gemeente'}
                            </button>
                            <button
                                onClick={() => handleReferentieChange('fryslan')}
                                style={{
                                    padding: '0.45rem 0.9rem',
                                    fontSize: '0.85rem',
                                    fontWeight: 500,
                                    border: 'none',
                                    borderRadius: 'calc(var(--radius-md) - 2px)',
                                    cursor: 'pointer',
                                    background: referentie === 'fryslan' ? 'var(--color-primary)' : 'transparent',
                                    color: referentie === 'fryslan' ? 'white' : 'var(--color-text-secondary)',
                                    transition: 'all 0.15s ease'
                                }}
                            >
                                ⌀ {provincieNaam(benchmarkProvincie)}
                            </button>
                        </div>

                        <button
                            onClick={exportCSV}
                            title="Download analyse als CSV bestand"
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.55rem 1rem',
                                background: 'var(--color-surface)',
                                border: '1px solid var(--color-border)',
                                borderRadius: 'var(--radius-md)',
                                color: 'var(--color-text-primary)',
                                fontSize: '0.85rem',
                                fontWeight: 500,
                                cursor: 'pointer'
                            }}
                        >
                            <Download size={15} /> CSV
                        </button>

                        <button
                            onClick={handlePrint}
                            title="Rapport afdrukken of exporteren naar PDF"
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.55rem 1rem',
                                background: 'var(--color-primary)',
                                border: 'none',
                                borderRadius: 'var(--radius-md)',
                                color: 'white',
                                fontSize: '0.85rem',
                                fontWeight: 500,
                                cursor: 'pointer',
                                boxShadow: 'var(--shadow-sm)'
                            }}
                        >
                            <Printer size={15} /> Print / PDF
                        </button>
                    </div>
                </div>

                {/* Right column: D3 Afwijkingskaart (~48% van het beeld) */}
                <div style={{
                    background: 'var(--color-bg-alt, #161f2e)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1.25rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem',
                    width: '100%'
                }}>
                    {/* Bovenste rij: titel + lagen-toggle */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <Map size={16} /> Afwijkingskaart
                        </span>
                        {woonplaatsGeo && (
                            <label style={{ fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', color: 'var(--color-text-muted)' }}>
                                <input
                                    type="checkbox"
                                    checked={showWoonplaatsGrenzen}
                                    onChange={e => setShowWoonplaatsGrenzen(e.target.checked)}
                                />
                                Woonplaatsgrens
                                <span style={{ color: '#8b5cf6', fontWeight: 700 }}>━ ━</span>
                            </label>
                        )}
                    </div>

                    {/* Onderste rij: legenda links (auto) + kaart rechts (flex:1) */}
                    <div style={{ display: 'flex', gap: '0.75rem', flex: 1, minHeight: 0 }}>
                        {/* Linker subkolom: legenda + hover-info */}
                        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', flexShrink: 0 }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.72rem' }}>
                                {legendItems.map(l => (
                                    <div key={l.color} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                        <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: l.color, flexShrink: 0 }} />
                                        <span style={{ color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>{l.label}</span>
                                    </div>
                                ))}
                            </div>
                            {hoveredBuurt && (
                                <div style={{
                                    fontSize: '0.72rem',
                                    color: 'var(--color-text-secondary)',
                                    marginTop: '0.5rem',
                                    maxWidth: '140px',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis'
                                }}>
                                    {(() => {
                                        const feat = geoData?.features?.find((f: any) => f.properties.buurt_id === hoveredBuurt);
                                        if (!feat) return null;
                                        return (
                                            <span>
                                                <strong>{feat.properties.buurt_naam}</strong><br/>
                                                z={feat.properties.max_z_score > 0 ? '+' : ''}{feat.properties.max_z_score}
                                            </span>
                                        );
                                    })()}
                                </div>
                            )}
                        </div>

                        {/* Rechter subkolom: D3 kaart */}
                        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: 0 }}>
                            {renderChoropleth()}
                        </div>
                    </div>
                </div>
            </header>

            {/* Print-only Header */}
            <div className="print-only" style={{ display: 'none', marginBottom: '1.5rem', borderBottom: '2px solid #333', paddingBottom: '1rem' }}>
                <h1 style={{ margin: 0, fontSize: '2rem' }}>{deelgebied_naam} — Woonplaats- & Deelgebiedsanalyse</h1>
                <p style={{ margin: '0.25rem 0', color: '#666' }}>
                    {methodologie.actieve_buurten_telling} buurten | {methodologie.totaal_inwoners_gebied.toLocaleString('nl-NL')} inwoners | Referentie: {referentie_label} | Gegenereerd op {new Date().toLocaleDateString('nl-NL')}
                </p>
            </div>

            {/* ─── SECTIE 1: SCOREKAARTEN PER KWADRANT ─────────────────────────── */}
            <section style={{ marginBottom: '2.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                    <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Overzicht per Kwadrant
                    </h2>
                    <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                        Klik op een kaart om naar het desbetreffende kwadrant te springen
                    </span>
                </div>

                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                    gap: '1rem'
                }}>
                    {kwadranten.map(kw => {
                        const gemZscore = kw.gem_zscore;
                        const heeftGemZscore = gemZscore !== null && gemZscore !== undefined;
                        const isPos = heeftGemZscore && gemZscore > 0;
                        const zColor = !heeftGemZscore
                            ? '#475569'
                            : Math.abs(gemZscore) >= 1.0
                              ? '#2b6ca3'
                              : Math.abs(gemZscore) >= 0.5
                                ? '#d4b483'
                                : '#8c96a0';

                        return (
                            <div
                                key={kw.kwadrant_naam}
                                onClick={() => scrollToKwadrant(kw.kwadrant_naam)}
                                className="kwadrant-scorekaart"
                                style={{
                                    background: 'var(--color-surface)',
                                    borderRadius: 'var(--radius-lg)',
                                    border: '1px solid var(--color-border)',
                                    padding: '1.25rem 1.5rem',
                                    cursor: 'pointer',
                                    transition: 'transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease',
                                    position: 'relative',
                                    overflow: 'hidden'
                                }}
                            >
                                <div style={{
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    height: '4px',
                                    background: kw.kwadrant_kleur || 'var(--color-primary)'
                                }} />

                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                                    <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                                        {kw.kwadrant_naam}
                                    </h3>
                                    <span style={{
                                        fontSize: '0.85rem',
                                        fontWeight: 700,
                                        padding: '0.2rem 0.55rem',
                                        borderRadius: 'var(--radius-sm)',
                                        background: zColor,
                                        color: 'white'
                                    }}>
                                        {heeftGemZscore ? `${isPos ? '+' : ''}${gemZscore.toFixed(2)} Z` : 'Neutraal'}
                                    </span>
                                </div>

                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1rem', fontSize: '0.825rem', color: 'var(--color-text-secondary)' }}>
                                    <div
                                        style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                                        title={`Totaal ${kw.totaal_aandachtspunten ?? kw.n_aandachtspunten} aandachtspunten, waarvan ${kw.n_aandachtspunten_sterk ?? 0} met een sterke afwijking (|Z| ≥ 1.0)`}
                                    >
                                        <AlertTriangle size={14} color="#f59e0b" />
                                        <span>
                                            <strong>{kw.totaal_aandachtspunten ?? kw.n_aandachtspunten}</strong> aandacht
                                            {kw.n_aandachtspunten_sterk !== undefined && (
                                                <span style={{ opacity: 0.65, fontSize: '0.75rem', marginLeft: '0.25rem' }}>
                                                    ({kw.n_aandachtspunten_sterk} sterk)
                                                </span>
                                            )}
                                        </span>
                                    </div>
                                    <div
                                        style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                                        title={`Totaal ${kw.totaal_kansen ?? kw.n_kansen} kansen, waarvan ${kw.n_kansen_sterk ?? 0} met een sterke afwijking (|Z| ≥ 1.0)`}
                                    >
                                        <Sparkles size={14} color="#10b981" />
                                        <span>
                                            <strong>{kw.totaal_kansen ?? kw.n_kansen}</strong> kansen
                                            {kw.n_kansen_sterk !== undefined && (
                                                <span style={{ opacity: 0.65, fontSize: '0.75rem', marginLeft: '0.25rem' }}>
                                                    ({kw.n_kansen_sterk} sterk)
                                                </span>
                                            )}
                                        </span>
                                    </div>
                                    <div style={{ color: 'var(--color-text-muted)' }}>
                                        {kw.n_indicatoren} indicatoren
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </section>

            {/* ─── SECTIE 2: ANALYSE PER KWADRANT & THEMA ──────────────────────── */}
            <section style={{ marginBottom: '3rem' }}>
                {kwadranten.map(kw => {
                    const kwId = `kwadrant-${kw.kwadrant_naam.toLowerCase().replace(/[^a-z0-9]/g, '-')}`;

                    return (
                        <div key={kw.kwadrant_naam} id={kwId} style={{ marginBottom: '2.5rem', scrollMarginTop: '1.5rem' }}>
                            {/* Kwadrant Header */}
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                paddingBottom: '0.75rem',
                                borderBottom: `2px solid ${kw.kwadrant_kleur || 'var(--color-primary)'}`,
                                marginBottom: '1.25rem'
                            }}>
                                <div style={{
                                    width: '12px',
                                    height: '12px',
                                    borderRadius: '50%',
                                    background: kw.kwadrant_kleur || 'var(--color-primary)'
                                }} />
                                <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700 }}>
                                    {kw.kwadrant_naam}
                                </h2>
                                <span style={{
                                    fontSize: '0.8rem',
                                    color: 'var(--color-text-muted)',
                                    marginLeft: 'auto'
                                }}>
                                    {kw.themas?.length || 0} thema's |{' '}
                                    {kw.gem_zscore !== null && kw.gem_zscore !== undefined
                                        ? `Gemiddeld ${kw.gem_zscore > 0 ? '+' : ''}${kw.gem_zscore.toFixed(2)} Z`
                                        : 'Beschrijvend (geen normatief gemiddelde)'}
                                </span>
                            </div>

                            {/* Thema Accordions */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                {kw.themas.map(th => {
                                    const themeKey = `${kw.kwadrant_naam}::${th.thema_naam}`;
                                    const isOpen = expandedThemas.has(themeKey);
                                    const currentMode = themaMode[themeKey] || 'aandacht';
                                    const itemsToShow = currentMode === 'aandacht' ? th.top10_aandachtspunten : th.top10_kansen;

                                    return (
                                        <div
                                            key={th.thema_naam}
                                            style={{
                                                background: 'var(--color-surface)',
                                                borderRadius: 'var(--radius-md)',
                                                border: '1px solid var(--color-border)',
                                                overflow: 'hidden'
                                            }}
                                        >
                                            {/* Thema Header Bar */}
                                            <div
                                                onClick={() => toggleThema(themeKey)}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'space-between',
                                                    padding: '1rem 1.25rem',
                                                    cursor: 'pointer',
                                                    background: isOpen ? 'var(--color-bg-alt)' : 'var(--color-surface)',
                                                    borderBottom: isOpen ? '1px solid var(--color-border)' : 'none',
                                                    transition: 'background 0.15s ease'
                                                }}
                                            >
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                    {isOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                                    <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>
                                                        Thema: {th.thema_naam}
                                                    </h3>
                                                    <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                                                        ({th.totaal_indicatoren} indicatoren)
                                                    </span>
                                                </div>

                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                    <span style={{
                                                        fontSize: '0.775rem',
                                                        padding: '0.2rem 0.5rem',
                                                        borderRadius: '999px',
                                                        background: 'rgba(239, 68, 68, 0.1)',
                                                        color: '#ef4444',
                                                        fontWeight: 500
                                                    }}>
                                                        {th.totaal_aandachtspunten} aandacht
                                                    </span>
                                                    <span style={{
                                                        fontSize: '0.775rem',
                                                        padding: '0.2rem 0.5rem',
                                                        borderRadius: '999px',
                                                        background: 'rgba(16, 185, 129, 0.1)',
                                                        color: '#10b981',
                                                        fontWeight: 500
                                                    }}>
                                                        {th.totaal_kansen} kansen
                                                    </span>
                                                </div>
                                            </div>

                                            {/* Thema Body */}
                                            {isOpen && (
                                                <div style={{ padding: '1.25rem' }}>
                                                    {/* Mode Switcher: Aandachtspunten vs Kansen */}
                                                    <div style={{
                                                        display: 'flex',
                                                        justifyContent: 'space-between',
                                                        alignItems: 'center',
                                                        marginBottom: '1rem',
                                                        flexWrap: 'wrap',
                                                        gap: '0.75rem'
                                                    }}>
                                                        <div style={{
                                                            display: 'inline-flex',
                                                            background: 'var(--color-bg-alt)',
                                                            padding: '0.2rem',
                                                            borderRadius: 'var(--radius-md)',
                                                            border: '1px solid var(--color-border)'
                                                        }}>
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); setModeForThema(themeKey, 'aandacht'); }}
                                                                style={{
                                                                    display: 'inline-flex',
                                                                    alignItems: 'center',
                                                                    gap: '0.4rem',
                                                                    padding: '0.4rem 0.8rem',
                                                                    fontSize: '0.825rem',
                                                                    fontWeight: 600,
                                                                    border: 'none',
                                                                    borderRadius: 'calc(var(--radius-md) - 2px)',
                                                                    cursor: 'pointer',
                                                                    background: currentMode === 'aandacht' ? 'rgba(239, 68, 68, 0.15)' : 'transparent',
                                                                    color: currentMode === 'aandacht' ? '#dc2626' : 'var(--color-text-secondary)'
                                                                }}
                                                            >
                                                                <AlertTriangle size={14} />
                                                                Top 10 Aandachtspunten ({th.top10_aandachtspunten.length})
                                                            </button>
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); setModeForThema(themeKey, 'kansen'); }}
                                                                style={{
                                                                    display: 'inline-flex',
                                                                    alignItems: 'center',
                                                                    gap: '0.4rem',
                                                                    padding: '0.4rem 0.8rem',
                                                                    fontSize: '0.825rem',
                                                                    fontWeight: 600,
                                                                    border: 'none',
                                                                    borderRadius: 'calc(var(--radius-md) - 2px)',
                                                                    cursor: 'pointer',
                                                                    background: currentMode === 'kansen' ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                                                                    color: currentMode === 'kansen' ? '#059669' : 'var(--color-text-secondary)'
                                                                }}
                                                            >
                                                                <Sparkles size={14} />
                                                                Top 10 Kansen ({th.top10_kansen.length})
                                                            </button>
                                                        </div>

                                                        <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                                                            {currentMode === 'aandacht'
                                                                ? 'Uitschieters met een ongunstige afwijking t.o.v. de referentie'
                                                                : 'Uitschieters met een gunstige afwijking t.o.v. de referentie'}
                                                        </span>
                                                    </div>

                                                    {/* Top 10 Table */}
                                                    {itemsToShow.length === 0 ? (
                                                        <p style={{ color: 'var(--color-text-muted)', fontStyle: 'italic', margin: '1rem 0' }}>
                                                            Geen indicatoren gevonden in deze categorie.
                                                        </p>
                                                    ) : (
                                                        <div style={{ overflowX: 'auto' }}>
                                                            <table style={{
                                                                width: '100%',
                                                                borderCollapse: 'collapse',
                                                                fontSize: '0.875rem',
                                                                textAlign: 'left'
                                                            }}>
                                                                <thead>
                                                                    <tr style={{
                                                                        borderBottom: '2px solid var(--color-border)',
                                                                        color: 'var(--color-text-secondary)'
                                                                    }}>
                                                                        <th style={{ padding: '0.6rem 0.5rem', width: '35px' }}>#</th>
                                                                        <th style={{ padding: '0.6rem 0.75rem' }}>Indicator</th>
                                                                        <th style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>Gewogen Waarde</th>
                                                                        <th style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>Ref. Gemiddelde</th>
                                                                        <th style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>Z-Score</th>
                                                                        <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center', width: '90px' }}>Acties</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {itemsToShow.map((item, idx) => {
                                                                        const isDrilldownOpen = expandedDrilldowns.has(item.indicator_uuid);
                                                                        const isOntologieOpen = expandedOntologie.has(item.indicator_uuid);

                                                                        return (
                                                                            <React.Fragment key={item.indicator_uuid}>
                                                                                <tr style={{
                                                                                    borderBottom: '1px solid var(--color-border)',
                                                                                    background: isDrilldownOpen || isOntologieOpen ? 'var(--color-bg-alt)' : 'transparent',
                                                                                    transition: 'background 0.15s ease'
                                                                                }}>
                                                                                    <td style={{ padding: '0.75rem 0.5rem', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                                                                                        {idx + 1}
                                                                                    </td>
                                                                                    <td style={{ padding: '0.75rem 0.75rem' }}>
                                                                                        <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                                                                                            {item.indicator_naam}
                                                                                        </div>
                                                                                        <div style={{ fontSize: '0.775rem', color: 'var(--color-text-muted)' }}>
                                                                                            Impact: {item.impact}
                                                                                            {item.eenheid && ` • Eenheid: ${item.eenheid}`}
                                                                                        </div>
                                                                                    </td>
                                                                                    <td style={{ padding: '0.75rem 0.75rem', textAlign: 'right', fontWeight: 600 }}>
                                                                                        {item.gewogen_waarde.toLocaleString('nl-NL')} {item.eenheid}
                                                                                    </td>
                                                                                    <td style={{ padding: '0.75rem 0.75rem', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                                                                                        {item.ref_gemiddelde.toLocaleString('nl-NL')} {item.eenheid}
                                                                                    </td>
                                                                                    <td style={{ padding: '0.75rem 0.75rem', textAlign: 'right' }}>
                                                                                        <span style={{
                                                                                            display: 'inline-block',
                                                                                            padding: '0.25rem 0.6rem',
                                                                                            borderRadius: 'var(--radius-sm)',
                                                                                            background: item.kleur_hex,
                                                                                            color: 'white',
                                                                                            fontWeight: 700,
                                                                                            fontSize: '0.8rem'
                                                                                        }}>
                                                                                            {item.z_score > 0 ? '+' : ''}{item.z_score.toFixed(2)}
                                                                                        </span>
                                                                                    </td>
                                                                                    <td style={{ padding: '0.75rem 0.75rem', textAlign: 'center' }}>
                                                                                        <div style={{ display: 'inline-flex', gap: '0.35rem' }}>
                                                                                            <button
                                                                                                onClick={() => toggleDrilldown(item.indicator_uuid)}
                                                                                                title="Onderliggende buurten tonen/verbergen"
                                                                                                aria-expanded={isDrilldownOpen}
                                                                                                style={{
                                                                                                    padding: '0.35rem 0.55rem',
                                                                                                    fontSize: '0.75rem',
                                                                                                    border: '1px solid var(--color-border)',
                                                                                                    borderRadius: 'var(--radius-sm)',
                                                                                                    background: isDrilldownOpen ? 'var(--color-primary)' : 'var(--color-surface)',
                                                                                                    color: isDrilldownOpen ? 'white' : 'var(--color-text-primary)',
                                                                                                    cursor: 'pointer',
                                                                                                    fontWeight: 600
                                                                                                }}
                                                                                            >
                                                                                                {isDrilldownOpen ? '−' : '+'} Buurten
                                                                                            </button>
                                                                                            <button
                                                                                                onClick={() => toggleOntologie(item.indicator_uuid)}
                                                                                                title="Definitie en ontologische toelichting"
                                                                                                aria-label="Definitie en ontologische toelichting"
                                                                                                aria-expanded={isOntologieOpen}
                                                                                                style={{
                                                                                                    padding: '0.35rem 0.55rem',
                                                                                                    fontSize: '0.75rem',
                                                                                                    border: '1px solid var(--color-border)',
                                                                                                    borderRadius: 'var(--radius-sm)',
                                                                                                    background: isOntologieOpen ? '#3B82F6' : 'var(--color-surface)',
                                                                                                    color: isOntologieOpen ? 'white' : 'var(--color-text-primary)',
                                                                                                    cursor: 'pointer'
                                                                                                }}
                                                                                            >
                                                                                                <Info size={13} />
                                                                                            </button>
                                                                                        </div>
                                                                                    </td>
                                                                                </tr>

                                                                                {/* Inline Ontologie Row */}
                                                                                {isOntologieOpen && (
                                                                                    <tr style={{ background: 'rgba(59, 130, 246, 0.04)' }}>
                                                                                        <td colSpan={6} style={{ padding: '1rem 1.25rem', borderBottom: '1px solid var(--color-border)' }}>
                                                                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem' }}>
                                                                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#2563eb', fontWeight: 600 }}>
                                                                                                    <Info size={15} /> Definitie & Ontologische Toelichting
                                                                                                </div>
                                                                                                {item.omschrijving && (
                                                                                                    <div>
                                                                                                        <strong style={{ color: 'var(--color-text-primary)' }}>CBS Definitie:</strong>{' '}
                                                                                                        <span style={{ color: 'var(--color-text-secondary)', whiteSpace: 'pre-line' }}>{item.omschrijving}</span>
                                                                                                    </div>
                                                                                                )}
                                                                                                {item.ontologische_beschrijving && (
                                                                                                    <div style={{ marginTop: '0.35rem' }}>
                                                                                                        <strong style={{ color: 'var(--color-text-primary)' }}>Betekenis & Beleidsduiding:</strong>{' '}
                                                                                                        <span style={{ color: 'var(--color-text-secondary)' }}>{item.ontologische_beschrijving}</span>
                                                                                                    </div>
                                                                                                )}
                                                                                                <div style={{ fontSize: '0.775rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                                                                                                    Bron: {item.bron || 'CBS/RIVM'} • Scoringstype: <code>{item.score_type}</code>
                                                                                                </div>
                                                                                            </div>
                                                                                        </td>
                                                                                    </tr>
                                                                                )}

                                                                                {/* Inline Buurten Drilldown Row */}
                                                                                {isDrilldownOpen && (
                                                                                    <tr style={{ background: 'var(--color-bg-alt)' }}>
                                                                                        <td colSpan={6} style={{ padding: '1rem 1.25rem', borderBottom: '1px solid var(--color-border)' }}>
                                                                                            <div style={{ marginBottom: '0.5rem', fontWeight: 600, fontSize: '0.825rem', color: 'var(--color-text-secondary)' }}>
                                                                                                Uitsplitsing onderliggende buurten binnen {deelgebied_naam} (gesorteerd op afwijking):
                                                                                            </div>
                                                                                            <div style={{ overflowX: 'auto', background: 'var(--color-surface)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}>
                                                                                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                                                                                    <thead>
                                                                                                        <tr style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)' }}>
                                                                                                            <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>Buurtnaam</th>
                                                                                                            <th style={{ padding: '0.5rem 0.75rem', textAlign: 'right' }}>Inwoners</th>
                                                                                                            <th style={{ padding: '0.5rem 0.75rem', textAlign: 'right' }}>Waarde</th>
                                                                                                            <th style={{ padding: '0.5rem 0.75rem', textAlign: 'right' }}>Buurt Z-Score</th>
                                                                                                            <th style={{ padding: '0.5rem 0.75rem', textAlign: 'right' }}>Verschil met Ref</th>
                                                                                                        </tr>
                                                                                                    </thead>
                                                                                                    <tbody>
                                                                                                        {item.buurten_drilldown.map(b => (
                                                                                                            <tr key={b.buurt_id} style={{ borderBottom: '1px solid var(--color-border-subtle, rgba(0,0,0,0.05))' }}>
                                                                                                                <td style={{ padding: '0.45rem 0.75rem', fontWeight: 500 }}>{b.buurt_naam}</td>
                                                                                                                <td style={{ padding: '0.45rem 0.75rem', textAlign: 'right', color: 'var(--color-text-muted)' }}>
                                                                                                                    {b.inwoners > 0 ? b.inwoners.toLocaleString('nl-NL') : 'Fallback (1)'}
                                                                                                                </td>
                                                                                                                <td style={{ padding: '0.45rem 0.75rem', textAlign: 'right', fontWeight: 600 }}>
                                                                                                                    {b.waarde.toLocaleString('nl-NL')} {item.eenheid}
                                                                                                                </td>
                                                                                                                <td style={{ padding: '0.45rem 0.75rem', textAlign: 'right' }}>
                                                                                                                    <span style={{
                                                                                                                        fontWeight: 600,
                                                                                                                        color: Math.abs(b.buurt_z_score) >= 1.0 ? (b.buurt_z_score > 0 ? '#2563eb' : '#dc2626') : 'inherit'
                                                                                                                    }}>
                                                                                                                        {b.buurt_z_score > 0 ? '+' : ''}{b.buurt_z_score.toFixed(2)}
                                                                                                                    </span>
                                                                                                                </td>
                                                                                                                <td style={{ padding: '0.45rem 0.75rem', textAlign: 'right', color: 'var(--color-text-secondary)' }}>
                                                                                                                    {b.verschil > 0 ? '+' : ''}{b.verschil.toFixed(1)} {item.eenheid} ({b.verschil_pct > 0 ? '+' : ''}{b.verschil_pct.toFixed(1)}%)
                                                                                                                </td>
                                                                                                            </tr>
                                                                                                        ))}
                                                                                                    </tbody>
                                                                                                </table>
                                                                                            </div>
                                                                                        </td>
                                                                                    </tr>
                                                                                )}
                                                                            </React.Fragment>
                                                                        );
                                                                    })}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    );
                })}
            </section>

            {/* ─── SECTIE 3: METHODOLOGISCHE VERANTWOORDING ────────────────────── */}
            <section style={{ marginBottom: '3rem' }}>
                <div
                    onClick={() => setIsMethodologieOpen(!isMethodologieOpen)}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '1.25rem 1.5rem',
                        background: 'var(--color-surface)',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--color-border)',
                        cursor: 'pointer',
                        boxShadow: 'var(--shadow-sm)'
                    }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <HelpCircle size={20} color="var(--color-primary)" />
                        <div>
                            <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600 }}>
                                Methodologische Verantwoording & Berekeningswijze
                            </h2>
                            <p style={{ margin: '0.2rem 0 0', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                                Transparante toelichting op de berekening van gewogen gemiddelden, Z-scores en scoringstypen
                            </p>
                        </div>
                    </div>
                    {isMethodologieOpen ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                </div>

                {isMethodologieOpen && (
                    <div style={{
                        marginTop: '0.75rem',
                        padding: '1.75rem',
                        background: 'var(--color-surface)',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--color-border)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '1.5rem'
                    }}>
                        {/* Validatie Disclaimer Alert */}
                        <div style={{
                            display: 'flex',
                            gap: '0.75rem',
                            padding: '1rem 1.25rem',
                            borderRadius: 'var(--radius-md)',
                            background: 'rgba(245, 158, 11, 0.1)',
                            border: '1px solid rgba(245, 158, 11, 0.3)',
                            color: '#b45309'
                        }}>
                            <AlertTriangle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
                            <div style={{ fontSize: '0.875rem', lineHeight: 1.5 }}>
                                <strong>Belangrijke methodologische kanttekening (Validatie):</strong>{' '}
                                {methodologie.scoringtype_disclaimer}
                            </div>
                        </div>

                        {/* Rekenstappen Matrix */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.25rem' }}>
                            <div style={{ padding: '1rem', background: 'var(--color-bg-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                                <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.925rem', fontWeight: 600, color: 'var(--color-primary)' }}>
                                    1. Herkomst Ruwe Data
                                </h4>
                                <p style={{ margin: 0, fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                                    De analyse gebruikt de meest recente eenheidswaarden per individuele buurt uit CBS Kerncijfers Wijken en Buurten, RIVM Gezondheidsmonitor en aanvullende databronnen.
                                </p>
                            </div>

                            <div style={{ padding: '1rem', background: 'var(--color-bg-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                                <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.925rem', fontWeight: 600, color: 'var(--color-primary)' }}>
                                    2. Gewogen Gemiddelde (Stadsscore)
                                </h4>
                                <p style={{ margin: '0 0 0.5rem', fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                                    Om een evenwichtig beeld voor de gehele woonplaats te krijgen, worden buurten gewogen naar inwoneraantal:
                                </p>
                                <code style={{ display: 'block', padding: '0.4rem', background: 'var(--color-surface)', borderRadius: '4px', fontSize: '0.8rem' }}>
                                    W = Σ(waarde_i × inw_i) / Σ(inw_i)
                                </code>
                            </div>

                            <div style={{ padding: '1rem', background: 'var(--color-bg-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                                <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.925rem', fontWeight: 600, color: 'var(--color-primary)' }}>
                                    3. Z-score Standaardisering
                                </h4>
                                <p style={{ margin: '0 0 0.5rem', fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                                    Het gewogen gemiddelde wordt genormaliseerd t.o.v. de referentiegroep (alle buurten in {referentie_label}):
                                </p>
                                <code style={{ display: 'block', padding: '0.4rem', background: 'var(--color-surface)', borderRadius: '4px', fontSize: '0.8rem' }}>
                                    {methodologie.z_score_formule}
                                </code>
                            </div>

                            <div style={{ padding: '1rem', background: 'var(--color-bg-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
                                <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.925rem', fontWeight: 600, color: 'var(--color-primary)' }}>
                                    4. Interpretatie Stadsgemiddelde
                                </h4>
                                <p style={{ margin: 0, fontSize: '0.825rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                                    {methodologie.statistisch_effect}
                                </p>
                            </div>
                        </div>

                        {/* Buurten & Gewicht Transparantie */}
                        <div>
                            <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.95rem', fontWeight: 600 }}>
                                Buurtgewichten & Inwonersverantwoording ({data.geselecteerde_buurten.length} buurten)
                            </h4>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', maxHeight: '140px', overflowY: 'auto', padding: '0.5rem', background: 'var(--color-bg-alt)', borderRadius: 'var(--radius-md)' }}>
                                {data.geselecteerde_buurten.map(b => (
                                    <span
                                        key={b.id}
                                        style={{
                                            fontSize: '0.75rem',
                                            padding: '0.25rem 0.5rem',
                                            borderRadius: '4px',
                                            background: b.is_fallback ? 'rgba(239, 68, 68, 0.1)' : 'var(--color-surface)',
                                            border: '1px solid var(--color-border)',
                                            color: b.is_fallback ? '#dc2626' : 'var(--color-text-secondary)'
                                        }}
                                        title={b.is_fallback ? 'Geen inwonersdata gevonden: ongewogen meegenomen (gewicht 1)' : `${b.inwoners.toLocaleString('nl-NL')} inwoners`}
                                    >
                                        {b.naam}: <strong>{b.inwoners > 0 ? b.inwoners.toLocaleString('nl-NL') : 'ongewogen (1)'}</strong>
                                    </span>
                                ))}
                            </div>
                            {methodologie.fallback_buurten?.length > 0 && (
                                <p style={{ fontSize: '0.775rem', color: '#b45309', margin: '0.4rem 0 0' }}>
                                    ⚠️ {methodologie.fallback_buurten.length} buurt(en) hadden geen inwonersregistratie in de CBS Kerncijfers en zijn met gewicht 1 meegenomen.
                                </p>
                            )}
                        </div>

                        {/* Bronverantwoording Toggle / Lijst */}
                        <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '1rem' }}>
                            <div
                                onClick={() => setIsBronverantwoordingOpen(!isBronverantwoordingOpen)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    cursor: 'pointer',
                                    padding: '0.5rem 0'
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, fontSize: '0.9rem' }}>
                                    <FileText size={16} /> Volledige Bronverantwoording & Peildata ({bronverantwoording?.length || 0} bronnen)
                                </div>
                                {isBronverantwoordingOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                            </div>

                            {isBronverantwoordingOpen && (
                                <div style={{ marginTop: '0.75rem', overflowX: 'auto' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                                        <thead>
                                            <tr style={{ borderBottom: '1px solid var(--color-border)', color: 'var(--color-text-muted)' }}>
                                                <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>Indicator</th>
                                                <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>Bronorganisatie</th>
                                                <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>Dataset / API Referentie</th>
                                                <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left' }}>Peildatum</th>
                                                <th style={{ padding: '0.5rem 0.75rem', textAlign: 'center' }}>Link</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {bronverantwoording.map(b => (
                                                <tr key={b.indicator_uuid} style={{ borderBottom: '1px solid var(--color-border-subtle, rgba(0,0,0,0.05))' }}>
                                                    <td style={{ padding: '0.45rem 0.75rem', fontWeight: 500 }}>{b.indicator_naam}</td>
                                                    <td style={{ padding: '0.45rem 0.75rem', color: 'var(--color-text-secondary)' }}>{b.bron}</td>
                                                    <td style={{ padding: '0.45rem 0.75rem', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                                                        {b.bron_tabel_referentie || b.bron_systeem_api || '—'}
                                                    </td>
                                                    <td style={{ padding: '0.45rem 0.75rem', color: 'var(--color-text-secondary)' }}>{b.peildata || 'Recentste'}</td>
                                                    <td style={{ padding: '0.45rem 0.75rem', textAlign: 'center' }}>
                                                        {b.bron_url ? (
                                                            <a href={b.bron_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-primary)' }}>
                                                                <ExternalLink size={13} />
                                                            </a>
                                                        ) : '—'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </section>
        </div>
    );
};
export default DeelgebiedPage;
