import React, { useEffect, useState } from 'react';
import { indicatorenAPI, polariteitenAPI, colorSchemasAPI } from '../services/api';
import { useAdminStore } from '../hooks/useAdminStore';
import { Search, ChevronLeft, ChevronRight, Edit, Save, X, Loader2, CheckCircle, Bot, Clock } from 'lucide-react';
import type { Indicator, IndicatorUpdate, OntologieStatus } from '../types';

// ── Helper: Status Badge ────────────────────────────────────────────────────
const OntologieStatusBadge: React.FC<{ status?: OntologieStatus | null }> = ({ status }) => {
    const config: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
        'draft': { icon: <Bot size={12} />, label: 'Draft', color: '#94A3B8' },
        'beoordeeld_ai': { icon: <Bot size={12} />, label: 'AI', color: '#F59E0B' },
        'goedgekeurd_mens': { icon: <CheckCircle size={12} />, label: '✓', color: '#22C55E' },
    };
    const c = config[status || 'draft'] || config['draft'];
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '3px',
            padding: '2px 6px', borderRadius: '4px', fontSize: '11px',
            background: `${c.color}22`, color: c.color, fontWeight: 600,
        }}>
            {c.icon} {c.label}
        </span>
    );
};

export const IndicatorsPage: React.FC = () => {
    const [indicators, setIndicators] = useState<Indicator[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [offset, setOffset] = useState(0);
    const [activeTab, setActiveTab] = useState<'basis' | 'validatie'>('basis');
    const limit = 20;

    const {
        selectedIndicator,
        setSelectedIndicator,
        colorSchemas,
        setColorSchemas,
        polariteiten,
        setPolariteiten
    } = useAdminStore();

    const [editForm, setEditForm] = useState<IndicatorUpdate>({});
    const [saving, setSaving] = useState(false);

    // Validatie state
    const [validatieBeschrijving, setValidatieBeschrijving] = useState('');
    const [validatieLoading, setValidatieLoading] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [schemasRes, polRes] = await Promise.all([
                    colorSchemasAPI.getAll(),
                    polariteitenAPI.getAll(),
                ]);
                setColorSchemas(schemasRes.data);
                setPolariteiten(polRes.data);
            } catch (error) {
                console.error('Error fetching reference data:', error);
            }
        };
        fetchData();
    }, [setColorSchemas, setPolariteiten]);

    useEffect(() => {
        const fetchIndicators = async () => {
            setLoading(true);
            try {
                const res = await indicatorenAPI.getAll({ search, limit, offset });
                setIndicators(res.data.indicatoren);
                setTotal(res.data.total);
            } catch (error) {
                console.error('Error fetching indicators:', error);
            } finally {
                setLoading(false);
            }
        };

        const debounce = setTimeout(fetchIndicators, 300);
        return () => clearTimeout(debounce);
    }, [search, offset]);

    const handleSelectIndicator = async (uuid: string) => {
        try {
            const res = await indicatorenAPI.getOne(uuid);
            setSelectedIndicator(res.data);
            setEditForm({
                naam: res.data.naam,
                omschrijving: res.data.omschrijving || '',
                bron: res.data.bron || '',
                eenheid: res.data.eenheid || '',
                polariteit: res.data.polariteit || 'hoger_is_beter',
                color_schema_id: res.data.color_schema_id || 1,
                admin_notes: res.data.admin_notes || '',
            });
            // Validatie tab: pre-fill met de huidige of AI-beschrijving
            setValidatieBeschrijving(
                res.data.ontologische_beschrijving || res.data.beschrijving_ai || ''
            );
        } catch (error) {
            console.error('Error fetching indicator:', error);
        }
    };

    const handleSave = async () => {
        if (!selectedIndicator) return;
        setSaving(true);
        try {
            const res = await indicatorenAPI.update(selectedIndicator.uuid, editForm);
            setSelectedIndicator(res.data);
            const listRes = await indicatorenAPI.getAll({ search, limit, offset });
            setIndicators(listRes.data.indicatoren);
        } catch (error) {
            console.error('Error saving indicator:', error);
        } finally {
            setSaving(false);
        }
    };

    const handleValideer = async (status: OntologieStatus) => {
        if (!selectedIndicator) return;
        setValidatieLoading(true);
        try {
            const res = await indicatorenAPI.valideer(selectedIndicator.uuid, {
                ontologische_beschrijving: validatieBeschrijving,
                ontologie_status: status,
            });
            setSelectedIndicator(res.data);
            const listRes = await indicatorenAPI.getAll({ search, limit, offset });
            setIndicators(listRes.data.indicatoren);
        } catch (error) {
            console.error('Error validating indicator:', error);
        } finally {
            setValidatieLoading(false);
        }
    };

    const handleResetToDraft = async () => {
        if (!selectedIndicator) return;
        setValidatieLoading(true);
        try {
            const res = await indicatorenAPI.valideer(selectedIndicator.uuid, {
                ontologische_beschrijving: selectedIndicator.beschrijving_ai || '',
                ontologie_status: 'draft',
            });
            setSelectedIndicator(res.data);
            setValidatieBeschrijving(res.data.beschrijving_ai || '');
            const listRes = await indicatorenAPI.getAll({ search, limit, offset });
            setIndicators(listRes.data.indicatoren);
        } catch (error) {
            console.error('Error resetting indicator:', error);
        } finally {
            setValidatieLoading(false);
        }
    };

    const totalPages = Math.ceil(total / limit);
    const currentPage = Math.floor(offset / limit) + 1;

    const tabStyle = (active: boolean): React.CSSProperties => ({
        padding: '8px 16px', cursor: 'pointer', fontWeight: active ? 600 : 400,
        borderBottom: active ? '2px solid var(--accent-color, #4A90D9)' : '2px solid transparent',
        color: active ? 'var(--accent-color, #4A90D9)' : 'var(--color-text-secondary)',
        background: 'none', border: 'none', fontSize: '0.875rem',
    });

    return (
        <div style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 140px)' }}>
            {/* Left: List */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    <div style={{ marginBottom: '1rem' }}>
                        <div style={{ position: 'relative' }}>
                            <input
                                type="text"
                                className="form-input"
                                aria-label="Zoek indicatoren"
                                placeholder="Zoeken..."
                                value={search}
                                onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
                                style={{ paddingLeft: '2.5rem' }}
                            />
                            <Search
                                size={18}
                                style={{
                                    position: 'absolute',
                                    left: '0.75rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    color: 'var(--color-text-muted)'
                                }}
                            />
                        </div>
                    </div>

                    <div style={{ flex: 1, overflow: 'auto' }}>
                        {loading ? (
                            <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
                                <Loader2 size={24} className="spin" />
                            </div>
                        ) : (
                            <table className="table">
                                <thead>
                                    <tr>
                                        <th>Naam</th>
                                        <th>Polariteit</th>
                                        <th>Ontologie</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {indicators.map((ind) => (
                                        <tr
                                            key={ind.uuid}
                                            onClick={() => handleSelectIndicator(ind.uuid)}
                                            style={{
                                                cursor: 'pointer',
                                                background: selectedIndicator?.uuid === ind.uuid
                                                    ? 'var(--color-surface-light)'
                                                    : undefined,
                                                opacity: ind.is_actief === false ? 0.6 : 1
                                            }}
                                        >
                                            <td>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                    <span>{ind.naam}</span>
                                                    {ind.is_actief === false && (
                                                        <span style={{ fontSize: '11px', padding: '3px 8px', background: '#ffffff', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '12px', fontWeight: 600, boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }}>
                                                            ● Inactief (Gemerged)
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                            <td>
                                                <span className={`badge ${ind.polariteit === 'lager_is_beter' ? 'badge-negative' : 'badge-positive'}`}>
                                                    {polariteiten.find((p) => p.code === ind.polariteit)?.naam ?? ind.polariteit ?? ind.score_type}
                                                </span>
                                            </td>
                                            <td>
                                                <OntologieStatusBadge status={ind.ontologie_status} />
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>

                    {/* Pagination */}
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginTop: '1rem',
                        paddingTop: '1rem',
                        borderTop: '1px solid var(--color-border)'
                    }}>
                        <span style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                            {total} indicatoren
                        </span>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setOffset(Math.max(0, offset - limit))}
                                disabled={offset === 0}
                                aria-label="Vorige pagina"
                            >
                                <ChevronLeft size={16} />
                            </button>
                            <span style={{ fontSize: '0.875rem' }}>
                                {currentPage} / {totalPages}
                            </span>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setOffset(offset + limit)}
                                disabled={offset + limit >= total}
                                aria-label="Volgende pagina"
                            >
                                <ChevronRight size={16} />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right: Editor with Tabs */}
            <div style={{ width: '450px' }}>
                <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                    {selectedIndicator ? (
                        <>
                            <div className="card-header" style={{ flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                    <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.95rem', margin: 0 }}>
                                        <Edit size={16} />
                                        {selectedIndicator.naam}
                                    </h3>
                                    {selectedIndicator.is_actief === false && (
                                        <span style={{ fontSize: '12px', padding: '4px 10px', background: '#ef4444', color: '#ffffff', borderRadius: '12px', fontWeight: 600, boxShadow: '0 2px 4px rgba(239, 68, 68, 0.2)' }}>
                                            ● Inactief (Gemerged)
                                        </span>
                                    )}
                                </div>
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => setSelectedIndicator(null)}
                                    aria-label="Details sluiten"
                                    title="Sluiten"
                                >
                                    <X size={16} />
                                </button>
                            </div>

                            {/* Tab Bar */}
                            <div style={{ display: 'flex', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
                                <button style={tabStyle(activeTab === 'basis')} onClick={() => setActiveTab('basis')}>
                                    Basis Info
                                </button>
                                <button style={tabStyle(activeTab === 'validatie')} onClick={() => setActiveTab('validatie')}>
                                    Ontologie Validatie {' '}
                                    <OntologieStatusBadge status={selectedIndicator.ontologie_status} />
                                </button>
                            </div>

                            <div style={{ flex: 1, overflow: 'auto', padding: '0.5rem 0' }}>
                                {/* ── TAB: Basis Info ── */}
                                {activeTab === 'basis' && (
                                    <>
                                        <div className="form-group">
                                            <label htmlFor="indicators-naam" className="form-label">Naam</label>
                                            <input id="indicators-naam" type="text" className="form-input" value={editForm.naam || ''} onChange={(e) => setEditForm({ ...editForm, naam: e.target.value })} />
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="indicators-omschrijving" className="form-label">Omschrijving</label>
                                            <textarea id="indicators-omschrijving" className="form-textarea" value={editForm.omschrijving || ''} onChange={(e) => setEditForm({ ...editForm, omschrijving: e.target.value })} />
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="indicators-polariteit" className="form-label">Polariteit</label>
                                            <select id="indicators-polariteit" className="form-select" value={editForm.polariteit || 'hoger_is_beter'} onChange={(e) => setEditForm({ ...editForm, polariteit: e.target.value })}>
                                                {polariteiten.map((p) => (<option key={p.code} value={p.code}>{p.naam}: {p.beschrijving.toLowerCase()}</option>))}
                                            </select>
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="indicators-kleurschema" className="form-label">Kleurschema</label>
                                            <select id="indicators-kleurschema" className="form-select" value={editForm.color_schema_id || 1} onChange={(e) => setEditForm({ ...editForm, color_schema_id: Number(e.target.value) })}>
                                                {colorSchemas.map((cs) => (<option key={cs.id} value={cs.id}>{cs.naam}</option>))}
                                            </select>
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="indicators-bron" className="form-label">Bron</label>
                                            <input id="indicators-bron" type="text" className="form-input" value={editForm.bron || ''} onChange={(e) => setEditForm({ ...editForm, bron: e.target.value })} />
                                        </div>
                                        {/* Data Lineage Info (Sprint 22 Track C) */}
                                        <div style={{ padding: '8px 12px', background: 'var(--color-surface-light, #1E293B)', borderRadius: '6px', marginBottom: '12px', fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: '4px', border: '1px solid var(--color-border, #334155)' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <span style={{ color: 'var(--color-text-secondary)' }}>Lineage Systeem:</span>
                                                <span style={{ fontWeight: 600, color: '#38bdf8' }}>{selectedIndicator.bron_systeem_api || 'LOKAAL'}</span>
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <span style={{ color: 'var(--color-text-secondary)' }}>Dataset / Tabel:</span>
                                                <span style={{ fontFamily: 'monospace' }}>{selectedIndicator.bron_tabel_referentie || '-'}</span>
                                            </div>
                                            {selectedIndicator.laatste_check_datum && (
                                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                    <span style={{ color: 'var(--color-text-secondary)' }}>Laatste Controle:</span>
                                                    <span>{new Date(selectedIndicator.laatste_check_datum).toLocaleDateString('nl-NL')}</span>
                                                </div>
                                            )}
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="indicators-eenheid" className="form-label">Eenheid</label>
                                            <input id="indicators-eenheid" type="text" className="form-input" value={editForm.eenheid || ''} onChange={(e) => setEditForm({ ...editForm, eenheid: e.target.value })} />
                                        </div>
                                        <div className="form-group">
                                            <label htmlFor="indicators-admin-notities" className="form-label">Admin Notities</label>
                                            <textarea id="indicators-admin-notities" className="form-textarea" value={editForm.admin_notes || ''} onChange={(e) => setEditForm({ ...editForm, admin_notes: e.target.value })} placeholder="Interne notities..." />
                                        </div>
                                        <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={handleSave} disabled={saving}>
                                            {saving ? (<><Loader2 size={16} className="spin" /> Opslaan...</>) : (<><Save size={16} /> Opslaan</>)}
                                        </button>
                                    </>
                                )}

                                {/* ── TAB: Ontologie Validatie ── */}
                                {activeTab === 'validatie' && (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                        {/* Status bar */}
                                        <div style={{
                                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                            padding: '8px 12px', borderRadius: '6px',
                                            background: 'var(--color-surface-light, #1E293B)',
                                        }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Status:</span>
                                                <OntologieStatusBadge status={selectedIndicator.ontologie_status} />
                                            </div>
                                            {selectedIndicator.gevalideerd_op && (
                                                <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                    <Clock size={12} />
                                                    {new Date(selectedIndicator.gevalideerd_op).toLocaleDateString('nl-NL')}
                                                    {selectedIndicator.gevalideerd_door_naam && ` door ${selectedIndicator.gevalideerd_door_naam}`}
                                                </span>
                                            )}
                                        </div>

                                        {/* AI Beschrijving (read-only) */}
                                        <div className="form-group">
                                            <div className="form-label" id="indicators-ai-beschrijving-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                <Bot size={14} aria-hidden="true" /> AI-gegenereerde beschrijving
                                            </div>
                                            <div aria-labelledby="indicators-ai-beschrijving-label" role="region" style={{
                                                padding: '10px 12px', borderRadius: '6px',
                                                background: 'var(--color-surface-light, #1E293B)',
                                                border: '1px solid var(--color-border)',
                                                fontSize: '0.85rem', color: 'var(--color-text-secondary)',
                                                minHeight: '80px', lineHeight: '1.5', whiteSpace: 'pre-wrap',
                                            }}>
                                                {selectedIndicator.beschrijving_ai || (
                                                    <em style={{ color: 'var(--color-text-muted)' }}>Geen AI-beschrijving beschikbaar</em>
                                                )}
                                            </div>
                                        </div>

                                        {/* Menselijke validatie (editable) */}
                                        <div className="form-group">
                                            <label htmlFor="indicators-gevalideerde-beschrijving" className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                <CheckCircle size={14} /> Gevalideerde beschrijving
                                            </label>
                                            <textarea id="indicators-gevalideerde-beschrijving"
                                                className="form-textarea"
                                                value={validatieBeschrijving}
                                                onChange={(e) => setValidatieBeschrijving(e.target.value)}
                                                placeholder="Bewerk of bevestig de beschrijving..."
                                                style={{ minHeight: '120px', lineHeight: '1.5' }}
                                            />
                                        </div>

                                        {/* Action buttons */}
                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                            <button
                                                className="btn btn-primary"
                                                style={{ flex: 1, justifyContent: 'center' }}
                                                onClick={() => handleValideer('goedgekeurd_mens')}
                                                disabled={validatieLoading || !validatieBeschrijving.trim()}
                                            >
                                                {validatieLoading ? <Loader2 size={14} className="spin" /> : <CheckCircle size={14} />}
                                                {' '}Goedkeuren
                                            </button>
                                            <button
                                                className="btn btn-secondary"
                                                style={{ justifyContent: 'center' }}
                                                onClick={handleResetToDraft}
                                                disabled={validatieLoading}
                                                title="Terugzetten naar AI-beschrijving"
                                            >
                                                <Bot size={14} /> Reset
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <div style={{
                            display: 'flex', flexDirection: 'column', alignItems: 'center',
                            justifyContent: 'center', height: '100%', color: 'var(--color-text-muted)'
                        }}>
                            <Edit size={48} strokeWidth={1} />
                            <p style={{ marginTop: '1rem' }}>Selecteer een indicator om te bewerken</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
