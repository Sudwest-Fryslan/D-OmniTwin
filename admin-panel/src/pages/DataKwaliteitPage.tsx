import React, { useEffect, useState } from 'react';
import { dataControleAPI, postgrestAPI } from '../services/api';
import { Layers, Activity, Zap, Loader2, CheckCircle, Search, RefreshCw, Bot } from 'lucide-react';

export const DataKwaliteitPage: React.FC = () => {
    const [activeTab, setActiveTab] = useState<'deduplicatie' | 'mutaties' | 'acties'>('deduplicatie');
    
    // Dynamic Loader Component voor betere UX tijdens AI calls
    const DynamicLoader = () => {
        const [textIdx, setTextIdx] = useState(0);
        const messages = [
            "🔍 Database doorzoeken op duplicaten...",
            "🧮 Semantische vectoren en teksten vergelijken...",
            "🧠 AI-model (Lokale LLM) wordt geraadpleegd voor advies...",
            "⏳ LLM is de matches aan het valideren, dit kan even duren...",
            "⚙️ Laatste controles uitvoeren..."
        ];

        useEffect(() => {
            const interval = setInterval(() => {
                setTextIdx((prev) => (prev < messages.length - 1 ? prev + 1 : prev));
            }, 5000);
            return () => clearInterval(interval);
            // eslint-disable-next-line react-hooks/exhaustive-deps
        }, []);

        return (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4rem', gap: '1rem', background: 'var(--color-surface-light)', borderRadius: '8px', border: '1px dashed var(--color-border)' }}>
                <Loader2 size={40} className="spin" style={{ color: '#3b82f6' }} />
                <h4 style={{ margin: 0, color: 'var(--color-text)' }}>{messages[textIdx]}</h4>
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-text-secondary)', textAlign: 'center', maxWidth: '400px' }}>
                    Het lokale AI-model analyseert momenteel de inhoudelijke context van elke mogelijke match. Dit kan 10 tot 30 seconden duren.
                </p>
            </div>
        );
    };
    
    // Deduplicatie State
    const [kandidaten, setKandidaten] = useState<any[]>([]);
    const [loadingDeduplicatie, setLoadingDeduplicatie] = useState(false);
    const [errorDeduplicatie, setErrorDeduplicatie] = useState<string | null>(null);
    
    // Mutaties State
    const [mutaties, setMutaties] = useState<any[]>([]);
    const [loadingMutaties, setLoadingMutaties] = useState(false);
    
    // Acties State
    const [actionLog, setActionLog] = useState<string>('');
    const [loadingAction, setLoadingAction] = useState(false);

    useEffect(() => {
        if (activeTab === 'deduplicatie') {
            fetchDeduplicatie();
        } else if (activeTab === 'mutaties') {
            fetchMutaties();
        }
    }, [activeTab]);

    const fetchDeduplicatie = async () => {
        setLoadingDeduplicatie(true);
        setErrorDeduplicatie(null);
        try {
            const res = await dataControleAPI.getDeduplicatieKandidaten();
            setKandidaten(res.data);
        } catch (error: any) {
            console.error('Error fetching kandidaten', error);
            const detail = error.response?.data?.detail || error.message || 'Onbekende fout';
            setErrorDeduplicatie(`Fout bij ophalen: ${detail}`);
        } finally {
            setLoadingDeduplicatie(false);
        }
    };

    const fetchMutaties = async () => {
        setLoadingMutaties(true);
        try {
            // Fetch mutaties of the last 30 days directly via PostgREST API
            const res = await postgrestAPI.getIndicatorenMutaties(30);
            setMutaties(res.data);
        } catch (error: any) {
            console.error('Error fetching mutaties', error);
        } finally {
            setLoadingMutaties(false);
        }
    };

    const handleMerge = async (primary_uuid: string, duplicate_uuids: string[], actie: string) => {
        if (!window.confirm(`Weet je zeker dat je deze actie ('${actie}') wilt uitvoeren?`)) return;
        setLoadingDeduplicatie(true);
        try {
            await dataControleAPI.mergeDeduplicatie({ primary_uuid, duplicate_uuids, actie });
            await fetchDeduplicatie(); // reload
        } catch (error: any) {
            console.error('Error merging', error);
            alert('Fout bij samenvoegen: ' + error.response?.data?.detail || error.message);
        } finally {
            setLoadingDeduplicatie(false);
        }
    };

    const handleRunLineage = async () => {
        setLoadingAction(true);
        setActionLog('Data Lineage check gestart...');
        try {
            const res = await dataControleAPI.runDataLineage();
            setActionLog(prev => prev + '\nVoltooid. Resultaten:\n' + JSON.stringify(res.data, null, 2));
        } catch (error: any) {
            setActionLog(prev => prev + '\nFout: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoadingAction(false);
        }
    };

    const handleGenereerOntologie = async () => {
        const uuids = mutaties.slice(0, 5).map(m => m.uuid);
        if (uuids.length === 0) {
            alert('Geen mutaties beschikbaar (laad eerst de mutaties tab).');
            return;
        }
        setLoadingAction(true);
        setActionLog(`AI-ontologie generatie gestart voor ${uuids.length} indicatoren...`);
        try {
            const res = await dataControleAPI.genereerOntologie(uuids);
            setActionLog(prev => prev + '\nVoltooid. ' + res.data.message);
        } catch (error: any) {
            setActionLog(prev => prev + '\nFout: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoadingAction(false);
        }
    };

    const handleHerbereken = async () => {
        const uuids = mutaties.slice(0, 5).map(m => m.uuid);
        if (uuids.length === 0) {
            alert('Geen mutaties beschikbaar (laad eerst de mutaties tab).');
            return;
        }
        setLoadingAction(true);
        setActionLog(`Statistieken herberekenen voor ${uuids.length} indicatoren...`);
        try {
            const res = await dataControleAPI.herberekenStatistieken(uuids);
            setActionLog(prev => prev + '\nVoltooid. ' + res.data.message);
        } catch (error: any) {
            setActionLog(prev => prev + '\nFout: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoadingAction(false);
        }
    };

    const tabStyle = (active: boolean): React.CSSProperties => ({
        padding: '12px 24px', cursor: 'pointer', fontWeight: active ? 600 : 400,
        borderBottom: active ? '2px solid var(--accent-color, #4A90D9)' : '2px solid transparent',
        color: active ? 'var(--accent-color, #4A90D9)' : 'var(--color-text-secondary)',
        background: 'none', border: 'none', fontSize: '0.95rem',
        display: 'flex', alignItems: 'center', gap: '8px'
    });

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: 'calc(100vh - 140px)' }}>
            <div className="card" style={{ flexShrink: 0 }}>
                <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Activity size={20} /> Data Kwaliteit & Beheer
                </h2>
                <div style={{ display: 'flex', borderBottom: '1px solid var(--color-border)', marginTop: '1rem' }}>
                    <button style={tabStyle(activeTab === 'deduplicatie')} onClick={() => setActiveTab('deduplicatie')}>
                        <Layers size={16} /> Deduplicatie Kandidaten
                    </button>
                    <button style={tabStyle(activeTab === 'mutaties')} onClick={() => setActiveTab('mutaties')}>
                        <Search size={16} /> Recente Mutaties
                    </button>
                    <button style={tabStyle(activeTab === 'acties')} onClick={() => setActiveTab('acties')}>
                        <Zap size={16} /> Systeemacties
                    </button>
                </div>
            </div>

            <div className="card" style={{ flex: 1, overflow: 'auto' }}>
                {activeTab === 'deduplicatie' && (
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <p style={{ color: 'var(--color-text-secondary)' }}>Automatisch gedetecteerde dubbele indicatoren op basis van fuzzy-matching (85%+).</p>
                            <button className="btn btn-secondary" onClick={fetchDeduplicatie} disabled={loadingDeduplicatie}>
                                {loadingDeduplicatie ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />} Vernieuwen
                            </button>
                        </div>
                        {loadingDeduplicatie ? (
                            <DynamicLoader />
                        ) : errorDeduplicatie ? (
                            <div style={{ padding: '2rem', textAlign: 'center', color: '#ef4444', background: 'rgba(239,68,68,0.1)', borderRadius: '6px', border: '1px solid rgba(239,68,68,0.3)' }}>
                                ⚠️ {errorDeduplicatie}
                            </div>
                        ) : kandidaten.length === 0 ? (
                            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>Geen duplicaten gevonden!</div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                {kandidaten.map((kandidaat, idx) => {
                                    // Default de eerste als primary
                                    const primaryUuid = kandidaat.geselecteerde_primary || kandidaat.indicatoren[0].uuid;
                                    const primaryInd = kandidaat.indicatoren.find((i: any) => i.uuid === primaryUuid) || kandidaat.indicatoren[0];
                                    const duplicates = kandidaat.indicatoren.filter((i: any) => i.uuid !== primaryUuid);
                                    
                                    return (
                                    <div key={kandidaat.groep_id || idx} style={{ border: '1px solid var(--color-border)', borderRadius: '6px', padding: '1rem', background: 'var(--color-surface-light)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                                            <div style={{ flex: 1 }}>
                                                <div style={{ marginBottom: '1rem', padding: '0.75rem', background: 'rgba(59, 130, 246, 0.1)', borderLeft: '3px solid #3b82f6', borderRadius: '4px' }}>
                                                    <strong>🤖 AI Advies:</strong> {kandidaat.ai_advies}
                                                </div>
                                                
                                                <h4 style={{ margin: '0 0 0.5rem 0' }}>Selecteer Hoofd Indicator:</h4>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                                    {kandidaat.indicatoren.map((ind: any) => (
                                                        <label key={ind.uuid} style={{ display: 'flex', gap: '0.75rem', padding: '0.5rem', background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: '4px', cursor: 'pointer' }}>
                                                            <input 
                                                                type="radio" 
                                                                name={`primary-${kandidaat.groep_id}`} 
                                                                checked={primaryUuid === ind.uuid}
                                                                onChange={() => {
                                                                    setKandidaten(prev => prev.map(k => k.groep_id === kandidaat.groep_id ? {...k, geselecteerde_primary: ind.uuid} : k));
                                                                }}
                                                            />
                                                            <div style={{ flex: 1 }}>
                                                                <div style={{ fontWeight: 600 }}>{ind.naam}</div>
                                                                <div style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                                                                    {ind.bron} | {ind.categorie} <br/>
                                                                    <span style={{ fontFamily: 'monospace', color: '#888' }}>UUID: {ind.uuid}</span>
                                                                </div>
                                                                {ind.broodkruimels && ind.broodkruimels.length > 0 && (
                                                                    <div style={{ marginTop: '0.25rem', fontSize: '0.8rem', color: '#10b981' }}>
                                                                        📍 {ind.broodkruimels.join(' | ')}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </label>
                                                    ))}
                                                </div>
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', minWidth: '200px' }}>
                                                <button className="btn btn-primary" onClick={() => handleMerge(primaryUuid, duplicates.map((d: any) => d.uuid), 'exact_duplicaat')}>
                                                    Merge als Exact Duplicaat
                                                </button>
                                                <button className="btn btn-secondary" onClick={() => handleMerge(primaryUuid, duplicates.map((d: any) => d.uuid), 'groepeer_bronnen')}>
                                                    Groepeer Bronnen
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )})}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'mutaties' && (
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <p style={{ color: 'var(--color-text-secondary)' }}>Indicatoren die de afgelopen 30 dagen zijn toegevoegd of gewijzigd (Direct via PostgREST API).</p>
                            <button className="btn btn-secondary" onClick={fetchMutaties} disabled={loadingMutaties}>
                                {loadingMutaties ? <Loader2 size={16} className="spin" /> : <RefreshCw size={16} />} Vernieuwen
                            </button>
                        </div>
                        {loadingMutaties ? (
                            <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}><Loader2 size={24} className="spin" /></div>
                        ) : mutaties.length === 0 ? (
                            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>Geen recente mutaties.</div>
                        ) : (
                            <table className="table">
                                <thead>
                                    <tr>
                                        <th>Naam</th>
                                        <th>Categorie</th>
                                        <th>Aangemaakt</th>
                                        <th>Gewijzigd</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {mutaties.map((mut) => (
                                        <tr key={mut.uuid}>
                                            <td>{mut.naam}</td>
                                            <td>{mut.categorie}</td>
                                            <td style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                                                {new Date(mut.created_at).toLocaleDateString()}
                                            </td>
                                            <td style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                                                {new Date(mut.updated_at).toLocaleDateString()}
                                            </td>
                                            <td>
                                                <span className={`badge ${mut.is_actief ? 'badge-positive' : 'badge-negative'}`}>
                                                    {mut.is_actief ? 'Actief' : 'Inactief'}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                )}

                {activeTab === 'acties' && (
                    <div style={{ display: 'flex', gap: '2rem' }}>
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <div className="card" style={{ background: 'var(--color-surface-light)', border: '1px solid var(--color-border)' }}>
                                <h3 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <Layers size={18} /> Data Lineage Check
                                </h3>
                                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: '1rem' }}>
                                    Controleer of externe bronnen (zoals CBS OData) recent zijn bijgewerkt.
                                </p>
                                <button className="btn btn-secondary" onClick={handleRunLineage} disabled={loadingAction}>
                                    Lineage Check Uitvoeren
                                </button>
                            </div>

                            <div className="card" style={{ background: 'var(--color-surface-light)', border: '1px solid var(--color-border)' }}>
                                <h3 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <Bot size={18} /> AI-Ontologie Generatie
                                </h3>
                                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: '1rem' }}>
                                    Forceer de generatie van AI-beschrijvingen voor recent gewijzigde indicatoren.
                                </p>
                                <button className="btn btn-secondary" onClick={handleGenereerOntologie} disabled={loadingAction}>
                                    Genereer Ontologie
                                </button>
                            </div>

                            <div className="card" style={{ background: 'var(--color-surface-light)', border: '1px solid var(--color-border)' }}>
                                <h3 style={{ margin: '0 0 0.5rem 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <Activity size={18} /> Statistieken Herberekenen
                                </h3>
                                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: '1rem' }}>
                                    Herbereken globale min/max waarden en datakwaliteitsscores op basis van nieuwe data.
                                </p>
                                <button className="btn btn-secondary" onClick={handleHerbereken} disabled={loadingAction}>
                                    Herbereken Statistieken
                                </button>
                            </div>
                        </div>

                        <div style={{ flex: 1 }}>
                            <div style={{ 
                                background: '#111827', 
                                borderRadius: '6px', 
                                padding: '1rem', 
                                height: '100%',
                                minHeight: '300px',
                                border: '1px solid #374151',
                                color: '#A7F3D0',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem',
                                whiteSpace: 'pre-wrap',
                                overflow: 'auto'
                            }}>
                                {actionLog || 'Selecteer een actie om te beginnen. Output verschijnt hier...'}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
