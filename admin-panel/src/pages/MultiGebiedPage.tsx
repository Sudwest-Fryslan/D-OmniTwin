import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { reportAPI } from '../services/api';
import { X, Layers, RefreshCw, Download, ArrowUpDown } from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────────────────────

interface BuurtAnalyse {
    buurt_id: string;
    buurt_naam: string;
    max_z_score: number;
    max_z_score_abs: number;
    indicator_naam: string;
    eenheid: string;
    thema: string;
    score_type: string;
    impact: string;
    kleur_hex: string;
    waarde: number;
    ref_gemiddelde: number;
    ref_min: number;
    ref_max: number;
}

interface ThemaAggregaat {
    gem_zscore: number;
    n_uitschieters: number;
    n_datapunten: number;
}

interface MultiGebiedData {
    deelgebied_naam: string;
    referentie_label: string;
    referentie_modus: string;
    totaal_buurten: number;
    buurten_met_data: number;
    buurten_analyse: BuurtAnalyse[];
    thema_aggregaat: Record<string, ThemaAggregaat>;
    top_uitschieters: BuurtAnalyse[];
}

interface GeoJSONFeature {
    type: 'Feature';
    geometry: any;
    properties: {
        buurt_id: string;
        buurt_naam: string;
        max_z_score: number;
        max_z_score_abs: number;
        indicator_naam: string;
        thema: string;
        impact: string;
        kleur_hex: string;
    };
}

interface GeoJSONCollection {
    type: 'FeatureCollection';
    metadata: { referentie_label: string; totaal_buurten: number };
    features: GeoJSONFeature[];
}

// ─── Component ─────────────────────────────────────────────────────────────

