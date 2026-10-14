import React, { useEffect, useState, useCallback } from 'react';
import { Inbox, CheckCircle, Clock, AlertCircle, Send, ArrowRight, User, Calendar, Tag, ShieldAlert } from 'lucide-react';
import { meldingenAPI } from '../services/api';
import type { Melding, MeldingsStatus, MeldingsType } from '../types';
import { foutmelding } from './OrganisatiePage';

export const STATUS_LABELS: Record<MeldingsStatus, string> = {
    nieuw: 'Nieuw',
    doorgestuurd_naar_bron: 'Doorgestuurd naar bron',
    in_behandeling: 'In behandeling',
    afgehandeld: 'Afgehandeld',
    afgewezen: 'Afgewezen',
};

export const TYPE_LABELS: Record<MeldingsType, string> = {
    data: 'Data / Indicator',
    ai: 'AI-resultaat',
    systeem: 'Systeem / Bug',
    overig: 'Suggestie / Overig',
};

export const tijd = (w: string | null) => (w ? new Date(w).toLocaleString('nl-NL') : '–');

export const MeldingenPage: React.FC = () => {
    const [meldingen, setMeldingen] = useState<Melding[]>([]);
    const [tellingen, setTellingen] = useState<Record<string, number>>({});
    const [totaal, setTotaal] = useState(0);
    const [actieveStatus, setActieveStatus] = useState<string>('alle');
    const [actiefType, setActiefType] = useState<string>('alle');
    const [geselecteerdeMelding, setGeselecteerdeMelding] = useState<Melding | null>(null);

    const [bezig, setBezig] = useState(false);
    const [succesBericht, setSuccesBericht] = useState<string | null>(null);
    const [foutBericht, setFoutBericht] = useState<string | null>(null);

    // Bewerkvelden detail
    const [nieuweStatus, setNieuweStatus] = useState<MeldingsStatus>('nieuw');
    const [notitieBeheer, setNotitieBeheer] = useState('');
    const [opslaanBezig, setOpslaanBezig] = useState(false);

    const laadMeldingen = useCallback(async () => {
        setBezig(true);
        setFoutBericht(null);
        try {
            const params: { status?: string; type?: string; limit: number; offset: number } = {
                limit: 50,
                offset: 0,
            };
            if (actieveStatus !== 'alle') params.status = actieveStatus;
            if (actiefType !== 'alle') params.type = actiefType;

            const res = await meldingenAPI.getMeldingen(params);
            setMeldingen(res.data.items);
            setTellingen(res.data.tellingen);
            setTotaal(res.data.totaal);

            setGeselecteerdeMelding((huidig) => {
                if (!huidig) return null;
                const actueel = res.data.items.find((m) => m.id === huidig.id);
                if (actueel) {
                    setNieuweStatus(actueel.status);
                    setNotitieBeheer(actueel.notitie_beheer || '');
                    return actueel;
                }
                return huidig;
            });
        } catch (err) {
            setFoutBericht(foutmelding(err, 'Ophalen van meldingen mislukt'));
        } finally {
            setBezig(false);
        }
    }, [actieveStatus, actiefType]);

    useEffect(() => {
        laadMeldingen();
    }, [laadMeldingen]);

    const selecteerMelding = (m: Melding) => {
        setGeselecteerdeMelding(m);
        setNieuweStatus(m.status);
        setNotitieBeheer(m.notitie_beheer || '');
        setSuccesBericht(null);
        setFoutBericht(null);
    };

    const slaWijzigingOp = async () => {
        if (!geselecteerdeMelding) return;
        setOpslaanBezig(true);
        setSuccesBericht(null);
        setFoutBericht(null);
        try {
            const res = await meldingenAPI.updateMelding(geselecteerdeMelding.id, {
                status: nieuweStatus,
                notitie_beheer: notitieBeheer,
            });
            setGeselecteerdeMelding(res.data);
            setNieuweStatus(res.data.status);
            setNotitieBeheer(res.data.notitie_beheer || '');
            setSuccesBericht(`Melding bijgewerkt naar '${STATUS_LABELS[res.data.status]}'.`);
            laadMeldingen();
        } catch (err) {
            setFoutBericht(foutmelding(err, 'Opslaan van wijziging mislukt'));
        } finally {
            setOpslaanBezig(false);
        }
    };

    const getStatusBadgeKleur = (status: MeldingsStatus) => {
        switch (status) {
            case 'nieuw':
                return { bg: 'rgba(59, 130, 246, 0.15)', text: '#3b82f6', border: 'rgba(59, 130, 246, 0.3)' };
            case 'doorgestuurd_naar_bron':
                return { bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)' };
            case 'in_behandeling':
                return { bg: 'rgba(168, 85, 247, 0.15)', text: '#a855f7', border: 'rgba(168, 85, 247, 0.3)' };
            case 'afgehandeld':
                return { bg: 'rgba(34, 197, 94, 0.15)', text: '#22c55e', border: 'rgba(34, 197, 94, 0.3)' };
            case 'afgewezen':
                return { bg: 'rgba(100, 116, 139, 0.15)', text: '#94a3b8', border: 'rgba(100, 116, 139, 0.3)' };
        }
    };

    const totaalAlle = Object.values(tellingen).reduce((a, b) => a + b, 0);

    return (
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.5rem', margin: 0 }}>
                        <Inbox size={26} color="var(--primary-color)" />
                        Terugmeldvoorziening & Regielogboek
                    </h1>
                    <p style={{ margin: '0.25rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                        Feedback van inwoners en gebruikers op indicatoren, AI-antwoorden en techniek. D-OmniTwin fungeert conform het regieprincipe als signaal- en doorstuurpost (&quot;bron blijft bron&quot;).
                    </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <label htmlFor="filter-type" style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>Categorie:</label>
                    <select
                        id="filter-type"
                        value={actiefType}
                        onChange={(e) => setActiefType(e.target.value)}
                        style={{
                            padding: '0.4rem 0.75rem',
                            borderRadius: 'var(--border-radius)',
                            background: 'var(--color-bg-surface)',
                            color: 'var(--color-text-primary)',
                            border: '1px solid var(--color-border)',
                            fontSize: '0.875rem'
                        }}
                    >
                        <option value="alle">Alle categorieën</option>
                        <option value="data">Data / Indicator</option>
                        <option value="ai">AI-resultaat</option>
                        <option value="systeem">Systeem / Bug</option>
                        <option value="overig">Suggestie / Overig</option>
                    </select>
                </div>
            </div>

            {/* Status Tabs */}
            <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--color-border)', marginBottom: '1.5rem', overflowX: 'auto', paddingBottom: '2px' }}>
                <button
                    type="button"
                    onClick={() => setActieveStatus('alle')}
                    style={{
                        padding: '0.6rem 1rem',
                        background: 'none',
                        border: 'none',
                        borderBottom: actieveStatus === 'alle' ? '2px solid var(--primary-color)' : '2px solid transparent',
                        color: actieveStatus === 'alle' ? 'var(--primary-color)' : 'var(--color-text-secondary)',
                        fontWeight: actieveStatus === 'alle' ? 600 : 400,
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.4rem',
                        whiteSpace: 'nowrap'
                    }}
                >
                    Alle
                    <span style={{ fontSize: '0.75rem', background: 'var(--color-border)', padding: '2px 6px', borderRadius: '10px' }}>
                        {totaalAlle}
                    </span>
                </button>

                {(Object.keys(STATUS_LABELS) as MeldingsStatus[]).map((st) => (
                    <button
                        key={st}
                        type="button"
                        onClick={() => setActieveStatus(st)}
                        style={{
                            padding: '0.6rem 1rem',
                            background: 'none',
                            border: 'none',
                            borderBottom: actieveStatus === st ? '2px solid var(--primary-color)' : '2px solid transparent',
                            color: actieveStatus === st ? 'var(--primary-color)' : 'var(--color-text-secondary)',
                            fontWeight: actieveStatus === st ? 600 : 400,
                            cursor: 'pointer',
                            fontSize: '0.9rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                            whiteSpace: 'nowrap'
                        }}
                    >
                        {STATUS_LABELS[st]}
                        <span style={{ fontSize: '0.75rem', background: 'var(--color-border)', padding: '2px 6px', borderRadius: '10px' }}>
                            {tellingen[st] || 0}
                        </span>
                    </button>
                ))}
            </div>

            {foutBericht && (
                <div style={{ padding: '0.75rem 1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 'var(--border-radius)', color: '#ef4444', marginBottom: '1rem', fontSize: '0.9rem' }}>
                    {foutBericht}
                </div>
            )}

            {succesBericht && (
                <div style={{ padding: '0.75rem 1rem', background: 'rgba(34, 197, 94, 0.1)', border: '1px solid rgba(34, 197, 94, 0.3)', borderRadius: 'var(--border-radius)', color: '#22c55e', marginBottom: '1rem', fontSize: '0.9rem' }}>
                    {succesBericht}
                </div>
            )}

            {/* Grid Layout: Lijst links, Detail rechts */}
            <div style={{ display: 'grid', gridTemplateColumns: geselecteerdeMelding ? '1fr 1fr' : '1fr', gap: '1.5rem', alignItems: 'start' }}>
                {/* Linker kolom: Meldingen lijst */}
                <div style={{ background: 'var(--color-bg-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--border-radius)', overflow: 'hidden' }}>
                    <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>Meldingen ({totaal})</span>
                        {bezig && <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Laden…</span>}
                    </div>

                    {meldingen.length === 0 ? (
                        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                            Geen meldingen gevonden voor deze selectie.
                        </div>
                    ) : (
                        <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                            {meldingen.map((m) => {
                                const badge = getStatusBadgeKleur(m.status);
                                const isGeselecteerd = geselecteerdeMelding?.id === m.id;
                                return (
                                    <li
                                        key={m.id}
                                        onClick={() => selecteerMelding(m)}
                                        style={{
                                            padding: '1rem',
                                            borderBottom: '1px solid var(--color-border)',
                                            background: isGeselecteerd ? 'color-mix(in srgb, var(--primary-color) 8%, transparent)' : 'transparent',
                                            cursor: 'pointer',
                                            transition: 'background 0.15s ease',
                                        }}
                                    >
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem', gap: '0.5rem' }}>
                                            <span style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--color-text-primary)' }}>
                                                {m.onderwerp}
                                            </span>
                                            <span
                                                style={{
                                                    fontSize: '0.75rem',
                                                    padding: '2px 8px',
                                                    borderRadius: '12px',
                                                    background: badge.bg,
                                                    color: badge.text,
                                                    border: `1px solid ${badge.border}`,
                                                    whiteSpace: 'nowrap',
                                                    fontWeight: 500,
                                                }}
                                            >
                                                {STATUS_LABELS[m.status]}
                                            </span>
                                        </div>

                                        <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                            {m.toelichting}
                                        </p>

                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                <Tag size={12} /> {TYPE_LABELS[m.type]}
                                            </span>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                <Calendar size={12} /> {tijd(m.aangemaakt_op)}
                                            </span>
                                        </div>
                                    </li>
                                );
                            })}
                        </ul>
                    )}
                </div>

                {/* Rechter kolom: Detailweergave */}
                {geselecteerdeMelding && (
                    <div style={{ background: 'var(--color-bg-surface)', border: '1px solid var(--color-border)', borderRadius: 'var(--border-radius)', padding: '1.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.75rem' }}>
                            <div>
                                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    {TYPE_LABELS[geselecteerdeMelding.type]}
                                </span>
                                <h2 style={{ fontSize: '1.25rem', margin: '0.25rem 0 0', color: 'var(--color-text-primary)' }}>
                                    {geselecteerdeMelding.onderwerp}
                                </h2>
                            </div>
                            <button
                                type="button"
                                onClick={() => setGeselecteerdeMelding(null)}
                                style={{ background: 'none', border: 'none', color: 'var(--color-text-secondary)', cursor: 'pointer', fontSize: '1.2rem' }}
                                aria-label="Sluit details"
                            >
                                &times;
                            </button>
                        </div>

                        {/* Metagegevens */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                            <div>
                                <span style={{ color: 'var(--color-text-secondary)', display: 'block' }}>Aangemaakt op</span>
                                <span style={{ fontWeight: 500 }}>{tijd(geselecteerdeMelding.aangemaakt_op)}</span>
                            </div>
                            <div>
                                <span style={{ color: 'var(--color-text-secondary)', display: 'block' }}>Melder E-mail</span>
                                <span style={{ fontWeight: 500 }}>
                                    {geselecteerdeMelding.melder_email ? (
                                        <span title="Wordt conform AVG gewist zodra de status afgehandeld of afgewezen is">
                                            {geselecteerdeMelding.melder_email}
                                        </span>
                                    ) : (
                                        <em style={{ color: 'var(--color-text-secondary)' }}>Anoniem (of reeds gewist)</em>
                                    )}
                                </span>
                            </div>
                        </div>

                        {/* Toelichting */}
                        <div style={{ marginBottom: '1.25rem' }}>
                            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                                Toelichting van melder
                            </span>
                            <div style={{ padding: '0.8rem', background: 'var(--color-bg-base)', border: '1px solid var(--color-border)', borderRadius: 'var(--border-radius)', fontSize: '0.9rem', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                                {geselecteerdeMelding.toelichting}
                            </div>
                        </div>

                        {/* Meegezonden Context */}
                        {geselecteerdeMelding.context && Object.keys(geselecteerdeMelding.context).length > 0 && (
                            <div style={{ marginBottom: '1.5rem' }}>
                                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                                    Meegezonden context
                                </span>
                                <div style={{ padding: '0.75rem', background: 'var(--color-bg-base)', border: '1px solid var(--color-border)', borderRadius: 'var(--border-radius)', fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                                    {Object.entries(geselecteerdeMelding.context).map(([k, v]) => (
                                        <div key={k} style={{ display: 'flex', gap: '0.5rem' }}>
                                            <span style={{ fontWeight: 600, color: 'var(--color-text-secondary)', minWidth: '110px' }}>{k}:</span>
                                            <span style={{ color: 'var(--color-text-primary)', wordBreak: 'break-word' }}>
                                                {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Afhandeling & Beheer Formulier */}
                        <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '1.25rem', marginTop: '1.25rem' }}>
                            <h3 style={{ fontSize: '1rem', margin: '0 0 1rem' }}>Behandeling & Regie</h3>

                            <div style={{ marginBottom: '1rem' }}>
                                <label htmlFor="wijzig-status" style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                                    Status wijzigen
                                </label>
                                <select
                                    id="wijzig-status"
                                    value={nieuweStatus}
                                    onChange={(e) => setNieuweStatus(e.target.value as MeldingsStatus)}
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem',
                                        borderRadius: 'var(--border-radius)',
                                        background: 'var(--color-bg-base)',
                                        color: 'var(--color-text-primary)',
                                        border: '1px solid var(--color-border)',
                                        fontSize: '0.9rem',
                                    }}
                                >
                                    <option value="nieuw">Nieuw (ongewijzigd)</option>
                                    <option value="doorgestuurd_naar_bron">Doorgestuurd naar bronhouder (regie)</option>
                                    <option value="in_behandeling">In behandeling</option>
                                    <option value="afgehandeld">Afgehandeld (wist melder e-mail)</option>
                                    <option value="afgewezen">Afgewezen (wist melder e-mail)</option>
                                </select>
                                {(nieuweStatus === 'afgehandeld' || nieuweStatus === 'afgewezen') && geselecteerdeMelding.melder_email && (
                                    <span style={{ display: 'block', fontSize: '0.75rem', color: '#f59e0b', marginTop: '4px' }}>
                                        ⚠️ Let op: Bij status &apos;afgehandeld&apos; of &apos;afgewezen&apos; wordt het e-mailadres conform AVG automatisch gewist.
                                    </span>
                                )}
                            </div>

                            <div style={{ marginBottom: '1.25rem' }}>
                                <label htmlFor="notitie-beheer" style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                                    Interne beheerdernotitie
                                </label>
                                <textarea
                                    id="notitie-beheer"
                                    value={notitieBeheer}
                                    onChange={(e) => setNotitieBeheer(e.target.value)}
                                    rows={3}
                                    maxLength={4000}
                                    placeholder="Bijv. Doorgestuurd naar Kadaster / BAG beheerder per ticket #123."
                                    style={{
                                        width: '100%',
                                        padding: '0.5rem',
                                        borderRadius: 'var(--border-radius)',
                                        background: 'var(--color-bg-base)',
                                        color: 'var(--color-text-primary)',
                                        border: '1px solid var(--color-border)',
                                        fontSize: '0.85rem',
                                        boxSizing: 'border-box',
                                        fontFamily: 'inherit',
                                    }}
                                />
                            </div>

                            <button
                                type="button"
                                onClick={slaWijzigingOp}
                                disabled={opslaanBezig}
                                className="btn btn-primary"
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.5rem 1.25rem',
                                    fontSize: '0.9rem',
                                    cursor: opslaanBezig ? 'not-allowed' : 'pointer',
                                    opacity: opslaanBezig ? 0.7 : 1,
                                }}
                            >
                                <CheckCircle size={16} />
                                {opslaanBezig ? 'Opslaan…' : 'Wijzigingen opslaan'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
