import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { externeKaartlagenAPI } from '../services/api';
import {
    ExterneKaartlaag,
    ExterneKaartlaagCreate,
    ExterneKaartlaagKoppelOpties,
    KaartlaagVolgordeItem,
    LokaalBestand,
} from '../types';
import { Plus, Pencil, Trash2, Globe, Eye, EyeOff, Upload, HardDrive, ArrowUp, ArrowDown, X } from 'lucide-react';

// ─── Default waarden voor nieuw formulier ──────────────────────────────────
const EMPTY_FORM: ExterneKaartlaagCreate = {
    naam: '',
    beschrijving: '',
    laag_type: 'selectie',
    bron_type: 'WFS',
    url: '',
    typename: '',
    srsname: 'EPSG:28992',
    versie: '2.0.0',
    filter_type: 'provincie',
    filter_waarde: 'Fryslân',
    koppel_veld: null,
    kleur_lijn: '#8B5CF6',
    kleur_fill: '#8B5CF6',
    opacity: 0.15,
    actief: true,
    volgorde: 0,
    groep_naam: null,
    groep_volgorde: 0,
    kompas_thema_naam: null,
    gekoppelde_indicatoren: [],
};

const EMPTY_KOPPEL_OPTIES: ExterneKaartlaagKoppelOpties = {
    themas: [],
    groepen: [],
    indicatoren: [],
};

export interface KaartlaagGroep {
    naam: string;
    isOverig: boolean;
    volgorde: number;
    lagen: ExterneKaartlaag[];
}

export function groepeerKaartlagen(lagen: ExterneKaartlaag[]): KaartlaagGroep[] {
    const groepen = new Map<string, KaartlaagGroep>();
    lagen.forEach(laag => {
        const explicieteGroep = (laag.groep_naam || '').trim();
        const themaGroep = (laag.kompas_thema_naam || '').trim();
        const isOverig = !explicieteGroep && !themaGroep;
        const groepsnaam = explicieteGroep || themaGroep || 'Overige kaartlagen';
        const gv = laag.groep_volgorde ?? 0;

        if (!groepen.has(groepsnaam)) {
            groepen.set(groepsnaam, { naam: groepsnaam, isOverig, volgorde: gv, lagen: [] });
        }
        const g = groepen.get(groepsnaam)!;
        if (gv < g.volgorde) g.volgorde = gv;
        g.lagen.push(laag);
    });

    const resultaat = Array.from(groepen.values()).sort((a, b) => {
        if (a.isOverig !== b.isOverig) return a.isOverig ? 1 : -1;
        if (a.volgorde !== b.volgorde) return a.volgorde - b.volgorde;
        return a.naam.localeCompare(b.naam, 'nl');
    });

    resultaat.forEach(g => {
        g.lagen.sort((a, b) => {
            if (a.volgorde !== b.volgorde) return a.volgorde - b.volgorde;
            return a.naam.localeCompare(b.naam, 'nl');
        });
    });

    return resultaat;
}

function foutMelding(err: unknown, fallback: string): string {
    const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
    return typeof detail === 'string' && detail ? detail : fallback;
}

