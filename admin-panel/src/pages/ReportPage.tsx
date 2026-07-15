import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { reportAPI } from '../services/api';
import type { ReportDataPayload, ReportNarrativeResponse } from '../types';
import { Download, RefreshCw, Printer, AlertCircle, TrendingUp, Info, Activity, ArrowLeft, Cpu, Database, Map as MapIcon, Compass, Terminal, ChevronDown, ChevronUp, X } from 'lucide-react';
import { ExportPrintModal } from '../components/ExportPrintModal';

export const ReportPage: React.FC = () => {
    const { gebied_id } = useParams<{ gebied_id?: string }>();
    const navigate = useNavigate();
    const originalTitleRef = useRef(document.title);

    // Gebied Selectie State (tijdelijke hardcode of default 'BU19700104' voor test)
    const [selectedGebied, setSelectedGebied] = useState(gebied_id || 'BU19700104');

    // Payload State
    const [dataPayload, setDataPayload] = useState<ReportDataPayload | null>(null);
    const [dataLoading, setDataLoading] = useState(false);
    const [dataError, setDataError] = useState<string | null>(null);

    // AI State
    const [aiResponse, setAiResponse] = useState<ReportNarrativeResponse | null>(null);
    const [aiLoading, setAiLoading] = useState(false);
    const [aiError, setAiError] = useState<string | null>(null);
    const [showDebugLogs, setShowDebugLogs] = useState(false);
    const [showPrintModal, setShowPrintModal] = useState(false);

    // Visual State (Map en Kompas Exports)
    const [mapSnapshot, setMapSnapshot] = useState<string | null>(null);
    const [mapSnapshotError, setMapSnapshotError] = useState<string | null>(null);
    const [kompasSnapshot, setKompasSnapshot] = useState<string | null>(null);
    const [kompasSnapshotError, setKompasSnapshotError] = useState<string | null>(null);

    const fetchReportData = async () => {
        setDataLoading(true);
        setDataError(null);
        try {
            const response = await reportAPI.getData(selectedGebied);
            setDataPayload(response.data);
        } catch (err: any) {
            setDataError(err.message || 'Fout bij ophalen gebiedsdata');
        } finally {
            setDataLoading(false);
        }
    };

    const generateAI = async () => {
        setAiLoading(true);
        setAiError(null);
        try {
            const response = await reportAPI.getNarrative(selectedGebied);
            setAiResponse(response.data);
        } catch (err: any) {
            setAiError(err.message || 'Fout bij genereren AI narrative');
        } finally {
            setAiLoading(false);
        }
    };

    useEffect(() => {
        if (selectedGebied) {
            fetchReportData();
        }

        // Listener voor image data vanuit de hoofdapplicatie (app.js canvas export)
        const handleMessage = (event: MessageEvent) => {
            if (event.data) {
                if (event.data.type === 'mapSnapshot' && event.data.image) {
                    setMapSnapshot(event.data.image);
                    setMapSnapshotError(null);
                }
                if (event.data.type === 'mapSnapshotError' && event.data.error) {
                    setMapSnapshotError(event.data.error);
                }
                if (event.data.type === 'kompasSnapshot' && event.data.image) {
                    setKompasSnapshot(event.data.image);
                    setKompasSnapshotError(null);
                }
                if (event.data.type === 'kompasSnapshotError' && event.data.error) {
                    setKompasSnapshotError(event.data.error);
                }
            }
        };

        window.addEventListener('message', handleMessage);

        // Vraag actief om een snapshot bij de parent window indien we ge-embed zijn of naast elkaar opereren
        if (window.opener || window.parent !== window) {
            const target = window.opener || window.parent;
            target.postMessage({ type: 'requestMapSnapshot', gebiedId: selectedGebied }, '*');
            target.postMessage({ type: 'requestKompasSnapshot', gebiedId: selectedGebied }, '*');
        }

        return () => window.removeEventListener('message', handleMessage);
    }, [selectedGebied]);

    const handlePrint = () => {
        originalTitleRef.current = document.title;
        if (dataPayload?.metadata) {
            const sanitize = (str: string) => {
                return str
                    .normalize('NFD')
                    .replace(/[\u0300-\u036f]/g, '')
                    .replace(/[^a-zA-Z0-9_\-]/g, '_')
                    .replace(/_+/g, '_');
            };

            const type = sanitize(dataPayload.metadata.gebiedstype);
            const code = sanitize(selectedGebied);
            const ref = sanitize(dataPayload.metadata.referentie_kader.replace('Gemeente ', ''));

            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');

            const dateStr = `${year}${month}${day}_${hours}${minutes}`;
            document.title = `${type}_${code}_${ref}_${dateStr}-export`;
        }
        setShowPrintModal(true);
    };

    const handleCloseModal = () => {
        setShowPrintModal(false);
        document.title = originalTitleRef.current;
    };

    return (
        <div className="page-container" style={{ maxWidth: '1400px', margin: '0 auto', padding: '2rem' }}>
            <div className="page-header hide-on-print">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <button
                            className="btn btn-secondary"
                            onClick={() => window.close()}
                            style={{ padding: '0.25rem 0.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                        >
                            <X size={16} /> Sluit rapport
                        </button>
                        <h1>D-OmniTwin Rapportage</h1>
                        <p className="text-secondary">AI-gedreven analyse voor {selectedGebied}</p>
                    </div>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <button
                            className="btn btn-secondary"
                            onClick={generateAI}
                            disabled={aiLoading || !dataPayload}
                        >
                            <Cpu size={16} style={{ marginRight: '0.5rem' }} />
                            {aiLoading ? 'AI Analyseren...' : 'Genereer AI Summary'}
                        </button>
                        <button
                            className="btn btn-primary"
                            onClick={handlePrint}
                        >
                            Exporteer PDF
                        </button>
                    </div>
                </div>
            </div>

            <div className="report-layout">
                {/* Linker kolom met inzichten */}
                <div className="report-main">

                    {/* Executive Summary AI Vlak */}
                    <div className="card report-section executive-summary" style={{ borderLeft: '4px solid var(--color-primary)' }}>
                        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                            <Cpu size={20} className="text-primary" /> Executive Summary (Lokale AI)
                        </h2>
                        {aiLoading ? (
                            <div className="loading-state" style={{ padding: '2rem', textAlign: 'center' }}>
                                <RefreshCw className="spin text-primary" size={24} />
                                <p style={{ marginTop: '1rem' }}>Samenvoegen tot totaaloverzicht...</p>
                                <small className="text-secondary">Bezig met genereren van kwadrant samenvattingen via lokale inferentie (ca. 60 sec).</small>
                            </div>
                        ) : aiError ? (
                            <div className="error-message">{aiError}</div>
                        ) : aiResponse ? (
                            <div className="ai-content">
                                <div style={{ fontSize: '1.1rem', lineHeight: 1.6, marginBottom: '2rem' }}>
                                    {aiResponse.ai_summary}
                                </div>

                                {aiResponse.domain_summaries && Object.keys(aiResponse.domain_summaries).length > 0 && (
                                    <div style={{ marginTop: '2rem', borderTop: '1px solid var(--color-border)', paddingTop: '1.5rem' }}>
                                        <h3 style={{ marginBottom: '1rem', fontSize: '1rem', color: 'var(--color-secondary)' }}>Analyse per Kwadrant</h3>
                                        <div className="rapport-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                                            {Object.entries(aiResponse.domain_summaries).map(([domain, text]) => (
                                                <div key={domain} className="card" style={{ padding: '1rem', background: 'var(--color-bg-alt)' }}>
                                                    <h4 style={{ color: 'var(--color-primary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>{domain}</h4>
                                                    <p style={{ fontSize: '0.9rem', lineHeight: 1.5, color: 'var(--color-text)' }}>{text}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {aiResponse.debug_info && (
                                    <div style={{ marginTop: '2rem', borderTop: '1px dotted var(--color-border)', paddingTop: '1rem' }}>
                                        <button
                                            className="btn btn-secondary btn-sm"
                                            onClick={() => setShowDebugLogs(!showDebugLogs)}
                                            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}
                                        >
                                            <Terminal size={14} />
                                            {showDebugLogs ? 'Verberg LLM Debug Logs' : 'Bekijk Prompt & JSON (LLM Debug Logs)'}
                                            {showDebugLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                        </button>

                                        {showDebugLogs && (
                                            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                                {aiResponse.debug_info.map((log, index) => (
                                                    <div key={index} style={{ background: '#1e1e1e', color: '#d4d4d4', padding: '1rem', borderRadius: '4px', fontSize: '0.8rem', overflowX: 'auto' }}>
                                                        <div style={{ color: '#569cd6', fontWeight: 'bold', marginBottom: '0.5rem', borderBottom: '1px solid #333', paddingBottom: '0.5rem' }}>
                                                            Gecontextualiseerde Call: {log.context} (Model: {log.model})
                                                        </div>
                                                        <div style={{ marginBottom: '1rem' }}>
                                                            <strong style={{ color: '#ce9178' }}>System Prompt:</strong>
                                                            <pre style={{ whiteSpace: 'pre-wrap', marginTop: '0.25rem' }}>{log.system_prompt}</pre>
                                                        </div>
                                                        <div>
                                                            <strong style={{ color: '#4ec9b0' }}>User Payload (Data/Query):</strong>
                                                            <pre style={{ whiteSpace: 'pre-wrap', marginTop: '0.25rem' }}>{log.user_prompt}</pre>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        ) : (
                            <p className="text-secondary">Klik op "Genereer AI Summary" om de kwadrant-analyses en totaal-samenvatting te maken.</p>
                        )}
                    </div>

                    <div className="card report-section" style={{ marginTop: '1.5rem' }}>
                        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                            <Database size={20} className="text-secondary" /> Significante Z-Score Datapunten
                        </h2>
                        <div style={{ background: 'var(--color-bg-alt)', borderLeft: '3px solid var(--color-primary)', borderRadius: '4px', padding: '0.6rem 1rem', marginBottom: '1rem', fontSize: '0.85rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                            ❓ <strong>Z-score:</strong> Vergelijkt een indicator met het gemiddelde van de referentiegroep. Score 0 = gemiddeld &nbsp;·&nbsp; Score &gt;+1 = beduidend hoger &nbsp;·&nbsp; Score &lt;-1 = beduidend lager. De kolom <em>Impact</em> geeft aan of de afwijking positief of negatief is voor de leefbaarheid.
                        </div>

                        {dataLoading ? (
                            <p>Data laden...</p>
                        ) : dataError ? (
                            <div className="error-message">{dataError}</div>
                        ) : dataPayload && Object.keys(dataPayload.significante_domeinen).length > 0 ? (
                            <div className="data-grid">
                                {Object.entries(dataPayload.significante_domeinen).map(([domein, indicatoren]) => (
                                    <div key={domein} className="domein-block" style={{ marginBottom: '1.5rem' }}>
                                        <h4 style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem', color: 'var(--color-primary)' }}>{domein}</h4>
                                        <table className="table" style={{ width: '100%', marginTop: '0.5rem' }}>
                                            <thead>
                                                <tr>
                                                    <th style={{ textAlign: 'left' }}>Indicator</th>
                                                    <th style={{ textAlign: 'left' }}>Waarde</th>
                                                    <th style={{ textAlign: 'left' }}>Jaar</th>
                                                    <th style={{ textAlign: 'right' }}>Z-Score</th>
                                                    <th style={{ textAlign: 'right' }}>Impact</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {indicatoren.map((ind, i) => (
                                                    <tr key={i}>
                                                        <td>
                                                            <strong>{ind.indicator}</strong>
                                                            {ind.omschrijving && (
                                                                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>{ind.omschrijving}</div>
                                                            )}
                                                        </td>
                                                        <td style={{ textAlign: 'left', fontWeight: 'bold' }}>{ind.waarde} <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontWeight: 'normal' }}>{ind.eenheid}</span></td>
                                                        <td style={{ textAlign: 'left', color: 'var(--color-text-secondary)' }}>{ind.meetjaar}</td>
                                                        <td style={{ textAlign: 'right', fontWeight: 'bold', color: ind.impact.includes('positief') ? 'var(--color-success)' : ind.impact.includes('negatief') ? 'var(--color-danger)' : 'var(--color-text)' }}>
                                                            {ind.z_score > 0 ? '+' : ''}{ind.z_score}
                                                        </td>
                                                        <td style={{ textAlign: 'right' }}>
                                                            <span className={`badge ${ind.impact.includes('positief') ? 'badge-positive' : ind.impact.includes('negatief') ? 'badge-negative' : 'badge-neutral'} `}>
                                                                {ind.impact}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-secondary">Geen uitschieters (Z-Score &gt; 1.0 of &lt; -1.0) gevonden voor dit gebied t.o.v. de referentiegroep {dataPayload?.referentie_groep}.</p>
                        )}
                    </div>

                </div>

                {/* Rechter kolom voor Map & Kompas Visuals */}
                <div className="report-sidebar">
                    <div className="card report-visual" style={{ minHeight: '300px', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>
                        <div style={{ padding: '1rem', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
                            <MapIcon size={16} /> Gebied op Kaart
                        </div>
                        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--color-bg-alt)' }}>
                            {mapSnapshot ? (
                                <img src={mapSnapshot} alt="Kaart weergave van het gebied" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                            ) : mapSnapshotError ? (
                                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-danger)' }}>
                                    <strong>Fout bij kaart-export:</strong><br />
                                    <span style={{ fontSize: '0.85rem' }}>{mapSnapshotError}</span>
                                </div>
                            ) : (
                                <p className="text-secondary" style={{ padding: '2rem', textAlign: 'center' }}>
                                    Geen kaartbeeld ontvangen van de hoofdapplicatie.
                                </p>
                            )}
                        </div>
                    </div>

                    <div className="card report-visual" style={{ minHeight: '400px', display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden', marginTop: '1.5rem' }}>
                        <div style={{ padding: '1rem', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
                            <Compass size={16} /> D-Omni Kompas Profiel
                        </div>
                        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--color-bg-alt)' }}>
                            {kompasSnapshot ? (
                                <img src={kompasSnapshot} alt="Kompas weergave van het gebied" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                            ) : kompasSnapshotError ? (
                                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-danger)' }}>
                                    <strong>Fout bij kompas-export:</strong><br />
                                    <span style={{ fontSize: '0.85rem' }}>{kompasSnapshotError}</span>
                                </div>
                            ) : (
                                <p className="text-secondary" style={{ padding: '2rem', textAlign: 'center' }}>
                                    Geen kompasbeeld ontvangen van de hoofdapplicatie. Selecteer het gebied in de linker monitor applicatie om data te delen.
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Nieuw Gebiedsinformatie Blokje */}
                    {dataPayload?.metadata && (
                        <div className="card report-section" style={{ marginTop: '1.5rem', background: 'var(--color-surface)', padding: '1.5rem' }}>
                            <h3 style={{ borderBottom: '2px solid var(--color-border)', paddingBottom: '0.5rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>
                                Gebiedsinformatie
                            </h3>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '0.75rem', fontSize: '1rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ color: 'var(--color-text-secondary)' }}>Naam:</span>
                                    <strong style={{ color: 'var(--color-text-primary)' }}>{dataPayload.metadata.gebied}</strong>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ color: 'var(--color-text-secondary)' }}>Type:</span>
                                    <strong style={{ color: 'var(--color-text-primary)' }}>{dataPayload.metadata.gebiedstype}</strong>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ color: 'var(--color-text-secondary)' }}>Referentiekader:</span>
                                    <strong style={{ color: 'var(--color-text-primary)' }}>{dataPayload.metadata.referentie_kader}</strong>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span style={{ color: 'var(--color-text-secondary)' }}>Totaal Indicatoren Analysegroep:</span>
                                    <strong style={{ color: 'var(--color-text-primary)' }}>{dataPayload.aantal_indicatoren}</strong>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
            
            <ExportPrintModal 
                isOpen={showPrintModal} 
                onClose={handleCloseModal} 
            />
        </div>
    );
};
