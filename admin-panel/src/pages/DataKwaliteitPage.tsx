import React, { useEffect, useState } from 'react';
import { dataControleAPI, postgrestAPI } from '../services/api';
import { Layers, Activity, Zap, Loader2, CheckCircle, Search, RefreshCw, Bot } from 'lucide-react';

export const DataKwaliteitPage: React.FC = () => {
    const [activeTab, setActiveTab] = useState<'deduplicatie' | 'mutaties' | 'acties'>('deduplicatie');
    
    // Deduplicatie State
    const [kandidaten, setKandidaten] = useState<any[]>([]);
    const [loadingDeduplicatie, setLoadingDeduplicatie] = useState(false);
    
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
        try {
            const res = await dataControleAPI.getDeduplicatieKandidaten();
            setKandidaten(res.data);
        } catch (error: any) {
            console.error('Error fetching kandidaten', error);
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
                            <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}><Loader2 size={24} className="spin" /></div>
                        ) : kandidaten.length === 0 ? (
                            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>Geen duplicaten gevonden!</div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                {kandidaten.map((kandidaat, idx) => (
                                    <div key={idx} style={{ border: '1px solid var(--color-border)', borderRadius: '6px', padding: '1rem', background: 'var(--color-surface-light)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                            <div>
                                                <h4 style={{ margin: '0 0 0.5rem 0' }}>Hoofd Indicator: {kandidaat.primary.naam}</h4>
                                                <div style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>
                                                    <strong>UUID:</strong> {kandidaat.primary.uuid}<br/>
                                                    <strong>Bron:</strong> {kandidaat.primary.bron} | <strong>Categorie:</strong> {kandidaat.primary.categorie}
                                                </div>
                                                <div style={{ marginTop: '1rem' }}>
                                                    <strong>Mogelijke Duplicaten ({kandidaat.duplicates.length}):</strong>
                                                    <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem', fontSize: '0.85rem' }}>
                                                        {kandidaat.duplicates.map((d: any) => (
                                                            <li key={d.uuid}>
                                                                {d.naam} <em>(Score: {d.match_score}%)</em> - {d.bron}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                <button className="btn btn-primary" onClick={() => handleMerge(kandidaat.primary.uuid, kandidaat.duplicates.map((d: any) => d.uuid), 'exact_duplicaat')}>
                                                    Merge als Exact Duplicaat
                                                </button>
                                                <button className="btn btn-secondary" onClick={() => handleMerge(kandidaat.primary.uuid, kandidaat.duplicates.map((d: any) => d.uuid), 'groepeer_bronnen')}>
                                                    Groepeer Bronnen
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
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
