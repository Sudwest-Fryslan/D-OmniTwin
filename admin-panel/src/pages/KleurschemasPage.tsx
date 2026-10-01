import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { visualisatieAPI } from '../services/api';
import { useDialogFocus } from '../hooks/useDialogFocus';
import {
    Palette,
    Plus,
    Edit3,
    Trash2,
    Save,
    X,
    Eye,
    BarChart2,
    Layers,
    CheckCircle,
    AlertCircle
} from 'lucide-react';

// ============================================================================
// Types
// ============================================================================
interface ColorPalette {
    id: number;
    naam: string;
    beschrijving: string | null;
    colors: {
        min: string;
        mid: string;
        max: string;
    };
    palette_type: string;
    classificatie: string;
    klassen: number;
    nodata_kleur: string;
    is_actief: boolean;
}

interface VisualisatieProfiel {
    id: number;
    naam: string;
    beschrijving: string | null;
    indicator_pattern: string | null;
    color_schema_id: number | null;
    schema_naam: string | null;
    classificatie_override: string | null;
    klassen_override: number | null;
    midpoint_waarde: number | null;
    is_actief: boolean;
}

// ============================================================================
// Color Gradient Preview Component
// ============================================================================
const ColorGradient: React.FC<{
    colors: { min: string; mid: string; max: string };
    nodata?: string;
    klassen?: number;
    size?: 'sm' | 'md' | 'lg';
}> = ({ colors, nodata, klassen = 5, size = 'md' }) => {
    const steps = generateColorSteps(colors, klassen);
    const height = size === 'sm' ? 16 : size === 'md' ? 24 : 36;

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <div
                style={{
                    display: 'flex',
                    borderRadius: '4px',
                    overflow: 'hidden',
                    border: '1px solid var(--color-border)',
                }}
            >
                {steps.map((color, i) => (
                    <div
                        key={i}
                        style={{
                            width: size === 'lg' ? 40 : 28,
                            height,
                            backgroundColor: color,
                        }}
                        title={color}
                    />
                ))}
            </div>
            {nodata && (
                <div
                    style={{
                        width: height,
                        height,
                        backgroundColor: nodata,
                        borderRadius: '4px',
                        border: '1px solid var(--color-border)',
                        marginLeft: '8px',
                    }}
                    title={`No Data: ${nodata}`}
                />
            )}
        </div>
    );
};

// Generate interpolated color steps
function generateColorSteps(
    colors: { min: string; mid: string; max: string },
    steps: number
): string[] {
    const result: string[] = [];
    const halfSteps = Math.ceil(steps / 2);

    for (let i = 0; i < halfSteps; i++) {
        const t = i / (halfSteps - 1 || 1);
        result.push(interpolateColor(colors.min, colors.mid, t));
    }
    for (let i = 1; i < steps - halfSteps + 1; i++) {
        const t = i / (steps - halfSteps || 1);
        result.push(interpolateColor(colors.mid, colors.max, t));
    }
    return result;
}

function interpolateColor(c1: string, c2: string, t: number): string {
    const r1 = parseInt(c1.slice(1, 3), 16);
    const g1 = parseInt(c1.slice(3, 5), 16);
    const b1 = parseInt(c1.slice(5, 7), 16);
    const r2 = parseInt(c2.slice(1, 3), 16);
    const g2 = parseInt(c2.slice(3, 5), 16);
    const b2 = parseInt(c2.slice(5, 7), 16);

    const r = Math.round(r1 + (r2 - r1) * t);
    const g = Math.round(g1 + (g2 - g1) * t);
    const b = Math.round(b1 + (b2 - b1) * t);

    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

// ============================================================================
// Palette Type Badge
// ============================================================================
const TypeBadge: React.FC<{ type: string }> = ({ type }) => {
    const styles: Record<string, { bg: string; color: string }> = {
        sequential: { bg: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6' },
        diverging: { bg: 'rgba(234, 179, 8, 0.15)', color: '#eab308' },
        qualitative: { bg: 'rgba(168, 85, 247, 0.15)', color: '#a855f7' },
    };
    const s = styles[type] || styles.sequential;

    return (
        <span
            style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '0.75rem',
                fontWeight: 500,
                background: s.bg,
                color: s.color,
            }}
        >
            {type}
        </span>
    );
};