export const MultiGebiedPage: React.FC = () => {
    const [searchParams] = useSearchParams();

    // State
    const [referentie, setReferentie] = useState<'gemeente' | 'fryslan'>(
        (searchParams.get('ref') as 'gemeente' | 'fryslan') || 'gemeente'
    );
    const [data, setData] = useState<MultiGebiedData | null>(null);
    const [geoData, setGeoData] = useState<GeoJSONCollection | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [sortField, setSortField] = useState<'z_score' | 'buurt' | 'thema'>('z_score');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
    const [hoveredBuurt, setHoveredBuurt] = useState<string | null>(null);

    const svgRef = useRef<SVGSVGElement>(null);

    const gebiedIds = searchParams.get('gebieden')?.split(',').filter(Boolean) || [];
    const deelgebiedNaam = searchParams.get('naam') || `${gebiedIds.length} buurten`;
    const gemeenteCode = searchParams.get('gemeente') || '1900';

    // ─── Data Fetching ──────────────────────────────────────────────────────

    const fetchData = async (ref: string) => {
        if (gebiedIds.length === 0) return;
        setLoading(true);
        setError(null);

        const payload = {
            gebied_ids: gebiedIds,
            referentie: ref,
            gemeente_code: gemeenteCode,
            deelgebied_naam: deelgebiedNaam
        };

        try {
            const [dataRes, geoRes] = await Promise.all([
                reportAPI.getMultiGebied(payload),
                reportAPI.getMultiGebiedGeoJSON(payload)
            ]);
            setData(dataRes.data);
            setGeoData(geoRes.data);
        } catch (err: any) {
            setError(err?.response?.data?.detail || err.message || 'Fout bij laden data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData(referentie);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const handleReferentieSwitch = (newRef: 'gemeente' | 'fryslan') => {
        setReferentie(newRef);
        fetchData(newRef);
    };

    // ─── Sorting ────────────────────────────────────────────────────────────

    const sortedBuurten = data ? [...data.buurten_analyse].sort((a, b) => {
        let cmp = 0;
        if (sortField === 'z_score') cmp = a.max_z_score_abs - b.max_z_score_abs;
        else if (sortField === 'buurt') cmp = a.buurt_naam.localeCompare(b.buurt_naam);
        else if (sortField === 'thema') cmp = a.thema.localeCompare(b.thema);
        return sortDir === 'desc' ? -cmp : cmp;
    }) : [];

    const toggleSort = (field: 'z_score' | 'buurt' | 'thema') => {
        if (sortField === field) {
            setSortDir(d => d === 'desc' ? 'asc' : 'desc');
        } else {
            setSortField(field);
            setSortDir('desc');
        }
    };

    // ─── CSV Export ─────────────────────────────────────────────────────────

    const exportCSV = () => {
        if (!data) return;
        const header = 'Rang,Buurt,Buurt ID,Thema,Indicator,Waarde,Eenheid,Bereik (min-max),Gemiddelde,Z-score,Impact\n';
        const rows = sortedBuurten.map((b, i) =>
            `${i + 1},"${b.buurt_naam}",${b.buurt_id},"${b.thema}","${b.indicator_naam}",${b.waarde},"${b.eenheid}","${b.ref_min}–${b.ref_max}",${b.ref_gemiddelde},${b.max_z_score},"${b.impact}"`
        ).join('\n');
        const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
        a.download = `multi-gebiedsdossier_${deelgebiedNaam.replace(/\s+/g, '_')}_${dateStr}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    // ─── Print ──────────────────────────────────────────────────────────────

    const handlePrint = () => {
        const originalTitle = document.title;
        const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
        document.title = `MultiGebied_${deelgebiedNaam.replace(/\s+/g, '_')}_${dateStr}`;
        const afterPrint = () => { document.title = originalTitle; window.removeEventListener('afterprint', afterPrint); };
        window.addEventListener('afterprint', afterPrint);
        setTimeout(() => window.print(), 100);
    };

    // ─── SVG Choropleth ─────────────────────────────────────────────────────

    const renderChoropleth = () => {
        if (!geoData || geoData.features.length === 0) return null;

        // Calculate bounds
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        geoData.features.forEach(f => {
            const coords = f.geometry.type === 'MultiPolygon'
                ? f.geometry.coordinates.flat(2)
                : f.geometry.coordinates.flat(1);
            coords.forEach((c: number[]) => {
                if (c[0] < minX) minX = c[0];
                if (c[0] > maxX) maxX = c[0];
                if (c[1] < minY) minY = c[1];
                if (c[1] > maxY) maxY = c[1];
            });
        });

        const padding = 20;
        const width = 500;
        const height = 400;
        const dataWidth = maxX - minX;
        const dataHeight = maxY - minY;
        const scale = Math.min(
            (width - 2 * padding) / dataWidth,
            (height - 2 * padding) / dataHeight
        );

        const projectX = (lon: number) => padding + (lon - minX) * scale;
        const projectY = (lat: number) => height - padding - (lat - minY) * scale;

        const toPath = (coords: number[][]) =>
            coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${projectX(c[0]).toFixed(1)},${projectY(c[1]).toFixed(1)}`).join('') + 'Z';

        return (
            <svg ref={svgRef} viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', maxHeight: '400px' }}>
                {geoData.features.map(f => {
                    const isHovered = hoveredBuurt === f.properties.buurt_id;
                    const polygons = f.geometry.type === 'MultiPolygon'
                        ? f.geometry.coordinates.map((poly: number[][][]) => poly[0])
                        : [f.geometry.coordinates[0]];

                    return (
                        <g key={f.properties.buurt_id}>
                            {polygons.map((ring: number[][], ri: number) => (
                                <path
                                    key={ri}
                                    d={toPath(ring)}
                                    fill={f.properties.kleur_hex}
                                    stroke={isHovered ? '#fff' : '#334155'}
                                    strokeWidth={isHovered ? 2 : 0.5}
                                    opacity={isHovered ? 1 : 0.85}
                                    style={{ cursor: 'pointer', transition: 'opacity 0.15s' }}
                                    onMouseEnter={() => setHoveredBuurt(f.properties.buurt_id)}
                                    onMouseLeave={() => setHoveredBuurt(null)}
                                >
                                    <title>{`${f.properties.buurt_naam}\n${f.properties.indicator_naam}: z=${f.properties.max_z_score}\n${f.properties.impact}`}</title>
                                </path>
                            ))}
                        </g>
                    );
                })}
            </svg>
        );
    };

    // ─── Thema Bars ─────────────────────────────────────────────────────────

    const renderThemaBars = () => {
        if (!data) return null;
        const entries = Object.entries(data.thema_aggregaat)
            .sort((a, b) => Math.abs(b[1].gem_zscore) - Math.abs(a[1].gem_zscore));
        const maxZ = Math.max(...entries.map(([, v]) => Math.abs(v.gem_zscore)), 0.1);

        return (
            <div>
                {entries.map(([thema, agg]) => {
                    const pct = Math.min((Math.abs(agg.gem_zscore) / maxZ) * 100, 100);
                    const isNeg = agg.gem_zscore < 0;
                    const barColor = Math.abs(agg.gem_zscore) >= 1.0
                        ? '#2b6ca3'
                        : '#8c96a0';

                    return (
                        <div key={thema} style={{ marginBottom: '0.75rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                                <span style={{ fontWeight: 500 }}>{thema}</span>
                                <span style={{ color: 'var(--color-text-muted)', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                                    z̄={agg.gem_zscore > 0 ? '+' : ''}{agg.gem_zscore} · {agg.n_uitschieters} uitschieter{agg.n_uitschieters !== 1 ? 's' : ''}
                                </span>
                            </div>
                            <div style={{ background: 'var(--color-bg-alt)', borderRadius: '4px', height: '10px', overflow: 'hidden' }}>
                                <div style={{
                                    width: `${pct}%`, height: '100%',
                                    background: barColor, borderRadius: '4px',
                                    transition: 'width 0.4s ease'
                                }} />
                            </div>
                        </div>
                    );
                })}
            </div>
        );
    };

    // ─── Legenda ─────────────────────────────────────────────────────────────

    const legendItems = [
        { color: '#8c96a0', label: 'In lijn (|z| < 0.5)' },
        { color: '#d4b483', label: 'Licht afwijkend (0.5–1.0)' },
        { color: '#c17c3e', label: 'Matig afwijkend (1.0–1.5)' },
        { color: '#2b6ca3', label: 'Sterk afwijkend (1.5–2.0)' },
        { color: '#1a3d5c', label: 'Extreem afwijkend (> 2.0)' },
    ];

    // ─── RENDER ─────────────────────────────────────────────────────────────

    if (gebiedIds.length === 0) {
        return (
            <div className="page-container">
                <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
                    <Layers size={48} style={{ color: 'var(--color-text-muted)', marginBottom: '1rem' }} />
                    <h2>Geen gebieden geselecteerd</h2>
                    <p className="text-secondary">
                        Selecteer een omgevingsvisie-deelgebied op de kaart om een Multi-Gebiedsdossier te genereren.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="page-container">
            {/* Header */}
            <div className="page-header hide-on-print">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <button className="btn btn-secondary" onClick={() => window.close()}
                            style={{ padding: '0.25rem 0.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <X size={16} /> Sluit rapport
                        </button>
                        <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <Layers size={24} /> Multi-Gebiedsdossier
                        </h1>
                        <p className="text-secondary">
                            Z-score afwijkingsanalyse voor {deelgebiedNaam} ({gebiedIds.length} buurten)
                        </p>
                    </div>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        {data && (
                            <>
                                <button className="btn btn-secondary" onClick={exportCSV}>
                                    <Download size={16} style={{ marginRight: '0.5rem' }} />
                                    CSV
                                </button>
                                <button className="btn btn-primary" onClick={handlePrint}>
                                    Exporteer PDF
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Referentie Toggle */}
            <div className="card hide-on-print" style={{ marginBottom: '1.5rem', padding: '1rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Referentiekader:</span>
                <div style={{ display: 'flex', gap: '0' }}>
                    {([
                        { key: 'gemeente' as const, label: '⌀ Gemeente SWF' },
                        { key: 'fryslan' as const, label: '⌀ Provincie Fryslân' },
                    ]).map(tab => (
                        <button
                            key={tab.key}
                            onClick={() => handleReferentieSwitch(tab.key)}
                            disabled={loading}
                            style={{
                                padding: '0.5rem 1.25rem',
                                border: '1px solid var(--color-border)',
                                background: referentie === tab.key ? 'var(--color-primary)' : 'var(--color-surface)',
                                color: referentie === tab.key ? 'white' : 'var(--color-text)',
                                cursor: loading ? 'wait' : 'pointer',
                                fontSize: '0.85rem',
                                fontWeight: referentie === tab.key ? 600 : 400,
                                borderRadius: tab.key === 'gemeente' ? 'var(--radius-sm) 0 0 var(--radius-sm)' : '0 var(--radius-sm) var(--radius-sm) 0',
                            }}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
                {data && (
                    <span style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem', marginLeft: 'auto' }}>
                        {data.buurten_met_data} van {data.totaal_buurten} buurten met data
                    </span>
                )}
            </div>

            {/* Loading / Error */}
            {loading && (
                <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
                    <RefreshCw className="spin text-primary" size={32} />
                    <p style={{ marginTop: '1rem' }}>Z-scores berekenen voor {gebiedIds.length} buurten...</p>
                </div>
            )}

            {error && (
                <div className="card" style={{ padding: '1rem', borderLeft: '4px solid var(--color-danger, #ef4444)', marginBottom: '1.5rem' }}>
                    <strong>Fout:</strong> {error}
                </div>
            )}

            {/* Results */}
            {data && !loading && (
                <>
                    {/* Print Header (only visible during print) */}
                    <div className="show-on-print" style={{ display: 'none', marginBottom: '1.5rem' }}>
                        <h1 style={{ margin: 0 }}>Multi-Gebiedsdossier: {data.deelgebied_naam}</h1>
                        <p style={{ margin: '0.25rem 0', color: '#666' }}>
                            Referentie: {data.referentie_label} · {data.buurten_met_data} buurten · {new Date().toLocaleDateString('nl-NL')}
                        </p>
                    </div>

                    {/* Kaart + Thema grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>

                        {/* Choropleth Kaart */}
                        <div className="card" style={{ padding: '1.25rem' }}>
                            <h3 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary)' }}>
                                🗺️ Z-score Afwijkingskaart
                            </h3>
                            {renderChoropleth()}
                            {/* Legenda */}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginTop: '1rem', fontSize: '0.75rem' }}>
                                {legendItems.map(l => (
                                    <div key={l.color} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                        <div style={{ width: '12px', height: '12px', borderRadius: '2px', background: l.color }} />
                                        <span style={{ color: 'var(--color-text-muted)' }}>{l.label}</span>
                                    </div>
                                ))}
                            </div>
                            {/* Hover info — fixed height zodat layout niet verspringt */}
                            <div style={{
                                marginTop: '0.75rem', minHeight: '56px',
                                transition: 'opacity 0.15s',
                                opacity: hoveredBuurt ? 1 : 0,
                                pointerEvents: 'none'
                            }}>
                                {(() => {
                                    const b = hoveredBuurt ? data?.buurten_analyse.find(x => x.buurt_id === hoveredBuurt) : null;
                                    if (!b) return <div style={{ padding: '0.75rem', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Beweeg muis over een buurt</div>;
                                    return (
                                        <div style={{
                                            padding: '0.75rem',
                                            background: 'var(--color-bg-alt)', borderRadius: 'var(--radius-sm)',
                                            fontSize: '0.85rem', borderLeft: `3px solid ${b.kleur_hex}`
                                        }}>
                                            <strong>{b.buurt_naam}</strong> — {b.indicator_naam}
                                            <br />
                                            <span style={{ color: 'var(--color-text-muted)' }}>
                                                Waarde: {b.waarde} {b.eenheid} · z={b.max_z_score > 0 ? '+' : ''}{b.max_z_score} · bereik: {b.ref_min}–{b.ref_max}
                                            </span>
                                        </div>
                                    );
                                })()}
                            </div>
                        </div>

                        {/* Thema Aggregaat */}
                        <div className="card" style={{ padding: '1.25rem' }}>
                            <h3 style={{ margin: '0 0 1rem', color: 'var(--color-primary)' }}>
                                📊 Thema Aggregaat
                            </h3>
                            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
                                Gemiddelde z-score per thema over alle {data.buurten_met_data} buurten
                            </p>
                            {renderThemaBars()}
                        </div>
                    </div>

                    {/* Uitschietertabel */}
                    <div className="card" style={{ marginBottom: '1.5rem' }}>
                        <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <h3 style={{ margin: 0, color: 'var(--color-primary)' }}>
                                📋 Uitschietertabel — Ranking per buurt
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
                                    <th style={{ textAlign: 'left', padding: '0.75rem 1rem', cursor: 'pointer' }}
                                        onClick={() => toggleSort('buurt')}>
                                        Buurt <ArrowUpDown size={12} style={{ opacity: sortField === 'buurt' ? 1 : 0.3 }} />
                                    </th>
                                    <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem', cursor: 'pointer' }}
                                        onClick={() => toggleSort('thema')}>
                                        Thema <ArrowUpDown size={12} style={{ opacity: sortField === 'thema' ? 1 : 0.3 }} />
                                    </th>
                                    <th style={{ textAlign: 'left', padding: '0.75rem 0.5rem' }}>Indicator</th>
                                    <th style={{ textAlign: 'right', padding: '0.75rem 0.5rem' }}>Waarde</th>
                                    <th style={{ textAlign: 'center', padding: '0.75rem 0.5rem' }}>Bereik (min–max)</th>
                                    <th style={{ textAlign: 'right', padding: '0.75rem 0.5rem', cursor: 'pointer' }}
                                        onClick={() => toggleSort('z_score')}>
                                        Z-score <ArrowUpDown size={12} style={{ opacity: sortField === 'z_score' ? 1 : 0.3 }} />
                                    </th>
                                    <th style={{ textAlign: 'center', padding: '0.75rem 1rem' }}>Impact</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortedBuurten.map((b, i) => (
                                    <tr key={b.buurt_id}
                                        style={{ background: hoveredBuurt === b.buurt_id ? 'var(--color-bg-alt)' : 'transparent' }}
                                        onMouseEnter={() => setHoveredBuurt(b.buurt_id)}
                                        onMouseLeave={() => setHoveredBuurt(null)}>
                                        <td style={{ textAlign: 'center', padding: '0.6rem 0.5rem', color: 'var(--color-text-muted)' }}>{i + 1}</td>
                                        <td style={{ padding: '0.6rem 1rem' }}>
                                            <strong>{b.buurt_naam}</strong>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>{b.buurt_id}</div>
                                        </td>
                                        <td style={{ padding: '0.6rem 0.5rem', fontSize: '0.85rem' }}>{b.thema}</td>
                                        <td style={{ padding: '0.6rem 0.5rem', fontSize: '0.85rem' }}>{b.indicator_naam}</td>
                                        <td style={{ textAlign: 'right', padding: '0.6rem 0.5rem', fontWeight: 600 }}>
                                            {b.waarde} <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>{b.eenheid}</span>
                                        </td>
                                        <td style={{ textAlign: 'center', padding: '0.6rem 0.5rem', fontSize: '0.8rem', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>
                                            {b.ref_min}–{b.ref_max}
                                        </td>
                                        <td style={{
                                            textAlign: 'right', padding: '0.6rem 0.5rem', fontWeight: 700, fontFamily: 'monospace',
                                            color: b.max_z_score_abs >= 2.0 ? '#1a3d5c' :
                                                b.max_z_score_abs >= 1.5 ? '#2b6ca3' :
                                                    b.max_z_score_abs >= 1.0 ? '#c17c3e' :
                                                        b.max_z_score_abs >= 0.5 ? '#d4b483' : '#8c96a0'
                                        }}>
                                            {b.max_z_score > 0 ? '+' : ''}{b.max_z_score}
                                        </td>
                                        <td style={{ textAlign: 'center', padding: '0.6rem 1rem' }}>
                                            <span style={{
                                                display: 'inline-block', width: '12px', height: '12px',
                                                borderRadius: '50%', background: b.kleur_hex
                                            }} title={b.impact} />
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    );
};
