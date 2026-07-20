import React, { useEffect, useState } from 'react';
import { dataControleAPI, postgrestAPI } from '../services/api';
import { useAdminStore } from '../hooks/useAdminStore';
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
                <style>{`
                    @keyframes spin { 100% { transform: rotate(360deg); } }
                    .spin { animation: spin 1s linear infinite; }
                `}</style>
                <Loader2 size={40} className="spin" style={{ color: '#3b82f6' }} />
                <h4 style={{ margin: 0, color: 'var(--color-text)' }}>{messages[textIdx]}</h4>
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-text-secondary)', textAlign: 'center', maxWidth: '400px' }}>
                    Het lokale AI-model analyseert momenteel de inhoudelijke context van elke mogelijke match. Dit kan 10 tot 30 seconden duren.
                </p>
            </div>
        );
    };
    
    // Deduplicatie State
    const { deduplicatieKandidaten, setDeduplicatieKandidaten } = useAdminStore();
    const kandidaten = deduplicatieKandidaten || [];
    const [loadingDeduplicatie, setLoadingDeduplicatie] = useState(false);
    const [errorDeduplicatie, setErrorDeduplicatie] = useState<string | null>(null);
    
    // Mutaties State
    const [mutaties, setMutaties] = useState<any[]>([]);
    const [loadingMutaties, setLoadingMutaties] = useState(false);
    
    // Acties State
    const [actionLog, setActionLog] = useState<string>('');
    const [loadingAction, setLoadingAction] = useState(false);

    useEffect(() => {
        if (activeTab === 'deduplicatie' && deduplicatieKandidaten === null) {
            fetchDeduplicatie();
        } else if (activeTab === 'mutaties') {
            fetchMutaties();
        }
    }, [activeTab, deduplicatieKandidaten]);

    const fetchDeduplicatie = async () => {
        setLoadingDeduplicatie(true);
        setErrorDeduplicatie(null);
        try {
            const res = await dataControleAPI.getDeduplicatieKandidaten();
            setDeduplicatieKandidaten(res.data);
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

    const handleMerge = async (groep_id: string, actie: string) => {
        const kandidaat = kandidaten.find(k => k.groep_id === groep_id);
        if (!kandidaat) return;
        
        const selected: string[] = kandidaat.geselecteerde_uuids || [];
        const primaryUuid: string = kandidaat.geselecteerde_primary;
        
        if (selected.length < 2) {
            alert('Selecteer minimaal 2 indicatoren om samen te voegen.');
            return;
        }
        if (!primaryUuid || !selected.includes(primaryUuid)) {
            alert('Selecteer eerst een hoofd-indicator (radio) uit je selectie.');
            return;
        }
        
        const duplicateUuids = selected.filter(u => u !== primaryUuid);
        if (!window.confirm(`Weet je zeker dat je ${duplicateUuids.length} indicator(en) wilt ${actie === 'exact_duplicaat' ? 'samenvoegen' : 'groeperen'}?`)) return;
        
        setLoadingDeduplicatie(true);
        try {
            await dataControleAPI.mergeDeduplicatie({ primary_uuid: primaryUuid, duplicate_uuids: duplicateUuids, actie });
            await fetchDeduplicatie();
        } catch (error: any) {
            console.error('Error merging', error);
            alert('Fout bij samenvoegen: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoadingDeduplicatie(false);
        }
    };

    const handleUitzondering = async (groep_id: string) => {
        const kandidaat = kandidaten.find(k => k.groep_id === groep_id);
        if (!kandidaat) return;
        
        const allUuids = kandidaat.indicatoren.map((i: any) => i.uuid);
        if (!window.confirm(`Alle ${allUuids.length} indicatoren in deze groep markeren als 'Gecheckt, geen duplicaten'? Ze verschijnen dan niet meer in toekomstige scans.`)) return;
        
        setLoadingDeduplicatie(true);
        try {
            await dataControleAPI.markeerUitzondering(allUuids);
            await fetchDeduplicatie();
        } catch (error: any) {
            console.error('Error marking uitzondering', error);
            alert('Fout: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoadingDeduplicatie(false);
        }
    };

    const toggleSelectie = (groep_id: string, uuid: string) => {
        setDeduplicatieKandidaten(kandidaten.map(k => {
            if (k.groep_id !== groep_id) return k;
            const current: string[] = k.geselecteerde_uuids || [];
            const next = current.includes(uuid) 
                ? current.filter((u: string) => u !== uuid)
                : [...current, uuid];
            // Als de primary niet meer in de selectie zit, reset hem
            const primary = next.includes(k.geselecteerde_primary) ? k.geselecteerde_primary : (next.length > 0 ? next[0] : null);
            return { ...k, geselecteerde_uuids: next, geselecteerde_primary: primary };
        }));
    };

    const setPrimary = (groep_id: string, uuid: string) => {
        setDeduplicatieKandidaten(kandidaten.map(k => 
            k.groep_id === groep_id ? { ...k, geselecteerde_primary: uuid } : k
        ));
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
                                    const selected: string[] = kandidaat.geselecteerde_uuids || [];
                                    const primaryUuid: string = kandidaat.geselecteerde_primary || '';
                                    
                                    return (
                                    <div key={kandidaat.groep_id || idx} style={{ border: '1px solid var(--color-border)', borderRadius: '6px', padding: '1rem', background: 'var(--color-surface-light)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                                            <div style={{ flex: 1 }}>
                                                <div style={{ marginBottom: '1rem', padding: '0.75rem', background: 'rgba(59, 130, 246, 0.1)', borderLeft: '3px solid #3b82f6', borderRadius: '4px' }}>
                                                    <strong>🤖 AI Advies:</strong> {kandidaat.ai_advies}
                                                </div>
                                                
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                                    <h4 style={{ margin: 0 }}>Selecteer indicatoren om te verwerken:</h4>
                                                    {selected.length > 0 && (
                                                        <span style={{ fontSize: '0.85rem', color: '#3b82f6', fontWeight: 600 }}>
                                                            {selected.length} geselecteerd
                                                        </span>
                                                    )}
                                                </div>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                    {kandidaat.indicatoren.map((ind: any) => {
                                                        const isSelected = selected.includes(ind.uuid);
                                                        return (
                                                        <div key={ind.uuid} style={{ 
                                                            display: 'flex', gap: '0.75rem', padding: '0.5rem', 
                                                            background: isSelected ? 'rgba(59, 130, 246, 0.08)' : 'var(--color-surface)', 
                                                            border: isSelected ? '1px solid #3b82f6' : '1px solid var(--color-border)', 
                                                            borderRadius: '4px', cursor: 'pointer',
                                                            transition: 'all 0.15s ease'
                                                        }}
                                                        onClick={() => toggleSelectie(kandidaat.groep_id, ind.uuid)}
                                                        >
                                                            <input 
                                                                type="checkbox" 
                                                                checked={isSelected}
                                                                onChange={() => {}}
                                                                style={{ marginTop: '2px' }}
                                                            />
                                                            {isSelected && selected.length >= 2 && (
                                                                <input 
                                                                    type="radio" 
                                                                    name={`primary-${kandidaat.groep_id}`} 
                                                                    checked={primaryUuid === ind.uuid}
                                                                    title="Hoofd indicator"
                                                                    onChange={(e) => { e.stopPropagation(); setPrimary(kandidaat.groep_id, ind.uuid); }}
                                                                    onClick={(e) => e.stopPropagation()}
                                                                    style={{ marginTop: '2px' }}
                                                                />
                                                            )}
                                                            <div style={{ flex: 1 }}>
                                                                <div style={{ fontWeight: 600 }}>
                                                                    {ind.naam}
                                                                    {isSelected && primaryUuid === ind.uuid && selected.length >= 2 && (
                                                                        <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', background: '#3b82f6', color: 'white', padding: '1px 6px', borderRadius: '3px' }}>HOOFD</span>
                                                                    )}
                                                                </div>
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
                                                        </div>
                                                    )})}
                                                </div>
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', minWidth: '220px' }}>
                                                <button className="btn btn-primary" disabled={selected.length < 2} onClick={() => handleMerge(kandidaat.groep_id, 'exact_duplicaat')}>
                                                    Merge Selectie ({selected.length})
                                                </button>
                                                <button className="btn btn-secondary" disabled={selected.length < 2} onClick={() => handleMerge(kandidaat.groep_id, 'groepeer_bronnen')}>
                                                    Groepeer Selectie ({selected.length})
                                                </button>
                                                <hr style={{ border: 'none', borderTop: '1px solid var(--color-border)', margin: '0.25rem 0' }} />
                                                <button 
                                                    className="btn" 
                                                    style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)' }}
                                                    onClick={() => handleUitzondering(kandidaat.groep_id)}
                                                >
                                                    ✅ Gecheckt, Geen Duplicaten
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