// ============================================================================
// Palette Editor Modal
// ============================================================================
const PaletteEditor: React.FC<{
    palette: Partial<ColorPalette> | null;
    onSave: (data: any) => void;
    onClose: () => void;
    isLoading?: boolean;
}> = ({ palette, onSave, onClose, isLoading }) => {
    const [form, setForm] = useState({
        naam: palette?.naam || '',
        beschrijving: palette?.beschrijving || '',
        colors: {
            min: palette?.colors?.min || '#deebf7',
            mid: palette?.colors?.mid || '#4292c6',
            max: palette?.colors?.max || '#08306b',
        },
        palette_type: palette?.palette_type || 'sequential',
        classificatie: palette?.classificatie || 'quantile',
        klassen: palette?.klassen || 5,
        nodata_kleur: palette?.nodata_kleur || '#d1d5db',
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSave(form);
    };
    const dialogRef = useDialogFocus<HTMLDivElement>(true, onClose);

    return (
        <div
            style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(0,0,0,0.6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
            }}
            onClick={onClose}
        >
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="palette-editor-titel"
                className="card"
                style={{ width: '520px', maxHeight: '80vh', overflowY: 'auto' }}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="card-header">
                    <h3 className="card-title" id="palette-editor-titel">
                        {palette?.id ? 'Palette Bewerken' : 'Nieuw Palette'}
                    </h3>
                    <button type="button" className="btn btn-secondary" onClick={onClose} aria-label="Sluiten" title="Sluiten">
                        <X size={16} />
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="kleurschemas-naam" className="form-label">Naam</label>
                        <input id="kleurschemas-naam"
                            className="form-input"
                            value={form.naam}
                            onChange={(e) => setForm({ ...form, naam: e.target.value })}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="kleurschemas-beschrijving" className="form-label">Beschrijving</label>
                        <input id="kleurschemas-beschrijving"
                            className="form-input"
                            value={form.beschrijving}
                            onChange={(e) => setForm({ ...form, beschrijving: e.target.value })}
                        />
                    </div>

                    {/* Color pickers */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                        <div className="form-group">
                            <label htmlFor="kleurschemas-min-kleur" className="form-label">Min kleur</label>
                            <input id="kleurschemas-min-kleur"
                                type="color"
                                value={form.colors.min}
                                onChange={(e) =>
                                    setForm({ ...form, colors: { ...form.colors, min: e.target.value } })
                                }
                                style={{ width: '100%', height: '36px', cursor: 'pointer', border: 'none', borderRadius: '4px' }}
                            />
                            <small style={{ color: 'var(--color-text-muted)', fontSize: '0.7rem' }}>{form.colors.min}</small>
                        </div>
                        <div className="form-group">
                            <label htmlFor="kleurschemas-mid-kleur" className="form-label">Mid kleur</label>
                            <input id="kleurschemas-mid-kleur"
                                type="color"
                                value={form.colors.mid}
                                onChange={(e) =>
                                    setForm({ ...form, colors: { ...form.colors, mid: e.target.value } })
                                }
                                style={{ width: '100%', height: '36px', cursor: 'pointer', border: 'none', borderRadius: '4px' }}
                            />
                            <small style={{ color: 'var(--color-text-muted)', fontSize: '0.7rem' }}>{form.colors.mid}</small>
                        </div>
                        <div className="form-group">
                            <label htmlFor="kleurschemas-max-kleur" className="form-label">Max kleur</label>
                            <input id="kleurschemas-max-kleur"
                                type="color"
                                value={form.colors.max}
                                onChange={(e) =>
                                    setForm({ ...form, colors: { ...form.colors, max: e.target.value } })
                                }
                                style={{ width: '100%', height: '36px', cursor: 'pointer', border: 'none', borderRadius: '4px' }}
                            />
                            <small style={{ color: 'var(--color-text-muted)', fontSize: '0.7rem' }}>{form.colors.max}</small>
                        </div>
                        <div className="form-group">
                            <label htmlFor="kleurschemas-no-data" className="form-label">No Data</label>
                            <input id="kleurschemas-no-data"
                                type="color"
                                value={form.nodata_kleur}
                                onChange={(e) => setForm({ ...form, nodata_kleur: e.target.value })}
                                style={{ width: '100%', height: '36px', cursor: 'pointer', border: 'none', borderRadius: '4px' }}
                            />
                            <small style={{ color: 'var(--color-text-muted)', fontSize: '0.7rem' }}>{form.nodata_kleur}</small>
                        </div>
                    </div>

                    {/* Live preview */}
                    <div className="form-group">
                        <div className="form-label">Preview ({form.klassen} klassen)</div>
                        <ColorGradient colors={form.colors} nodata={form.nodata_kleur} klassen={form.klassen} size="lg" />
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                        <div className="form-group">
                            <label htmlFor="kleurschemas-type" className="form-label">Type</label>
                            <select id="kleurschemas-type"
                                className="form-select"
                                value={form.palette_type}
                                onChange={(e) => setForm({ ...form, palette_type: e.target.value })}
                            >
                                <option value="sequential">Sequential</option>
                                <option value="diverging">Diverging</option>
                                <option value="qualitative">Qualitative</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label htmlFor="kleurschemas-classificatie" className="form-label">Classificatie</label>
                            <select id="kleurschemas-classificatie"
                                className="form-select"
                                value={form.classificatie}
                                onChange={(e) => setForm({ ...form, classificatie: e.target.value })}
                            >
                                <option value="quantile">Quantile</option>
                                <option value="jenks">Natural Breaks (Jenks)</option>
                                <option value="equal_interval">Equal Interval</option>
                                <option value="diverging_midpoint">Diverging Midpoint</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label htmlFor="kleurschemas-klassen" className="form-label">Klassen (max 7)</label>
                            <input id="kleurschemas-klassen"
                                type="number"
                                className="form-input"
                                min={3}
                                max={7}
                                value={form.klassen}
                                onChange={(e) => setForm({ ...form, klassen: parseInt(e.target.value) || 5 })}
                            />
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '16px' }}>
                        <button type="button" className="btn btn-secondary" onClick={onClose}>
                            Annuleren
                        </button>
                        <button type="submit" className="btn btn-primary" disabled={isLoading}>
                            <Save size={16} />
                            {isLoading ? 'Opslaan...' : 'Opslaan'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// ============================================================================
// Profile Editor Modal
// ============================================================================
const ProfielEditor: React.FC<{
    profiel: Partial<VisualisatieProfiel> | null;
    paletten: ColorPalette[];
    onSave: (data: any) => void;
    onClose: () => void;
    isLoading?: boolean;
}> = ({ profiel, paletten, onSave, onClose, isLoading }) => {
    const [form, setForm] = useState({
        naam: profiel?.naam || '',
        beschrijving: profiel?.beschrijving || '',
        indicator_pattern: profiel?.indicator_pattern || '',
        color_schema_id: profiel?.color_schema_id || (paletten[0]?.id ?? null),
        classificatie_override: profiel?.classificatie_override || '',
        klassen_override: profiel?.klassen_override || null as number | null,
        midpoint_waarde: profiel?.midpoint_waarde || null as number | null,
    });

    const selectedPalette = paletten.find(p => p.id === form.color_schema_id);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSave({
            ...form,
            classificatie_override: form.classificatie_override || null,
            klassen_override: form.klassen_override || null,
            midpoint_waarde: form.midpoint_waarde || null,
        });
    };
    const dialogRef = useDialogFocus<HTMLDivElement>(true, onClose);

    return (
        <div
            style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(0,0,0,0.6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
            }}
            onClick={onClose}
        >
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                aria-labelledby="profiel-editor-titel"
                className="card"
                style={{ width: '520px', maxHeight: '80vh', overflowY: 'auto' }}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="card-header">
                    <h3 className="card-title" id="profiel-editor-titel">
                        {profiel?.id ? 'Profiel Bewerken' : 'Nieuw Profiel'}
                    </h3>
                    <button type="button" className="btn btn-secondary" onClick={onClose} aria-label="Sluiten" title="Sluiten">
                        <X size={16} />
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="kleurschemas-regel-naam" className="form-label">Naam</label>
                        <input id="kleurschemas-regel-naam"
                            className="form-input"
                            value={form.naam}
                            onChange={(e) => setForm({ ...form, naam: e.target.value })}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="kleurschemas-regel-beschrijving" className="form-label">Beschrijving</label>
                        <input id="kleurschemas-regel-beschrijving"
                            className="form-input"
                            value={form.beschrijving}
                            onChange={(e) => setForm({ ...form, beschrijving: e.target.value })}
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="kleurschemas-indicator-pattern" className="form-label">Indicator Pattern (SQL LIKE)</label>
                        <input id="kleurschemas-indicator-pattern"
                            className="form-input"
                            value={form.indicator_pattern}
                            onChange={(e) => setForm({ ...form, indicator_pattern: e.target.value })}
                            placeholder="%inwoner%, %dichtheid%"
                        />
                        <small style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
                            Gebruik % als wildcard. Matcht de indicator naam.
                        </small>
                    </div>

                    <div className="form-group">
                        <label htmlFor="kleurschemas-kleurschema" className="form-label">Kleurschema</label>
                        <select id="kleurschemas-kleurschema"
                            className="form-select"
                            value={form.color_schema_id ?? ''}
                            onChange={(e) => setForm({ ...form, color_schema_id: parseInt(e.target.value) })}
                        >
                            {paletten.map((p) => (
                                <option key={p.id} value={p.id}>
                                    {p.naam} ({p.palette_type})
                                </option>
                            ))}
                        </select>
                        {selectedPalette && (
                            <div style={{ marginTop: '8px' }}>
                                <ColorGradient colors={selectedPalette.colors} nodata={selectedPalette.nodata_kleur} klassen={selectedPalette.klassen} />
                            </div>
                        )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                        <div className="form-group">
                            <label htmlFor="kleurschemas-classificatie-override" className="form-label">Classificatie Override</label>
                            <select id="kleurschemas-classificatie-override"
                                className="form-select"
                                value={form.classificatie_override}
                                onChange={(e) => setForm({ ...form, classificatie_override: e.target.value })}
                            >
                                <option value="">Gebruik schema default</option>
                                <option value="quantile">Quantile</option>
                                <option value="jenks">Jenks</option>
                                <option value="equal_interval">Equal Interval</option>
                                <option value="diverging_midpoint">Diverging Midpoint</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label htmlFor="kleurschemas-klassen-override" className="form-label">Klassen Override</label>
                            <input id="kleurschemas-klassen-override"
                                type="number"
                                className="form-input"
                                min={3}
                                max={7}
                                value={form.klassen_override ?? ''}
                                onChange={(e) =>
                                    setForm({ ...form, klassen_override: e.target.value ? parseInt(e.target.value) : null })
                                }
                                placeholder="Gebruik default"
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="kleurschemas-midpoint-waarde" className="form-label">Midpoint Waarde</label>
                            <input id="kleurschemas-midpoint-waarde"
                                type="number"
                                className="form-input"
                                value={form.midpoint_waarde ?? ''}
                                onChange={(e) =>
                                    setForm({ ...form, midpoint_waarde: e.target.value ? parseFloat(e.target.value) : null })
                                }
                                placeholder="Bijv. 50 voor index"
                            />
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '16px' }}>
                        <button type="button" className="btn btn-secondary" onClick={onClose}>
                            Annuleren
                        </button>
                        <button type="submit" className="btn btn-primary" disabled={isLoading}>
                            <Save size={16} />
                            {isLoading ? 'Opslaan...' : 'Opslaan'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// ============================================================================
// Main Page Component
// ============================================================================
export const KleurschemasPage: React.FC = () => {
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState<'paletten' | 'profielen'>('paletten');
    const [editingPalette, setEditingPalette] = useState<Partial<ColorPalette> | null>(null);
    const [editingProfiel, setEditingProfiel] = useState<Partial<VisualisatieProfiel> | null>(null);
    const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

    // Queries
    const { data: palettenData, isLoading: loadingPaletten } = useQuery({
        queryKey: ['paletten'],
        queryFn: () => visualisatieAPI.getPaletten().then(r => r.data),
    });

    const { data: profielenData, isLoading: loadingProfielen } = useQuery({
        queryKey: ['profielen'],
        queryFn: () => visualisatieAPI.getProfielen().then(r => r.data),
    });

    // Mutations
    const createPalette = useMutation({
        mutationFn: (data: any) => visualisatieAPI.createPalette(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['paletten'] });
            setEditingPalette(null);
            showNotification('success', 'Palette aangemaakt! 🎨');
        },
        onError: (err: any) => showNotification('error', `Fout: ${err.response?.data?.detail || err.message}`),
    });

    const updatePalette = useMutation({
        mutationFn: ({ id, data }: { id: number; data: any }) => visualisatieAPI.updatePalette(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['paletten'] });
            setEditingPalette(null);
            showNotification('success', 'Palette bijgewerkt! ✅');
        },
        onError: (err: any) => showNotification('error', `Fout: ${err.response?.data?.detail || err.message}`),
    });

    const createProfiel = useMutation({
        mutationFn: (data: any) => visualisatieAPI.createProfiel(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['profielen'] });
            setEditingProfiel(null);
            showNotification('success', 'Profiel aangemaakt! ✅');
        },
        onError: (err: any) => showNotification('error', `Fout: ${err.response?.data?.detail || err.message}`),
    });

    const updateProfiel = useMutation({
        mutationFn: ({ id, data }: { id: number; data: any }) => visualisatieAPI.updateProfiel(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['profielen'] });
            setEditingProfiel(null);
            showNotification('success', 'Profiel bijgewerkt! ✅');
        },
        onError: (err: any) => showNotification('error', `Fout: ${err.response?.data?.detail || err.message}`),
    });

    const deleteProfiel = useMutation({
        mutationFn: (id: number) => visualisatieAPI.deleteProfiel(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['profielen'] });
            showNotification('success', 'Profiel verwijderd');
        },
        onError: (err: any) => showNotification('error', `Fout: ${err.response?.data?.detail || err.message}`),
    });

    const showNotification = (type: 'success' | 'error', message: string) => {
        setNotification({ type, message });
        setTimeout(() => setNotification(null), 3000);
    };

    const handleSavePalette = (data: any) => {
        if (editingPalette?.id) {
            updatePalette.mutate({ id: editingPalette.id, data });
        } else {
            createPalette.mutate(data);
        }
    };

    const handleSaveProfiel = (data: any) => {
        if (editingProfiel?.id) {
            updateProfiel.mutate({ id: editingProfiel.id, data });
        } else {
            createProfiel.mutate(data);
        }
    };

    const paletten: ColorPalette[] = palettenData?.paletten || [];
    const profielen: VisualisatieProfiel[] = profielenData?.profielen || [];

    return (
        <div>
            {/* Notification */}
            {notification && (
                <div
                    role="status"
                    style={{
                        position: 'fixed',
                        top: '20px',
                        right: '20px',
                        padding: '12px 20px',
                        borderRadius: '8px',
                        background: notification.type === 'success' ? 'var(--color-success)' : 'var(--color-error)',
                        color: 'white',
                        fontWeight: 500,
                        zIndex: 2000,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        boxShadow: 'var(--shadow-lg)',
                    }}
                >
                    {notification.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
                    {notification.message}
                </div>
            )}

            {/* Stats Bar */}
            <div className="stats-grid" style={{ marginBottom: '1rem' }}>
                <div className="stat-card">
                    <div className="stat-value">{paletten.length}</div>
                    <div className="stat-label">Kleurpaletten</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{profielen.length}</div>
                    <div className="stat-label">Visualisatie Profielen</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{profielen.filter(p => p.is_actief).length}</div>
                    <div className="stat-label">Actieve Profielen</div>
                </div>
            </div>

            {/* Tab Switcher */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '1rem' }}>
                <button
                    className={`btn ${activeTab === 'paletten' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('paletten')}
                >
                    <Palette size={16} />
                    Kleurpaletten
                </button>
                <button
                    className={`btn ${activeTab === 'profielen' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveTab('profielen')}
                >
                    <Layers size={16} />
                    Visualisatie Profielen
                </button>
            </div>

            {/* Paletten Tab */}
            {activeTab === 'paletten' && (
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Kleurpaletten</h3>
                        <button className="btn btn-primary" onClick={() => setEditingPalette({})}>
                            <Plus size={16} />
                            Nieuw Palette
                        </button>
                    </div>

                    {loadingPaletten ? (
                        <p style={{ color: 'var(--color-text-secondary)' }}>Laden...</p>
                    ) : (
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Naam</th>
                                    <th>Type</th>
                                    <th>Preview</th>
                                    <th>Classificatie</th>
                                    <th>Klassen</th>
                                    <th>Status</th>
                                    <th>Acties</th>
                                </tr>
                            </thead>
                            <tbody>
                                {paletten.map((p) => (
                                    <tr key={p.id}>
                                        <td style={{ color: 'var(--color-text-muted)' }}>{p.id}</td>
                                        <td>
                                            <div>
                                                <strong>{p.naam}</strong>
                                                {p.beschrijving && (
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                                        {p.beschrijving}
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                        <td><TypeBadge type={p.palette_type} /></td>
                                        <td>
                                            <ColorGradient colors={p.colors} nodata={p.nodata_kleur} klassen={p.klassen} />
                                        </td>
                                        <td style={{ fontSize: '0.875rem' }}>{p.classificatie}</td>
                                        <td>{p.klassen}</td>
                                        <td>
                                            <span className={`badge ${p.is_actief ? 'badge-positive' : 'badge-negative'}`}>
                                                {p.is_actief ? 'Actief' : 'Inactief'}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                className="btn btn-secondary"
                                                style={{ padding: '4px 8px' }}
                                                onClick={() => setEditingPalette(p)}
                                                aria-label={`Palette ${p.naam} bewerken`}
                                                title="Bewerken"
                                            >
                                                <Edit3 size={14} />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            {/* Profielen Tab */}
            {activeTab === 'profielen' && (
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Visualisatie Profielen</h3>
                        <button className="btn btn-primary" onClick={() => setEditingProfiel({})}>
                            <Plus size={16} />
                            Nieuw Profiel
                        </button>
                    </div>

                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem', marginBottom: '1rem' }}>
                        Profielen koppelen indicatoren automatisch aan een kleurschema via pattern matching.
                    </p>

                    {loadingProfielen ? (
                        <p style={{ color: 'var(--color-text-secondary)' }}>Laden...</p>
                    ) : (
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Naam</th>
                                    <th>Pattern</th>
                                    <th>Kleurschema</th>
                                    <th>Classificatie</th>
                                    <th>Klassen</th>
                                    <th>Midpoint</th>
                                    <th>Status</th>
                                    <th>Acties</th>
                                </tr>
                            </thead>
                            <tbody>
                                {profielen.map((p) => {
                                    const linkedPalette = paletten.find(pal => pal.id === p.color_schema_id);
                                    return (
                                        <tr key={p.id}>
                                            <td>
                                                <strong>{p.naam}</strong>
                                                {p.beschrijving && (
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                                                        {p.beschrijving}
                                                    </div>
                                                )}
                                            </td>
                                            <td>
                                                <code style={{
                                                    background: 'var(--color-surface-light)',
                                                    padding: '2px 6px',
                                                    borderRadius: '3px',
                                                    fontSize: '0.8rem'
                                                }}>
                                                    {p.indicator_pattern || '—'}
                                                </code>
                                            </td>
                                            <td>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                    {linkedPalette && (
                                                        <ColorGradient colors={linkedPalette.colors} klassen={linkedPalette.klassen} size="sm" />
                                                    )}
                                                    <span style={{ fontSize: '0.8rem' }}>{p.schema_naam || '—'}</span>
                                                </div>
                                            </td>
                                            <td style={{ fontSize: '0.85rem' }}>{p.classificatie_override || '—'}</td>
                                            <td>{p.klassen_override || '—'}</td>
                                            <td>{p.midpoint_waarde ?? '—'}</td>
                                            <td>
                                                <span className={`badge ${p.is_actief ? 'badge-positive' : 'badge-negative'}`}>
                                                    {p.is_actief ? 'Actief' : 'Inactief'}
                                                </span>
                                            </td>
                                            <td>
                                                <div style={{ display: 'flex', gap: '4px' }}>
                                                    <button
                                                        className="btn btn-secondary"
                                                        style={{ padding: '4px 8px' }}
                                                        onClick={() => setEditingProfiel(p)}
                                                        aria-label={`Profiel ${p.naam} bewerken`}
                                                        title="Bewerken"
                                                    >
                                                        <Edit3 size={14} />
                                                    </button>
                                                    <button
                                                        className="btn btn-action"
                                                        style={{ padding: '4px 8px' }}
                                                        onClick={() => {
                                                            if (window.confirm(`Profiel "${p.naam}" verwijderen?`)) {
                                                                deleteProfiel.mutate(p.id);
                                                            }
                                                        }}
                                                        aria-label={`Profiel ${p.naam} verwijderen`}
                                                        title="Verwijderen"
                                                    >
                                                        <Trash2 size={14} />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    )}
                </div>
            )}

            {/* Modals */}
            {editingPalette !== null && (
                <PaletteEditor
                    palette={editingPalette}
                    onSave={handleSavePalette}
                    onClose={() => setEditingPalette(null)}
                    isLoading={createPalette.isPending || updatePalette.isPending}
                />
            )}

            {editingProfiel !== null && (
                <ProfielEditor
                    profiel={editingProfiel}
                    paletten={paletten}
                    onSave={handleSaveProfiel}
                    onClose={() => setEditingProfiel(null)}
                    isLoading={createProfiel.isPending || updateProfiel.isPending}
                />
            )}
        </div>
    );
};
