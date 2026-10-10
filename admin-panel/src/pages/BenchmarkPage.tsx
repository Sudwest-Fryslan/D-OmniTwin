import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { reportAPI, gebiedenAPI } from '../services/api';
import type { BenchmarkMode, BenchmarkPayload, BenchmarkNarrativeResponse, GebiedListItem } from '../types';
import { AILabel } from '../components/AILabel';
import { ArrowLeft, Cpu, RefreshCw, Plus, X, Scale, BarChart3, Terminal, ChevronDown, ChevronUp } from 'lucide-react';

export const BenchmarkPage: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    // ─── Selectie State ─────────────────────────────────────────────────────
    const [mode, setMode] = useState<BenchmarkMode>('gebieden');
    const [gebiedA, setGebiedA] = useState<string>('');
    const [gebiedASearch, setGebiedASearch] = useState('');
    const [gebiedenB, setGebiedenB] = useState<string[]>(['']);
    const [gebiedenBSearch, setGebiedenBSearch] = useState<string[]>(['']);
    const [referentieGemeente, setReferentieGemeente] = useState<string>('');

    // ─── Data State ─────────────────────────────────────────────────────────
    const [benchmarkData, setBenchmarkData] = useState<BenchmarkPayload | null>(null);
    const [dataLoading, setDataLoading] = useState(false);
    const [dataError, setDataError] = useState<string | null>(null);

    // ─── AI State ───────────────────────────────────────────────────────────
    const [aiResponse, setAiResponse] = useState<BenchmarkNarrativeResponse | null>(null);
    const [aiLoading, setAiLoading] = useState(false);
    const [aiError, setAiError] = useState<string | null>(null);
    const [showDebugLogs, setShowDebugLogs] = useState(false);

    // ─── Live Search State ──────────────────────────────────────────────────
    const [suggestions, setSuggestions] = useState<GebiedListItem[]>([]);
    const [gemeenten, setGemeenten] = useState<{ code: string; naam: string }[]>([]);
    const [gebiedenLoading, setGebiedenLoading] = useState(false); // eslint-disable-line @typescript-eslint/no-unused-vars
    const searchTimerRef = useRef<NodeJS.Timeout | null>(null);

    // ─── Auto typing state (multiple dropdowns) ─────────────────────────────
    const [focusedField, setFocusedField] = useState<string | null>(null);

    // Debounced live search
    const searchGebieden = useCallback((q: string) => {
        if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
        if (q.length < 2) { setSuggestions([]); return; }
        searchTimerRef.current = setTimeout(async () => {
            try {
                const res = await gebiedenAPI.zoekGebieden(q);
                setSuggestions(res.data.gebieden || []);
            } catch (err) {
                console.error('Zoek fout:', err);
                setSuggestions([]);
            }
        }, 300);
    }, []);

    // Filter suggestions op basis van huidige zoekterm (client-side, vanuit suggestions)
    const filterGebieden = useCallback((search: string): GebiedListItem[] => {
        if (!search || search.length < 2) return [];
        const lower = search.toLowerCase();
        return suggestions
            .filter(g => g.naam.toLowerCase().includes(lower) || g.id.toLowerCase().includes(lower))
            .slice(0, 12);
    }, [suggestions]);

    // Laad gemeenten bij mount + URL pre-populatie
    useEffect(() => {
        // Laad gemeenten voor dropdown
        gebiedenAPI.getGemeenten()
            .then(res => setGemeenten(res.data.gemeenten || []))
            .catch(err => console.error('Fout bij laden gemeenten:', err));

        // URL pre-populatie: ?gebied_a=BU...&gebieden_b=BU...,BU...
        const aId = searchParams.get('gebied_a');
        const bIds = searchParams.get('gebieden_b')?.split(',').filter(Boolean) ?? [];

        if (aId) {
            setGebiedA(aId);
            // Zoek naam op via API voor weergave in zoekveld
            gebiedenAPI.zoekGebieden(aId).then(r => {
                const match = r.data.gebieden.find(g => g.id === aId);
                if (match) setGebiedASearch(match.naam);
            }).catch(() => setGebiedASearch(aId));
        }
        if (bIds.length > 0) {
            setGebiedenB(bIds);
            // Zoek namen op voor weergave
            Promise.all(bIds.map(id => gebiedenAPI.zoekGebieden(id))).then(results => {
                const namen = results.map((r, i) =>
                    r.data.gebieden.find(g => g.id === bIds[i])?.naam ?? bIds[i]
                );
                setGebiedenBSearch(namen);
            }).catch(() => setGebiedenBSearch(bIds));
        }
        if (bIds.length > 0 && aId) setMode('gebieden');
    }, []); // eslint-disable-line react-hooks/exhaustive-deps


    // ─── Handlers ───────────────────────────────────────────────────────────

    const addGebiedB = () => {
        if (gebiedenB.length < 5) {
            setGebiedenB([...gebiedenB, '']);
            setGebiedenBSearch([...gebiedenBSearch, '']);
        }
    };

    const removeGebiedB = (index: number) => {
        setGebiedenB(gebiedenB.filter((_, i) => i !== index));
        setGebiedenBSearch(gebiedenBSearch.filter((_, i) => i !== index));
    };

    const updateGebiedB = (index: number, value: string, label: string) => {
        const updated = [...gebiedenB];
        updated[index] = value;
        setGebiedenB(updated);
        const updatedSearch = [...gebiedenBSearch];
        updatedSearch[index] = label;
        setGebiedenBSearch(updatedSearch);
        setFocusedField(null);
    };

    const selectGebiedA = (id: string, naam: string) => {
        setGebiedA(id);
        setGebiedASearch(naam);
        setFocusedField(null);
    };

    const canLoadBenchmark = (): boolean => {
        if (!gebiedA) return false;
        if (mode === 'gebieden' && gebiedenB.filter(g => g).length === 0) return false;
        if (mode === 'gemeente' && !referentieGemeente) return false;
        return true;
    };

    const fetchBenchmark = async () => {
        if (!canLoadBenchmark()) return;
        setDataLoading(true);
        setDataError(null);
        setBenchmarkData(null);
        setAiResponse(null);
        try {
            const response = await reportAPI.getBenchmark({
                gebied_a: gebiedA,
                mode,
                gebieden_b: mode === 'gebieden' ? gebiedenB.filter(g => g) : undefined,
                referentie_gemeente: mode === 'gemeente' ? referentieGemeente : undefined,
            });
            setBenchmarkData(response.data);
        } catch (err: any) {
            setDataError(err?.response?.data?.detail || err.message || 'Fout bij laden benchmark data');
        } finally {
            setDataLoading(false);
        }
    };

    const fetchAINarrative = async () => {
        if (!canLoadBenchmark()) return;
        setAiLoading(true);
        setAiError(null);
        try {
            const response = await reportAPI.getBenchmarkNarrative({
                gebied_a: gebiedA,
                mode,
                gebieden_b: mode === 'gebieden' ? gebiedenB.filter(g => g) : undefined,
                referentie_gemeente: mode === 'gemeente' ? referentieGemeente : undefined,
            });
            setAiResponse(response.data);
        } catch (err: any) {
            setAiError(err?.response?.data?.detail || err.message || 'Fout bij genereren AI narrative');
        } finally {
            setAiLoading(false);
        }
    };

    const handlePrint = () => {
        const originalTitle = document.title;
        if (benchmarkData) {
            const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
            document.title = `Benchmark_${benchmarkData.gebied_a.naam}_vs_${benchmarkData.referentie_label}_${dateStr}`;
        }
        const afterPrint = () => { document.title = originalTitle; window.removeEventListener('afterprint', afterPrint); };
        window.addEventListener('afterprint', afterPrint);
        setTimeout(() => window.print(), 100);
    };

    // ─── Typeahead Dropdown Component ───────────────────────────────────────
    const TypeaheadSelector: React.FC<{
        value: string;
        searchValue: string;
        onSearchChange: (s: string) => void;
        onSelect: (id: string, naam: string) => void;
        placeholder: string;
        fieldId: string;
        ariaLabel?: string;
    }> = ({ value, searchValue, onSearchChange, onSelect, placeholder, fieldId, ariaLabel }) => {
        const suggestions = filterGebieden(searchValue);
        const isOpen = focusedField === fieldId && suggestions.length > 0;

        return (
            <div style={{ position: 'relative', flex: 1 }}>
                <input
                    id={`benchmark-${fieldId}`}
                    type="text"
                    className="form-input"
                    placeholder={placeholder}
                    aria-label={ariaLabel}
                    role="combobox"
                    aria-autocomplete="list"
                    aria-expanded={isOpen}
                    aria-controls={`benchmark-${fieldId}-lijst`}
                    value={searchValue}
                    onChange={(e) => { onSearchChange(e.target.value); searchGebieden(e.target.value); setFocusedField(fieldId); }}
                    onFocus={() => setFocusedField(fieldId)}
                    onBlur={() => setTimeout(() => setFocusedField(null), 200)}
                    style={{
                        width: '100%', padding: '0.6rem 0.75rem',
                        background: 'var(--color-bg-alt)', border: '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-sm)', color: 'var(--color-text)',
                        fontSize: '0.9rem'
                    }}
                />
                {value && (
                    <span style={{
                        position: 'absolute', right: '0.5rem', top: '50%', transform: 'translateY(-50%)',
                        fontSize: '0.7rem', color: 'var(--color-text-muted)', fontFamily: 'monospace'
                    }}>
                        {value}
                    </span>
                )}
                {isOpen && (
                    <div id={`benchmark-${fieldId}-lijst`} role="listbox" style={{
                        position: 'absolute', top: '100%', left: 0, right: 0,
                        background: 'var(--color-surface)', border: '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-sm)', maxHeight: '200px', overflowY: 'auto',
                        zIndex: 100, boxShadow: 'var(--shadow-md)'
                    }}>
                        {suggestions.map(g => (
                            <div
                                key={g.id}
                                role="option"
                                aria-selected={g.id === value}
                                onClick={() => onSelect(g.id, g.naam)}
                                style={{
                                    padding: '0.5rem 0.75rem', cursor: 'pointer',
                                    borderBottom: '1px solid var(--color-border)',
                                    fontSize: '0.85rem'
                                }}
                                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-bg-alt)')}
                                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                            >
                                <strong>{g.naam}</strong>
                                <span style={{ color: 'var(--color-text-muted)', marginLeft: '0.5rem', fontSize: '0.75rem' }}>{g.id}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    };

    // ─── Delta Bar Helper ───────────────────────────────────────────────────
    const DeltaBar: React.FC<{ delta: number; maxDelta: number; impact: string }> = ({ delta, maxDelta, impact }) => {
        const width = maxDelta > 0 ? Math.min(Math.abs(delta) / maxDelta * 100, 100) : 0;
        const isPositive = impact.includes('positief');
        const color = isPositive ? 'var(--color-success, #22c55e)' : 'var(--color-danger, #ef4444)';

        return (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', width: '150px' }}>
                <div style={{ flex: 1, background: 'var(--color-bg-alt)', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
                    <div style={{ width: `${width}%`, height: '100%', background: color, borderRadius: '4px', transition: 'width 0.3s ease' }} />
                </div>
            </div>
        );
    };

    // Bereken maxDelta voor schaling
    const maxDelta = benchmarkData ? Math.max(...benchmarkData.vergelijking.map(v => Math.abs(v.delta)), 1) : 1;

    // Groepeer per kwadrant
    const groupedByKwadrant = benchmarkData ? benchmarkData.vergelijking.reduce<Record<string, typeof benchmarkData.vergelijking>>((acc, item) => {
        const kw = item.kwadrant || 'Overig';
        if (!acc[kw]) acc[kw] = [];
        acc[kw].push(item);
        return acc;
    }, {}) : {};

    // ─── RENDER ─────────────────────────────────────────────────────────────

    return (
        <div className="page-container" style={{ maxWidth: '1400px', margin: '0 auto', padding: '2rem' }}>
            <div className="page-header hide-on-print">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <button className="btn btn-secondary" onClick={() => window.close()}
                            style={{ padding: '0.25rem 0.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <X size={16} /> Sluit rapport
                        </button>
                        <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <Scale size={24} /> Benchmark Vergelijker
                        </h1>
                        <p className="text-secondary">Vergelijk een gebied met andere gebieden, een gemeente of geheel Fryslân</p>
                    </div>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        {benchmarkData && (
                            <>
                                <button className="btn btn-secondary" onClick={fetchAINarrative} disabled={aiLoading}>
                                    <Cpu size={16} style={{ marginRight: '0.5rem' }} />
                                    {aiLoading ? 'AI Analyseren...' : 'Genereer AI Vergelijking'}
                                </button>
                                <button className="btn btn-primary" onClick={handlePrint}>
                                    Exporteer PDF
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* ─── Configuratie Paneel ─────────────────────────────────────── */}
            <div className="card hide-on-print" style={{ marginBottom: '1.5rem', padding: '1.5rem' }}>
                {/* Gebied A */}
                <div style={{ marginBottom: '1.25rem' }}>
                    <label htmlFor="benchmark-gebiedA" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block', color: 'var(--color-primary)' }}>
                        Gebied A (referentie)
                    </label>
                    <TypeaheadSelector
                        value={gebiedA}
                        searchValue={gebiedASearch}
                        onSearchChange={setGebiedASearch}
                        onSelect={selectGebiedA}
                        placeholder={gebiedenLoading ? 'Gebieden laden...' : 'Zoek op buurtnaam of code...'}
                        fieldId="gebiedA"
                    />
                </div>

                {/* Modus Tabs */}
                <div style={{ marginBottom: '1.25rem' }}>
                    <span id="benchmark-modus-label" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>Vergelijkingsmodus</span>
                    <div role="group" aria-labelledby="benchmark-modus-label" style={{ display: 'flex', gap: '0' }}>
                        {([
                            { key: 'gebieden', label: 'Specifieke Gebieden' },
                            { key: 'gemeente', label: 'Gemeente Gemiddelde' },
                            { key: 'fryslan', label: 'Fryslân Gemiddelde' },
                        ] as { key: BenchmarkMode; label: string }[]).map(tab => (
                            <button
                                key={tab.key}
                                type="button"
                                aria-pressed={mode === tab.key}
                                onClick={() => setMode(tab.key)}
                                style={{
                                    padding: '0.5rem 1.25rem',
                                    border: '1px solid var(--color-border)',
                                    background: mode === tab.key ? 'var(--color-primary)' : 'var(--color-surface)',
                                    color: mode === tab.key ? 'white' : 'var(--color-text)',
                                    cursor: 'pointer',
                                    fontSize: '0.85rem',
                                    fontWeight: mode === tab.key ? 600 : 400,
                                    borderRadius: tab.key === 'gebieden' ? 'var(--radius-sm) 0 0 var(--radius-sm)' :
                                        tab.key === 'fryslan' ? '0 var(--radius-sm) var(--radius-sm) 0' : '0',
                                }}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Modus-specifieke opties */}
                {mode === 'gebieden' && (
                    <div style={{ marginBottom: '1rem' }}>
                        <span id="benchmark-vergelijking-label" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                            Vergelijkingsgebieden (max. 5)
                        </span>
                        {gebiedenB.map((g, idx) => (
                            <div key={idx} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
                                <TypeaheadSelector
                                    value={gebiedenB[idx]}
                                    searchValue={gebiedenBSearch[idx]}
                                    onSearchChange={(s) => {
                                        const u = [...gebiedenBSearch]; u[idx] = s; setGebiedenBSearch(u);
                                    }}
                                    onSelect={(id, naam) => updateGebiedB(idx, id, naam)}
                                    placeholder={`Vergelijkingsgebied ${idx + 1}`}
                                    fieldId={`gebiedB_${idx}`}
                                    ariaLabel={`Vergelijkingsgebied ${idx + 1}`}
                                />
                                {gebiedenB.length > 1 && (
                                    <button type="button" onClick={() => removeGebiedB(idx)}
                                        aria-label={`Vergelijkingsgebied ${idx + 1} verwijderen`} title="Verwijderen"
                                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-danger, #ef4444)', padding: '0.25rem' }}>
                                        <X size={18} />
                                    </button>
                                )}
                            </div>
                        ))}
                        {gebiedenB.length < 5 && (
                            <button onClick={addGebiedB}
                                style={{
                                    background: 'none', border: '1px dashed var(--color-border)',
                                    color: 'var(--color-text-muted)', padding: '0.4rem 1rem',
                                    borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontSize: '0.85rem',
                                    display: 'flex', alignItems: 'center', gap: '0.25rem'
                                }}>
                                <Plus size={14} /> Voeg gebied toe
                            </button>
                        )}
                    </div>
                )}

                {mode === 'gemeente' && (
                    <div style={{ marginBottom: '1rem' }}>
                        <label htmlFor="benchmark-referentie-gemeente" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                            Referentie Gemeente
                        </label>
                        <select id="benchmark-referentie-gemeente"
                            value={referentieGemeente}
                            onChange={(e) => setReferentieGemeente(e.target.value)}
                            style={{
                                width: '100%', padding: '0.6rem 0.75rem',
                                background: 'var(--color-bg-alt)', border: '1px solid var(--color-border)',
                                borderRadius: 'var(--radius-sm)', color: 'var(--color-text)', fontSize: '0.9rem'
                            }}
                        >
                            <option value="" style={{ background: '#1e2535', color: '#e2e8f0' }}>Kies een gemeente...</option>
                            {gemeenten.map(g => (
                                <option key={g.code} value={g.code} style={{ background: '#1e2535', color: '#e2e8f0' }}>{g.naam}</option>
                            ))}
                        </select>
                    </div>
                )}

                {mode === 'fryslan' && (
                    <div style={{
                        padding: '1rem', background: 'var(--color-bg-alt)',
                        borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)',
                        marginBottom: '1rem', fontSize: '0.9rem', color: 'var(--color-text-muted)'
                    }}>
                        <strong>⌀ Provincie Fryslân</strong> — Vergelijkt Gebied A met het gemiddelde van alle ~965 buurten.
                    </div>
                )}

                {/* Laad knop */}
                <button
                    className="btn btn-primary"
                    onClick={fetchBenchmark}
                    disabled={!canLoadBenchmark() || dataLoading}
                    style={{ width: '100%', padding: '0.75rem', fontSize: '1rem', fontWeight: 600 }}
                >
                    {dataLoading ? (
                        <><RefreshCw size={16} className="spin" style={{ marginRight: '0.5rem' }} /> Vergelijking laden...</>
                    ) : (
                        <><BarChart3 size={16} style={{ marginRight: '0.5rem' }} /> Laad Vergelijking</>
                    )}
                </button>
            </div>

            {/* ─── Error ──────────────────────────────────────────────────── */}
            {dataError && (
                <div className="card" style={{ padding: '1rem', borderLeft: '4px solid var(--color-danger, #ef4444)', marginBottom: '1.5rem' }}>
                    <strong>Fout:</strong> {dataError}
                </div>
            )}

            {/* ─── Resultaten ─────────────────────────────────────────────── */}
            {benchmarkData && (
                <>
                    {/* Header met context */}
                    <div className="card" style={{ padding: '1.25rem', marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderLeft: '4px solid var(--color-primary)' }}>
                        <div>
                            <h2 style={{ margin: 0, fontSize: '1.1rem' }}>
                                {benchmarkData.gebied_a.naam}
                                <span style={{ color: 'var(--color-text-muted)', fontWeight: 400, margin: '0 0.75rem' }}>vs.</span>
                                {benchmarkData.referentie_label}
                            </h2>
                        </div>
                        <span style={{
                            background: 'var(--color-bg-alt)', padding: '0.35rem 0.75rem',
                            borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', color: 'var(--color-text-muted)'
                        }}>
                            {benchmarkData.totaal_indicatoren} indicatoren vergeleken
                        </span>
                    </div>

                    {/* AI Narrative */}
                    {(aiResponse || aiLoading || aiError) && (
                        <div className="card" style={{ padding: '1.5rem', marginBottom: '1.5rem', borderLeft: '4px solid var(--color-primary)' }}>
                            <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                                <Cpu size={20} className="text-primary" /> AI Vergelijkingsanalyse
                            </h2>
                            {aiLoading ? (
                                <div style={{ padding: '2rem', textAlign: 'center' }}>
                                    <RefreshCw className="spin text-primary" size={24} />
                                    <p style={{ marginTop: '1rem' }}>Analyseren van de vergelijking...</p>
                                    <small className="text-secondary">Het ingestelde taalmodel maakt de analyse (kan een minuut duren).</small>
                                </div>
                            ) : aiError ? (
                                <div className="error-message">{aiError}</div>
                            ) : aiResponse ? (
                                <div>
                                    <div style={{ fontSize: '1.05rem', lineHeight: 1.6 }}>{aiResponse.ai_narrative}</div>
                                    {aiResponse.ai && (
                                        <AILabel usecase="B" pagina="Beheer: benchmark"
                                            resultaat={aiResponse.ai_narrative}
                                            bronnen={[`${aiResponse.gebied_a?.naam ?? ''} t.o.v. ${aiResponse.referentie_label}`]} />
                                    )}
                                    {aiResponse.debug_info && aiResponse.debug_info.length > 0 && (
                                        <div style={{ marginTop: '1.5rem', borderTop: '1px dotted var(--color-border)', paddingTop: '1rem' }}>
                                            <button className="btn btn-secondary btn-sm" onClick={() => setShowDebugLogs(!showDebugLogs)}
                                                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                                                <Terminal size={14} />
                                                {showDebugLogs ? 'Verberg Debug Logs' : 'Bekijk Prompt (Debug)'}
                                                {showDebugLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                            </button>
                                            {showDebugLogs && (
                                                <div style={{ marginTop: '1rem' }}>
                                                    {aiResponse.debug_info.map((log, i) => (
                                                        <div key={i} style={{ background: '#1e1e1e', color: '#d4d4d4', padding: '1rem', borderRadius: '4px', fontSize: '0.8rem', overflowX: 'auto' }}>
                                                            <div style={{ color: '#569cd6', fontWeight: 'bold', marginBottom: '0.5rem' }}>
                                                                Context: {log.context} — Model: {log.model}
                                                            </div>
                                                            <div style={{ marginBottom: '0.5rem' }}>
                                                                <strong style={{ color: '#ce9178' }}>System Prompt:</strong>
                                                                <pre style={{ whiteSpace: 'pre-wrap', marginTop: '0.25rem' }}>{log.system_prompt}</pre>
                                                            </div>
                                                            <div>
                                                                <strong style={{ color: '#4ec9b0' }}>User Prompt:</strong>
                                                                <pre style={{ whiteSpace: 'pre-wrap', marginTop: '0.25rem' }}>{log.user_prompt}</pre>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ) : null}
                        </div>
                    )}

                    {/* Delta Tabel, gegroepeerd per kwadrant */}
                    {Object.entries(groupedByKwadrant).map(([kwadrant, items]) => (
                        <div key={kwadrant} className="card" style={{ marginBottom: '1.5rem' }}>
                            <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid var(--color-border)' }}>
                                <h3 style={{ margin: 0, color: 'var(--color-primary)', fontSize: '1rem' }}>{kwadrant}</h3>
                            </div>
                            <table className="table" style={{ width: '100%' }}>
                                <thead>
                                    <tr>
                                        <th style={{ textAlign: 'left', padding: '0.75rem 1rem' }}>Indicator</th>
                                        <th style={{ textAlign: 'right', padding: '0.75rem 0.5rem' }}>{benchmarkData.gebied_a.naam}</th>
                                        <th style={{ textAlign: 'right', padding: '0.75rem 0.5rem' }}>Referentie</th>
                                        <th style={{ textAlign: 'right', padding: '0.75rem 0.5rem' }}>Delta</th>
                                        <th style={{ textAlign: 'center', padding: '0.75rem 0.5rem', width: '150px' }}>Afwijking</th>
                                        <th style={{ textAlign: 'right', padding: '0.75rem 1rem' }}>Impact</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.map((item, idx) => (
                                        <tr key={idx}>
                                            <td style={{ padding: '0.6rem 1rem' }}>
                                                <strong>{item.indicator}</strong>
                                                {item.omschrijving && (
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.15rem' }}>
                                                        {item.omschrijving.length > 80 ? item.omschrijving.slice(0, 80) + '...' : item.omschrijving}
                                                    </div>
                                                )}
                                            </td>
                                            <td style={{ textAlign: 'right', padding: '0.6rem 0.5rem', fontWeight: 600 }}>
                                                {item.waarde_a} <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>{item.eenheid}</span>
                                            </td>
                                            <td style={{ textAlign: 'right', padding: '0.6rem 0.5rem', color: 'var(--color-text-secondary)' }}>
                                                {item.referentie_waarde} <span style={{ fontSize: '0.75rem' }}>{item.eenheid}</span>
                                            </td>
                                            <td style={{
                                                textAlign: 'right', padding: '0.6rem 0.5rem', fontWeight: 700,
                                                color: item.impact.includes('positief') ? 'var(--color-success, #22c55e)' : item.impact.includes('negatief') ? 'var(--color-danger, #ef4444)' : 'var(--color-text)'
                                            }}>
                                                {item.delta > 0 ? '+' : ''}{item.delta}
                                            </td>
                                            <td style={{ padding: '0.6rem 0.5rem' }}>
                                                <DeltaBar delta={item.delta} maxDelta={maxDelta} impact={item.impact} />
                                            </td>
                                            <td style={{ textAlign: 'right', padding: '0.6rem 1rem' }}>
                                                <span style={{
                                                    padding: '0.2rem 0.6rem', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 500,
                                                    background: item.impact.includes('positief') ? 'rgba(34,197,94,0.15)' : item.impact.includes('negatief') ? 'rgba(239,68,68,0.15)' : 'var(--color-bg-alt)',
                                                    color: item.impact.includes('positief') ? 'var(--color-success, #22c55e)' : item.impact.includes('negatief') ? 'var(--color-danger, #ef4444)' : 'var(--color-text-muted)'
                                                }}>
                                                    {item.impact}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ))}
                </>
            )}
        </div>
    );
};