export const ExterneKaartlagenPage: React.FC = () => {
    const [lagen, setLagen] = useState<ExterneKaartlaag[]>([]);
    const [koppelOpties, setKoppelOpties] = useState<ExterneKaartlaagKoppelOpties>(EMPTY_KOPPEL_OPTIES);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);

    // Formulier state
    const [showForm, setShowForm] = useState(false);
    const [editId, setEditId] = useState<number | null>(null);
    const [form, setForm] = useState<ExterneKaartlaagCreate>({ ...EMPTY_FORM });
    const [indicatorZoek, setIndicatorZoek] = useState('');

    // Bevestig verwijderen
    const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

    // Lokale bestanden state
    const [lokaalBestanden, setLokaalBestanden] = useState<LokaalBestand[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const fetchLagen = useCallback(async () => {
        try {
            const res = await externeKaartlagenAPI.getAll();
            setLagen(res.data.lagen);
        } catch (err) {
            setError(foutMelding(err, 'Fout bij ophalen kaartlagen'));
        } finally {
            setIsLoading(false);
        }
    }, []);

    const fetchKoppelOpties = useCallback(async () => {
        try {
            const res = await externeKaartlagenAPI.getKoppelOpties();
            setKoppelOpties(res.data);
        } catch {
            /* opties zijn optioneel; formulier blijft bruikbaar */
        }
    }, []);

    const fetchLokaalBestanden = useCallback(async () => {
        try {
            const res = await externeKaartlagenAPI.getLokaalBestanden();
            setLokaalBestanden(res.data.bestanden);
        } catch { /* stille fout */ }
    }, []);

    useEffect(() => {
        fetchLagen();
        fetchKoppelOpties();
        fetchLokaalBestanden();
    }, [fetchLagen, fetchKoppelOpties, fetchLokaalBestanden]);

    const gegroepeerdeLagen = useMemo(() => groepeerKaartlagen(lagen), [lagen]);
    const benoemdeGroepenAantal = useMemo(
        () => gegroepeerdeLagen.filter(g => !g.isOverig).length,
        [gegroepeerdeLagen]
    );

    const indicatorNaamMap = useMemo(() => {
        const m = new Map<string, string>();
        koppelOpties.indicatoren.forEach(ind => m.set(ind.uuid, ind.naam));
        return m;
    }, [koppelOpties.indicatoren]);

    const gefilterdeIndicatoren = useMemo(() => {
        const q = indicatorZoek.trim().toLowerCase();
        if (!q) return koppelOpties.indicatoren;
        return koppelOpties.indicatoren.filter(
            ind =>
                ind.naam.toLowerCase().includes(q) ||
                (ind.thema && ind.thema.toLowerCase().includes(q))
        );
    }, [koppelOpties.indicatoren, indicatorZoek]);

    const themaOpties = useMemo(() => {
        const set = new Set(koppelOpties.themas);
        if (form.kompas_thema_naam) set.add(form.kompas_thema_naam);
        return Array.from(set).sort((a, b) => a.localeCompare(b, 'nl'));
    }, [koppelOpties.themas, form.kompas_thema_naam]);

    const clearMessages = () => { setError(null); setSuccess(null); };

    const openNewForm = () => {
        clearMessages();
        setEditId(null);
        setForm({ ...EMPTY_FORM });
        setIndicatorZoek('');
        setShowForm(true);
    };

    const openEditForm = (laag: ExterneKaartlaag) => {
        clearMessages();
        setEditId(laag.id);
        setForm({
            naam: laag.naam,
            beschrijving: laag.beschrijving || '',
            laag_type: laag.laag_type,
            bron_type: laag.bron_type,
            url: laag.url,
            typename: laag.typename || '',
            srsname: laag.srsname,
            versie: laag.versie,
            filter_type: laag.filter_type,
            filter_waarde: laag.filter_waarde || '',
            koppel_veld: laag.koppel_veld || null,
            kleur_lijn: laag.kleur_lijn,
            kleur_fill: laag.kleur_fill,
            opacity: laag.opacity,
            actief: laag.actief,
            volgorde: laag.volgorde,
            groep_naam: laag.groep_naam || null,
            groep_volgorde: laag.groep_volgorde ?? 0,
            kompas_thema_naam: laag.kompas_thema_naam || null,
            gekoppelde_indicatoren: laag.gekoppelde_indicatoren || [],
        });
        setIndicatorZoek('');
        setShowForm(true);
    };

    const handleSave = async () => {
        if (!form.naam.trim() || !form.url.trim()) {
            setError('Naam en URL zijn verplicht');
            return;
        }
        setIsSaving(true);
        clearMessages();
        const payload: ExterneKaartlaagCreate = {
            ...form,
            groep_naam: form.groep_naam?.trim() || null,
            kompas_thema_naam: form.kompas_thema_naam?.trim() || null,
            groep_volgorde: Number(form.groep_volgorde) || 0,
            gekoppelde_indicatoren: form.gekoppelde_indicatoren || [],
        };
        try {
            if (editId) {
                await externeKaartlagenAPI.update(editId, payload);
                setSuccess(`Kaartlaag "${payload.naam}" bijgewerkt`);
            } else {
                await externeKaartlagenAPI.create(payload);
                setSuccess(`Kaartlaag "${payload.naam}" aangemaakt`);
            }
            setShowForm(false);
            await Promise.all([fetchLagen(), fetchKoppelOpties()]);
            setTimeout(() => setSuccess(null), 4000);
        } catch (err) {
            setError(foutMelding(err, 'Fout bij opslaan'));
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async (id: number) => {
        setIsSaving(true);
        clearMessages();
        try {
            const res = await externeKaartlagenAPI.delete(id);
            setSuccess(`Kaartlaag "${res.data.naam}" verwijderd`);
            setDeleteConfirmId(null);
            await fetchLagen();
            setTimeout(() => setSuccess(null), 4000);
        } catch (err) {
            setError(foutMelding(err, 'Fout bij verwijderen'));
        } finally {
            setIsSaving(false);
        }
    };

    const handleToggleActief = async (laag: ExterneKaartlaag) => {
        clearMessages();
        try {
            await externeKaartlagenAPI.update(laag.id, { actief: !laag.actief });
            await fetchLagen();
            setSuccess(`${laag.naam} ${!laag.actief ? 'geactiveerd' : 'gedeactiveerd'}`);
            setTimeout(() => setSuccess(null), 3000);
        } catch (err) {
            setError(foutMelding(err, 'Fout bij togglen'));
        }
    };

    const slaVolgordeOp = async (items: KaartlaagVolgordeItem[], melding: string) => {
        if (items.length === 0) return;
        setIsSaving(true);
        clearMessages();
        try {
            await externeKaartlagenAPI.updateVolgorde(items);
            await fetchLagen();
            setSuccess(melding);
            setTimeout(() => setSuccess(null), 3000);
        } catch (err) {
            setError(foutMelding(err, 'Fout bij aanpassen volgorde'));
        } finally {
            setIsSaving(false);
        }
    };

    const moveGroup = async (groepIndex: number, delta: -1 | 1) => {
        const benoemd = gegroepeerdeLagen.filter(g => !g.isOverig);
        const doelIndex = groepIndex + delta;
        if (groepIndex < 0 || doelIndex < 0 || doelIndex >= benoemd.length) return;

        const herordend = [...benoemd];
        const [verplaatst] = herordend.splice(groepIndex, 1);
        herordend.splice(doelIndex, 0, verplaatst);

        const items: KaartlaagVolgordeItem[] = [];
        herordend.forEach((groep, gIdx) => {
            const nieuweGroepVolgorde = gIdx * 10;
            groep.lagen.forEach((laag, lIdx) => {
                items.push({
                    id: laag.id,
                    volgorde: lIdx * 10,
                    groep_volgorde: nieuweGroepVolgorde,
                });
            });
        });

        await slaVolgordeOp(items, `Groep "${verplaatst.naam}" verplaatst`);
    };

    const moveLayer = async (groep: KaartlaagGroep, laagIndex: number, delta: -1 | 1) => {
        const doelIndex = laagIndex + delta;
        if (laagIndex < 0 || doelIndex < 0 || doelIndex >= groep.lagen.length) return;

        const herordend = [...groep.lagen];
        const [verplaatst] = herordend.splice(laagIndex, 1);
        herordend.splice(doelIndex, 0, verplaatst);

        const items: KaartlaagVolgordeItem[] = herordend.map((laag, idx) => ({
            id: laag.id,
            volgorde: idx * 10,
            groep_volgorde: laag.groep_volgorde ?? groep.volgorde,
        }));

        await slaVolgordeOp(items, `Volgorde van "${verplaatst.naam}" aangepast`);
    };

    const toggleIndicator = (uuid: string) => {
        setForm(prev => {
            const huidig = prev.gekoppelde_indicatoren || [];
            const bestaat = huidig.includes(uuid);
            return {
                ...prev,
                gekoppelde_indicatoren: bestaat ? huidig.filter(u => u !== uuid) : [...huidig, uuid],
            };
        });
    };

    const updateField = <K extends keyof ExterneKaartlaagCreate>(key: K, value: ExterneKaartlaagCreate[K]) => {
        setForm(prev => ({ ...prev, [key]: value }));
    };

    const handleUpload = async (file: File) => {
        setIsUploading(true);
        clearMessages();
        try {
            const res = await externeKaartlagenAPI.upload(file);
            setSuccess(`Bestand "${res.data.bestandsnaam}" geüpload (${res.data.features} features)`);
            await fetchLokaalBestanden();
            setTimeout(() => setSuccess(null), 4000);
        } catch (err) {
            setError(foutMelding(err, 'Fout bij uploaden'));
        } finally {
            setIsUploading(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file) handleUpload(file);
    };

    if (isLoading) return <div className="p-4">Externe kaartlagen laden...</div>;

    return (
        <div className="page-container">
            <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1>Externe Kaartlagen</h1>
                    <p className="text-secondary">Beheer externe geo-lagen (WFS/WMS/lokaal), hun groepering in de viewer en koppelingen met Kompasthema&apos;s en indicatoren.</p>
                </div>
                <button className="btn btn-primary" onClick={openNewForm} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Plus size={16} /> Nieuwe Laag
                </button>
            </header>

            {error && <div className="alert alert-error">{error}</div>}
            {success && <div className="alert alert-success">{success}</div>}

            {/* Upload sectie */}
            <div className="card mb-4">
                <div className="card-header pb-3 mb-3 border-bottom">
                    <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Upload size={18} /> Bestand Uploaden
                    </h2>
                </div>
                <div
                    onDrop={handleDrop}
                    onDragOver={e => e.preventDefault()}
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                        border: '2px dashed var(--color-border)',
                        borderRadius: '8px',
                        padding: '2rem',
                        textAlign: 'center',
                        cursor: 'pointer',
                        transition: 'border-color 0.2s',
                        opacity: isUploading ? 0.5 : 1,
                    }}
                >
                    <Upload size={32} style={{ color: 'var(--color-text-muted)', marginBottom: '0.5rem' }} />
                    <p style={{ margin: 0 }}>
                        {isUploading ? 'Bezig met uploaden...' : 'Sleep een .gpkg of .geojson bestand hierheen, of klik om te selecteren'}
                    </p>
                    <input
                        ref={fileInputRef}
                        type="file"
                        aria-label="Bestand kiezen"
                        accept=".gpkg,.geojson,.json"
                        style={{ display: 'none' }}
                        onChange={e => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }}
                    />
                </div>
                {lokaalBestanden.length > 0 && (
                    <div style={{ marginTop: '1rem' }}>
                        <p style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                            <HardDrive size={14} style={{ verticalAlign: 'middle' }} /> Beschikbare bestanden ({lokaalBestanden.length})
                        </p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                            {lokaalBestanden.map(b => (
                                <span key={b.bestandsnaam} style={{
                                    padding: '0.35rem 0.75rem',
                                    background: 'var(--color-bg-secondary)',
                                    borderRadius: '6px',
                                    fontSize: '0.8rem',
                                    display: 'flex', alignItems: 'center', gap: '0.4rem',
                                }}>
                                    📦 {b.bestandsnaam}
                                    {b.features !== undefined && <span style={{ color: 'var(--color-text-muted)' }}>({b.features} features)</span>}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Formulier (toevoegen / bewerken) */}
            {showForm && (
                <div className="card mb-4">
                    <div className="card-header pb-3 mb-3 border-bottom">
                        <h2 className="card-title">{editId ? 'Laag Bewerken' : 'Nieuwe Laag Toevoegen'}</h2>
                    </div>

                    <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        {/* Naam */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-naam">Naam *</label>
                            <input id="el-naam" className="form-control" value={form.naam}
                                onChange={e => updateField('naam', e.target.value)}
                                placeholder="bijv. BAG Woonplaatsen" />
                        </div>

                        {/* Laag type */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-laag-type">Laag Type</label>
                            <select id="el-laag-type" className="form-control" value={form.laag_type}
                                onChange={e => updateField('laag_type', e.target.value as 'selectie' | 'data_koppel')}>
                                <option value="selectie">Selectie (klik → buurten selecteren)</option>
                                <option value="data_koppel">Data Koppel (CBS-buurt verrijking)</option>
                            </select>
                        </div>

                        {/* Beschrijving */}
                        <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                            <label className="form-label" htmlFor="el-beschrijving">Beschrijving</label>
                            <textarea id="el-beschrijving" className="form-control" rows={2}
                                value={form.beschrijving || ''}
                                onChange={e => updateField('beschrijving', e.target.value)}
                                placeholder="Beschrijving van de laag..." />
                        </div>

                        {/* Kompasthema */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-kompas-thema">Kompasthema</label>
                            <select id="el-kompas-thema" className="form-control"
                                value={form.kompas_thema_naam || ''}
                                onChange={e => updateField('kompas_thema_naam', e.target.value || null)}>
                                <option value="">— Geen Kompasthema —</option>
                                {themaOpties.map(t => (
                                    <option key={t} value={t}>{t}</option>
                                ))}
                            </select>
                        </div>

                        {/* Groepsnaam (optioneel) */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-groep-naam">Groepsnaam (optioneel)</label>
                            <input id="el-groep-naam" className="form-control" list="el-groepen-datalist"
                                value={form.groep_naam || ''}
                                onChange={e => updateField('groep_naam', e.target.value || null)}
                                placeholder="bijv. Gebiedsindelingen (leeg = Kompasthema)" />
                            <datalist id="el-groepen-datalist">
                                {koppelOpties.groepen.map(g => (
                                    <option key={g} value={g} />
                                ))}
                            </datalist>
                            <small style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
                                Laat leeg om het gekozen Kompasthema als groep in de viewer te gebruiken.
                            </small>
                        </div>

                        {/* Gekoppelde indicatoren */}
                        <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                            <label className="form-label" htmlFor="el-indicatoren-zoek">
                                Gekoppelde indicatoren ({(form.gekoppelde_indicatoren || []).length})
                            </label>
                            {(form.gekoppelde_indicatoren || []).length > 0 && (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.5rem' }}>
                                    {(form.gekoppelde_indicatoren || []).map(uuid => {
                                        const indNaam = indicatorNaamMap.get(uuid) || uuid;
                                        return (
                                            <span key={uuid} style={{
                                                display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                                                padding: '0.2rem 0.55rem', borderRadius: '999px',
                                                background: 'var(--color-bg-secondary)', fontSize: '0.78rem',
                                            }}>
                                                {indNaam}
                                                <button type="button" onClick={() => toggleIndicator(uuid)}
                                                    aria-label={`Ontkoppel ${indNaam}`}
                                                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'inline-flex' }}>
                                                    <X size={12} />
                                                </button>
                                            </span>
                                        );
                                    })}
                                </div>
                            )}
                            <input id="el-indicatoren-zoek" type="search" className="form-control"
                                value={indicatorZoek}
                                onChange={e => setIndicatorZoek(e.target.value)}
                                placeholder="Zoek indicator op naam of thema..." style={{ marginBottom: '0.4rem' }} />
                            <div role="group" aria-label="Kies gekoppelde indicatoren" style={{
                                maxHeight: '160px', overflowY: 'auto', border: '1px solid var(--color-border)',
                                borderRadius: '6px', padding: '0.4rem 0.6rem', display: 'flex', flexDirection: 'column', gap: '0.25rem',
                            }}>
                                {gefilterdeIndicatoren.length === 0 ? (
                                    <span style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
                                        Geen indicatoren gevonden.
                                    </span>
                                ) : (
                                    gefilterdeIndicatoren.map(ind => (
                                        <label key={ind.uuid} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', cursor: 'pointer' }}>
                                            <input type="checkbox"
                                                checked={(form.gekoppelde_indicatoren || []).includes(ind.uuid)}
                                                onChange={() => toggleIndicator(ind.uuid)} />
                                            <span>{ind.naam}</span>
                                            {ind.thema && (
                                                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
                                                    ({ind.thema})
                                                </span>
                                            )}
                                        </label>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Bron type */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-bron-type">Bron Type</label>
                            <select id="el-bron-type" className="form-control" value={form.bron_type}
                                onChange={e => {
                                    const v = e.target.value as 'WFS' | 'WMS' | 'GeoJSON' | 'lokaal';
                                    updateField('bron_type', v);
                                    if (v === 'lokaal') {
                                        updateField('filter_type', 'alles');
                                        updateField('filter_waarde', '');
                                    }
                                }}>
                                <option value="WFS">WFS (externe service)</option>
                                <option value="WMS">WMS</option>
                                <option value="GeoJSON">GeoJSON (URL)</option>
                                <option value="lokaal">Lokaal bestand (data-upload/)</option>
                            </select>
                        </div>

                        {/* URL of bestandsselector (uniek id="el-url") */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-url">
                                {form.bron_type === 'lokaal' ? 'Bestand *' : 'WFS/WMS URL *'}
                            </label>
                            {form.bron_type === 'lokaal' ? (
                                <select id="el-url" className="form-control" value={form.url}
                                    onChange={e => {
                                        const filename = e.target.value;
                                        updateField('url', filename);
                                        const best = lokaalBestanden.find(b => b.bestandsnaam === filename);
                                        if (best?.layers?.[0]) updateField('typename', best.layers[0]);
                                    }}>
                                    <option value="">— Kies een bestand —</option>
                                    {lokaalBestanden.filter(b => !b.fout).map(b => (
                                        <option key={b.bestandsnaam} value={b.bestandsnaam}>
                                            {b.bestandsnaam} ({b.features} features, {b.crs})
                                        </option>
                                    ))}
                                </select>
                            ) : (
                                <input id="el-url" className="form-control" value={form.url}
                                    onChange={e => updateField('url', e.target.value)}
                                    placeholder="https://service.pdok.nl/..." />
                            )}
                        </div>

                        {/* TypeName */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-typename">TypeName</label>
                            <input id="el-typename" className="form-control" value={form.typename || ''}
                                onChange={e => updateField('typename', e.target.value)}
                                placeholder="bijv. bag:woonplaats" />
                        </div>

                        {/* SRS Name */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-srsname">SRS</label>
                            <select id="el-srsname" className="form-control" value={form.srsname}
                                onChange={e => updateField('srsname', e.target.value)}>
                                <option value="EPSG:28992">EPSG:28992 (Rijksdriehoek)</option>
                                <option value="EPSG:4326">EPSG:4326 (WGS84)</option>
                            </select>
                        </div>

                        {/* Filter type */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-filter-type">Filter Type</label>
                            <select id="el-filter-type" className="form-control" value={form.filter_type}
                                onChange={e => updateField('filter_type', e.target.value as 'bbox' | 'provincie' | 'alles')}>
                                <option value="provincie">Provincie (bbox)</option>
                                <option value="bbox">Custom BBox</option>
                                <option value="alles">Geen filter (alles)</option>
                            </select>
                        </div>

                        {/* Filter waarde */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-filter-waarde">
                                {form.filter_type === 'provincie' ? 'Provincie' : 'BBox (minX,minY,maxX,maxY)'}
                            </label>
                            {form.filter_type === 'provincie' ? (
                                <select id="el-filter-waarde" className="form-control"
                                    value={form.filter_waarde || ''}
                                    onChange={e => updateField('filter_waarde', e.target.value)}>
                                    <option value="Fryslân">Fryslân</option>
                                    <option value="Groningen">Groningen</option>
                                    <option value="Drenthe">Drenthe</option>
                                    <option value="Overijssel">Overijssel</option>
                                    <option value="Flevoland">Flevoland</option>
                                    <option value="Gelderland">Gelderland</option>
                                    <option value="Utrecht">Utrecht</option>
                                    <option value="Noord-Holland">Noord-Holland</option>
                                    <option value="Zuid-Holland">Zuid-Holland</option>
                                    <option value="Zeeland">Zeeland</option>
                                    <option value="Noord-Brabant">Noord-Brabant</option>
                                    <option value="Limburg">Limburg</option>
                                    <option value="Nederland">Nederland</option>
                                </select>
                            ) : (
                                <input id="el-filter-waarde" className="form-control"
                                    value={form.filter_waarde || ''}
                                    onChange={e => updateField('filter_waarde', e.target.value)}
                                    placeholder="90000,535000,250000,640000" />
                            )}
                        </div>

                        {/* Kleuren */}
                        <div className="form-group">
                            <span className="form-label" id="el-kleuren-label">Kleuren</span>
                            <div role="group" aria-labelledby="el-kleuren-label" style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                                    Lijn
                                    <input type="color" value={form.kleur_lijn}
                                        onChange={e => updateField('kleur_lijn', e.target.value)}
                                        style={{ width: '40px', height: '30px', border: 'none', cursor: 'pointer' }} />
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                                    Vul
                                    <input type="color" value={form.kleur_fill}
                                        onChange={e => updateField('kleur_fill', e.target.value)}
                                        style={{ width: '40px', height: '30px', border: 'none', cursor: 'pointer' }} />
                                </label>
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                                    Opacity
                                    <input type="range" min="0" max="1" step="0.05"
                                        value={form.opacity}
                                        onChange={e => updateField('opacity', parseFloat(e.target.value))}
                                        style={{ width: '80px' }} />
                                    <span style={{ minWidth: '2.5rem', textAlign: 'right' }}>{Math.round(form.opacity * 100)}%</span>
                                </label>
                            </div>
                        </div>

                        {/* Volgorde + Actief */}
                        <div className="form-group">
                            <label className="form-label" htmlFor="el-volgorde">Volgorde &amp; Zichtbaarheid</label>
                            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                                <input id="el-volgorde" type="number" className="form-control" style={{ width: '80px' }}
                                    value={form.volgorde}
                                    onChange={e => updateField('volgorde', parseInt(e.target.value, 10) || 0)} />
                                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                                    <input type="checkbox" checked={form.actief}
                                        onChange={e => updateField('actief', e.target.checked)} />
                                    Actief (zichtbaar in frontend)
                                </label>
                            </div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
                        <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
                            {isSaving ? 'Opslaan...' : editId ? 'Wijzigingen Opslaan' : 'Laag Toevoegen'}
                        </button>
                        <button className="btn btn-secondary" onClick={() => setShowForm(false)} disabled={isSaving}>
                            Annuleren
                        </button>
                    </div>
                </div>
            )}

            {/* Gegroepeerd overzicht */}
            <div className="card">
                <div className="card-header pb-3 mb-3 border-bottom">
                    <h2 className="card-title">Geregistreerde Kaartlagen ({lagen.length})</h2>
                </div>

                {lagen.length === 0 ? (
                    <p className="text-secondary">Nog geen externe kaartlagen geregistreerd. Klik op &quot;Nieuwe Laag&quot; om te beginnen.</p>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                        {gegroepeerdeLagen.map((groep, groepIdx) => (
                            <section key={groep.naam} aria-label={`Groep ${groep.naam}`} style={{
                                border: '1px solid var(--color-border)', borderRadius: '8px', overflow: 'hidden',
                            }}>
                                <div style={{
                                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                    padding: '0.6rem 0.9rem', background: 'var(--color-bg-secondary)',
                                    borderBottom: '1px solid var(--color-border)',
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <strong>{groep.naam}</strong>
                                        <span className="badge" style={{ fontSize: '0.75rem' }}>{groep.lagen.length}</span>
                                    </div>
                                    <div style={{ display: 'flex', gap: '0.35rem' }}>
                                        <button type="button" className="btn btn-secondary btn-sm"
                                            disabled={isSaving || groep.isOverig || groepIdx === 0}
                                            onClick={() => moveGroup(groepIdx, -1)}
                                            aria-label={`Groep ${groep.naam} omhoog verplaatsen`}
                                            title="Groep omhoog" style={{ padding: '0.25rem 0.45rem' }}>
                                            <ArrowUp size={14} />
                                        </button>
                                        <button type="button" className="btn btn-secondary btn-sm"
                                            disabled={isSaving || groep.isOverig || groepIdx >= benoemdeGroepenAantal - 1}
                                            onClick={() => moveGroup(groepIdx, 1)}
                                            aria-label={`Groep ${groep.naam} omlaag verplaatsen`}
                                            title="Groep omlaag" style={{ padding: '0.25rem 0.45rem' }}>
                                            <ArrowDown size={14} />
                                        </button>
                                    </div>
                                </div>

                                <div style={{ overflowX: 'auto' }}>
                                    <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                                        <thead>
                                            <tr>
                                                <th style={{ textAlign: 'left', padding: '0.65rem 0.5rem' }}>Volgorde</th>
                                                <th style={{ textAlign: 'left', padding: '0.65rem 0.5rem' }}>Naam &amp; Koppeling</th>
                                                <th style={{ textAlign: 'left', padding: '0.65rem 0.5rem' }}>Type</th>
                                                <th style={{ textAlign: 'left', padding: '0.65rem 0.5rem' }}>Bron</th>
                                                <th style={{ textAlign: 'center', padding: '0.65rem 0.5rem' }}>Kleur</th>
                                                <th style={{ textAlign: 'center', padding: '0.65rem 0.5rem' }}>Status</th>
                                                <th style={{ textAlign: 'right', padding: '0.65rem 0.5rem' }}>Acties</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {groep.lagen.map((laag, laagIdx) => (
                                                <tr key={laag.id} style={{
                                                    borderBottom: '1px solid var(--color-border)',
                                                    opacity: laag.actief ? 1 : 0.5,
                                                }}>
                                                    <td style={{ padding: '0.65rem 0.5rem', whiteSpace: 'nowrap' }}>
                                                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                                                            <button type="button" className="btn btn-secondary btn-sm"
                                                                disabled={isSaving || laagIdx === 0}
                                                                onClick={() => moveLayer(groep, laagIdx, -1)}
                                                                aria-label={`${laag.naam} omhoog verplaatsen`}
                                                                title="Omhoog" style={{ padding: '0.25rem 0.4rem' }}>
                                                                <ArrowUp size={13} />
                                                            </button>
                                                            <button type="button" className="btn btn-secondary btn-sm"
                                                                disabled={isSaving || laagIdx === groep.lagen.length - 1}
                                                                onClick={() => moveLayer(groep, laagIdx, 1)}
                                                                aria-label={`${laag.naam} omlaag verplaatsen`}
                                                                title="Omlaag" style={{ padding: '0.25rem 0.4rem' }}>
                                                                <ArrowDown size={13} />
                                                            </button>
                                                        </div>
                                                    </td>
                                                    <td style={{ padding: '0.65rem 0.5rem' }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                            <Globe size={16} style={{ color: laag.kleur_lijn, flexShrink: 0 }} />
                                                            <div>
                                                                <strong>{laag.naam}</strong>
                                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '2px' }}>
                                                                    {laag.kompas_thema_naam && (
                                                                        <span className="badge" style={{ fontSize: '0.72rem' }}>
                                                                            Thema: {laag.kompas_thema_naam}
                                                                        </span>
                                                                    )}
                                                                    {(laag.gekoppelde_indicatoren?.length ?? 0) > 0 && (
                                                                        <span className="badge" style={{ fontSize: '0.72rem' }}>
                                                                            {laag.gekoppelde_indicatoren.length} ind.
                                                                        </span>
                                                                    )}
                                                                </div>
                                                                {laag.beschrijving && (
                                                                    <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                                                                        {laag.beschrijving.slice(0, 60)}{laag.beschrijving.length > 60 ? '…' : ''}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td style={{ padding: '0.65rem 0.5rem' }}>
                                                        <span className="badge" style={{ fontSize: '0.75rem' }}>
                                                            {laag.laag_type === 'selectie' ? '🗺️ Selectie' : '📊 Data'}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '0.65rem 0.5rem', fontSize: '0.85rem' }}>
                                                        <code style={{ fontSize: '0.8rem' }}>{laag.bron_type}</code>
                                                        <br />
                                                        <span style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}>
                                                            {laag.typename}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '0.65rem 0.5rem', textAlign: 'center' }}>
                                                        <div style={{ display: 'flex', justifyContent: 'center', gap: '4px' }}>
                                                            <span style={{
                                                                display: 'inline-block', width: '20px', height: '20px',
                                                                borderRadius: '4px', border: '2px solid ' + laag.kleur_lijn,
                                                                background: laag.kleur_fill + Math.round(laag.opacity * 255).toString(16).padStart(2, '0'),
                                                            }} title={`Lijn: ${laag.kleur_lijn}, Vul: ${laag.kleur_fill}, Opacity: ${Math.round(laag.opacity * 100)}%`} />
                                                        </div>
                                                    </td>
                                                    <td style={{ padding: '0.65rem 0.5rem', textAlign: 'center' }}>
                                                        <button
                                                            onClick={() => handleToggleActief(laag)}
                                                            title={laag.actief ? 'Deactiveren' : 'Activeren'}
                                                            aria-label={`${laag.naam} ${laag.actief ? 'deactiveren' : 'activeren'}`}
                                                            aria-pressed={laag.actief}
                                                            style={{
                                                                background: 'none', border: 'none', cursor: 'pointer',
                                                                color: laag.actief ? 'var(--color-success)' : 'var(--color-text-muted)',
                                                            }}
                                                        >
                                                            {laag.actief ? <Eye size={18} /> : <EyeOff size={18} />}
                                                        </button>
                                                    </td>
                                                    <td style={{ padding: '0.65rem 0.5rem', textAlign: 'right' }}>
                                                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                                                            <button className="btn btn-secondary btn-sm" onClick={() => openEditForm(laag)}
                                                                title="Bewerken" aria-label={`${laag.naam} bewerken`} style={{ padding: '0.35rem 0.5rem' }}>
                                                                <Pencil size={14} />
                                                            </button>
                                                            {deleteConfirmId === laag.id ? (
                                                                <>
                                                                    <button className="btn btn-sm"
                                                                        style={{ background: 'var(--color-error)', color: 'white', padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}
                                                                        onClick={() => handleDelete(laag.id)} disabled={isSaving}>
                                                                        Bevestig
                                                                    </button>
                                                                    <button className="btn btn-secondary btn-sm"
                                                                        style={{ padding: '0.35rem 0.5rem', fontSize: '0.75rem' }}
                                                                        onClick={() => setDeleteConfirmId(null)}>
                                                                        Nee
                                                                    </button>
                                                                </>
                                                            ) : (
                                                                <button className="btn btn-secondary btn-sm"
                                                                    onClick={() => setDeleteConfirmId(laag.id)}
                                                                    title="Verwijderen" aria-label={`${laag.naam} verwijderen`} style={{ padding: '0.35rem 0.5rem', color: 'var(--color-error)' }}>
                                                                    <Trash2 size={14} />
                                                                </button>
                                                            )}
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </section>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
