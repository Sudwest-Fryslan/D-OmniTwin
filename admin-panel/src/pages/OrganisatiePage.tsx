// Organisatie en thema instellen (#253). Eén instantie = één organisatie (ADR 0007); alles hier is
// data in de tabel `organisatie` en is als JSON uit te wisselen met een andere instantie (mesh).
// Lezen: GET /api/organisatie (publiek). Instellen, thema's, logo's, export en import: alleen beheerder.
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, Download, Plus, Save, Trash2, Upload } from 'lucide-react';
import { gebiedenAPI, organisatieAPI } from '../services/api';
import type { Organisatie, OrganisatieInvoer, OrganisatieLogo, ThemaInfo } from '../services/api';
import Beeldmerk from '../components/Beeldmerk';

const GEMEENTECODE = /^\d{4}$/;

export function alsInvoer(org: Organisatie): OrganisatieInvoer {
    return {
        code: org.code,
        naam: org.naam,
        korte_naam: org.korte_naam,
        oin: org.oin,
        gemeente_codes: [...org.gemeente_codes],
        benchmark_provincie: org.benchmark_provincie,
        contact_email: org.contact_email,
        thema: org.thema,
        logos: org.logos.map(l => ({ pad: l.pad, naam: l.naam, rol: l.rol })),
        meld_url: org.meld_url ?? null,
    };
}

// Meldingen van de backend leesbaar maken: 422 van FastAPI is een lijst {loc, msg}
export function foutmelding(err: unknown, standaard: string): string {
    const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
    if (Array.isArray(detail)) {
        return detail
            .map((d: { msg?: string }) => String(d?.msg ?? '').replace(/^Value error, /, ''))
            .filter(Boolean)
            .join('; ') || standaard;
    }
    return typeof detail === 'string' ? detail : standaard;
}

const leeg = (s: string) => (s.trim() === '' ? null : s);

// ── Voorbeeld van een thema: kopbalk, knop, link en beeldmerk met de tokens van dat thema ──

// De breedte van de accentlijn (--d-omnitwin-header-accent-width) is geen kleur en staat dus niet in
// `kleuren`. Het voorbeeld toont de lijn (4px) als de accentkleur afwijkt van het eind van het
// kopbalkverloop; het standaardthema zet daar dezelfde kleur met breedte 0px.
const accentBreedte = (thema: ThemaInfo) => {
    const k = thema.kleuren.licht;
    const kleur = k['--d-omnitwin-header-accent-color'];
    return kleur && kleur !== k['--d-omnitwin-header-background-color-end'] ? '4px' : '0px';
};

/** Waarschuwing bij een thema dat WCAG 2.1 AA niet haalt (#284). */
export const WCAG_WAARSCHUWING = 'Voldoet niet aan WCAG 2.1 AA; niet geschikt als standaard voor een overheidsorganisatie.';

export const ThemaVoorbeeld: React.FC<{ thema: ThemaInfo; modus: 'licht' | 'donker'; naam: string }> = ({ thema, modus, naam }) => {
    const k = thema.kleuren[modus];
    // Alle tokens als CSS-variabelen op de container: het beeldmerk (<use>) erft ze ook
    const vars = Object.fromEntries(Object.entries(k)) as React.CSSProperties;
    const t = (token: string, terugval: string) => k[token] ?? terugval;
    return (
        <figure
            data-testid={`voorbeeld-${modus}`}
            style={{ ...vars, margin: 0, border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', overflow: 'hidden', minWidth: 0 }}
        >
            <div
                data-testid={`voorbeeld-${modus}-kopbalk`}
                style={{
                    background: `linear-gradient(135deg, ${t('--d-omnitwin-header-background-color-start', '#1e3a8a')} 0%, ${t('--d-omnitwin-header-background-color-end', '#15803d')} 100%)`,
                    // Accentlijn onder de kopbalk (#284)
                    boxShadow: `inset 0 -${accentBreedte(thema)} 0 ${t('--d-omnitwin-header-accent-color', 'transparent')}`,
                    color: t('--d-omnitwin-header-color', '#ffffff'),
                    display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.75rem',
                }}
            >
                <Beeldmerk size={28} className="voorbeeld-beeldmerk" />
                <div>
                    <div style={{ fontWeight: 600 }}>D-OmniTwin</div>
                    <div style={{ fontSize: '0.75rem', opacity: 0.9 }}>{naam || 'Organisatie'}</div>
                </div>
            </div>
            <div style={{ background: t('--basis-color-default-bg-document', '#f1f5f9'), padding: '0.75rem' }}>
                <div style={{
                    background: t('--basis-color-default-bg-default', '#ffffff'),
                    color: t('--basis-color-default-color-document', '#1e293b'),
                    border: `1px solid ${t('--basis-color-default-border-subtle', '#e2e8f0')}`,
                    borderRadius: 6, padding: '0.6rem', display: 'flex', flexDirection: 'column', gap: '0.5rem',
                }}>
                    <span style={{ fontSize: '0.8rem' }}>
                        Paneel met <span style={{ color: t('--basis-color-accent-1-color-default', '#1e3a8a'), fontWeight: 600 }}>link</span>{' '}
                        en <span style={{ color: t('--basis-color-default-color-subtle', '#64748b') }}>secundaire tekst</span>
                    </span>
                    <span style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <span
                            data-testid={`voorbeeld-${modus}-knop`}
                            style={{
                                background: t('--basis-color-action-1-bg-default', '#1e3a8a'),
                                color: t('--basis-color-action-1-inverse-color-default', '#ffffff'),
                                padding: '0.3rem 0.7rem', borderRadius: 4, fontSize: '0.8rem', fontWeight: 500,
                            }}
                        >Knop</span>
                        <span data-testid={`voorbeeld-${modus}-tab`} style={{
                            background: t('--d-omnitwin-tab-active-background-color', '#c59d00'),
                            color: t('--d-omnitwin-tab-active-color', '#0f172a'),
                            border: `2px solid ${t('--d-omnitwin-tab-active-border-color', t('--d-omnitwin-tab-active-background-color', '#c59d00'))}`,
                            padding: '0.2rem 0.45rem', borderRadius: 4, fontSize: '0.75rem',
                        }}>Actieve tab</span>
                    </span>
                </div>
            </div>
            <figcaption style={{ fontSize: '0.75rem', padding: '0.25rem 0.75rem', color: 'var(--color-text-secondary)' }}>
                {modus === 'licht' ? 'Licht' : 'Donker'}
            </figcaption>
        </figure>
    );
};

export const OrganisatiePage: React.FC = () => {
    const [form, setForm] = useState<OrganisatieInvoer | null>(null);
    const [themas, setThemas] = useState<ThemaInfo[]>([]);
    const [logos, setLogos] = useState<string[]>([]);
    const [gemeenten, setGemeenten] = useState<{ code: string; naam: string; provincie?: string }[]>([]);
    const [fout, setFout] = useState<string | null>(null);
    const [melding, setMelding] = useState<string | null>(null);
    const [bezig, setBezig] = useState(false);
    const [nieuweCode, setNieuweCode] = useState('');
    const [nieuwLogo, setNieuwLogo] = useState('');
    const bestandRef = useRef<HTMLInputElement>(null);

    const laad = useCallback(async () => {
        setFout(null);
        try {
            const [org, th, lg] = await Promise.all([organisatieAPI.get(), organisatieAPI.themas(), organisatieAPI.logos()]);
            setForm(alsInvoer(org.data));
            setThemas(th.data);
            setLogos(lg.data);
        } catch (err) {
            setFout(foutmelding(err, 'Organisatie niet te laden.'));
        }
        // Gemeentenamen en provincies zijn hulp bij het invullen; zonder lukt het ook
        gebiedenAPI.getGemeenten().then(r => setGemeenten(r.data.gemeenten)).catch(() => setGemeenten([]));
    }, []);

    useEffect(() => { laad(); }, [laad]);

    const gekozenThema = useMemo(() => themas.find(t => t.naam === form?.thema), [themas, form?.thema]);
    const provincies = useMemo(
        () => Array.from(new Set(gemeenten.map(g => g.provincie).filter((p): p is string => !!p))).sort(),
        [gemeenten],
    );
    const gemeenteNaam = (code: string) => gemeenten.find(g => g.code === code)?.naam;

    if (!form) {
        return (
            <div className="card">
                {fout ? <p role="alert" style={{ color: 'var(--color-error)' }}>{fout}</p> : <p>Bezig met laden...</p>}
            </div>
        );
    }

    const zet = (wijziging: Partial<OrganisatieInvoer>) => {
        setMelding(null);
        setForm({ ...form, ...wijziging });
    };

    // ── gemeentecodes ──
    const voegCodeToe = () => {
        const code = nieuweCode.trim();
        if (!GEMEENTECODE.test(code)) {
            setFout('Een gemeentecode bestaat uit vier cijfers (CBS), bijvoorbeeld 0080.');
            return;
        }
        setFout(null);
        if (!form.gemeente_codes.includes(code)) zet({ gemeente_codes: [...form.gemeente_codes, code] });
        setNieuweCode('');
    };
    const maakStandaard = (code: string) =>
        zet({ gemeente_codes: [code, ...form.gemeente_codes.filter(c => c !== code)] });

    // ── logo's ──
    const verplaats = (i: number, richting: -1 | 1) => {
        const lijst = [...form.logos];
        const j = i + richting;
        if (j < 0 || j >= lijst.length) return;
        [lijst[i], lijst[j]] = [lijst[j], lijst[i]];
        zet({ logos: lijst });
    };
    const zetLogo = (i: number, w: Partial<OrganisatieLogo>) =>
        zet({ logos: form.logos.map((l, n) => (n === i ? { ...l, ...w } : l)) });
    const beschikbaar = logos.filter(p => !form.logos.some(l => l.pad === p));

    const opslaan = async (e: React.FormEvent) => {
        e.preventDefault();
        setBezig(true);
        setFout(null);
        setMelding(null);
        try {
            const res = await organisatieAPI.zet(form);
            setForm(alsInvoer(res.data));
            setMelding('Opgeslagen. Herlaad de pagina om het beheerscherm in het nieuwe thema te zien; de viewer toont het bij de volgende keer laden.');
        } catch (err) {
            setFout(foutmelding(err, 'Opslaan mislukt.'));
        } finally {
            setBezig(false);
        }
    };

    const exporteer = async () => {
        setFout(null);
        try {
            const res = await organisatieAPI.exporteer();
            const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `organisatie-${res.data.organisatie.code}.json`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            setFout(foutmelding(err, 'Exporteren mislukt.'));
        }
    };

    const importeer = async (bestand: File | undefined) => {
        if (!bestand) return;
        setFout(null);
        setMelding(null);
        try {
            let data: unknown;
            try {
                data = JSON.parse(await bestand.text());
            } catch {
                setFout('Het bestand is geen geldige JSON.');
                return;
            }
            const res = await organisatieAPI.importeer(data);
            setForm(alsInvoer(res.data));
            setMelding(`Geïmporteerd uit ${bestand.name}. Herlaad de pagina om het thema te zien.`);
        } catch (err) {
            setFout(foutmelding(err, 'Importeren mislukt.'));
        } finally {
            if (bestandRef.current) bestandRef.current.value = '';
        }
    };

    return (
        <form onSubmit={opslaan} aria-label="Organisatie instellen" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)', maxWidth: 1100 }}>
            <section className="card" aria-labelledby="kop-thema">
                <h3 id="kop-thema" className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>Thema (huisstijl)</h3>
                <fieldset style={{ border: 'none', display: 'flex', flexWrap: 'wrap', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-md)' }}>
                    <legend className="form-label">Kies een thema uit <code>static/css/themes/</code></legend>
                    {themas.map(t => (
                        <label key={t.naam} className="btn btn-secondary" style={{
                            outline: form.thema === t.naam ? '2px solid var(--merk-bg)' : 'none', cursor: 'pointer',
                        }}>
                            <input type="radio" name="thema" value={t.naam} checked={form.thema === t.naam}
                                onChange={() => zet({ thema: t.naam })} />
                            <span className="color-preview" aria-hidden="true">
                                {['--d-omnitwin-header-background-color-start', '--d-omnitwin-header-background-color-end',
                                    '--basis-color-action-1-bg-default', '--basis-color-accent-2-bg-default'].map(tk => (
                                    <span key={tk} className="color-swatch" style={{ background: t.kleuren.licht[tk] ?? 'transparent', width: 14, height: 14 }} />
                                ))}
                            </span>
                            <span><strong>{t.naam}</strong> — {t.titel}</span>
                            {t.wcag_aa === false && (
                                <span className="badge" title={WCAG_WAARSCHUWING}
                                    style={{ marginLeft: '0.4rem', fontSize: '0.7rem', color: 'var(--color-warning)', border: '1px solid currentColor', borderRadius: 4, padding: '0 0.3rem' }}>
                                    niet WCAG AA
                                </span>
                            )}
                        </label>
                    ))}
                </fieldset>
                {gekozenThema?.wcag_aa === false && (
                    <p role="alert" data-testid="wcag-waarschuwing"
                        style={{ color: 'var(--color-warning)', fontWeight: 600, marginBottom: 'var(--spacing-md)' }}>
                        Thema {gekozenThema.naam}: {WCAG_WAARSCHUWING}
                    </p>
                )}
                {gekozenThema ? (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 'var(--spacing-md)' }}>
                        <ThemaVoorbeeld thema={gekozenThema} modus="licht" naam={form.korte_naam || form.naam} />
                        <ThemaVoorbeeld thema={gekozenThema} modus="donker" naam={form.korte_naam || form.naam} />
                    </div>
                ) : (
                    <p role="alert" style={{ color: 'var(--color-warning)' }}>Thema {form.thema} staat niet in static/css/themes/.</p>
                )}
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: 'var(--spacing-md)' }}>
                    Een eigen thema maak je als bestand (zie de documentatie <em>Thema's</em>). De inlogpagina van Keycloak
                    wisselt niet mee: zet daar <code>loginTheme</code> van realm <code>omnitwin</code> apart.
                </p>
            </section>

            <section className="card" aria-labelledby="kop-org">
                <h3 id="kop-org" className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>Organisatie</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0 var(--spacing-md)' }}>
                    <div className="form-group">
                        <label className="form-label" htmlFor="org-naam">Naam</label>
                        <input id="org-naam" className="form-input" required maxLength={200} value={form.naam}
                            onChange={e => zet({ naam: e.target.value })} />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="org-korte-naam">Korte naam</label>
                        <input id="org-korte-naam" className="form-input" maxLength={50} value={form.korte_naam ?? ''}
                            onChange={e => zet({ korte_naam: leeg(e.target.value) })} />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="org-code">Code (a-z, 0-9, -)</label>
                        <input id="org-code" className="form-input" required pattern="[a-z0-9][a-z0-9\-]{0,31}" value={form.code}
                            onChange={e => zet({ code: e.target.value })} />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="org-email">Contactadres (e-mail)</label>
                        <input id="org-email" type="email" className="form-input" maxLength={254} value={form.contact_email ?? ''}
                            onChange={e => zet({ contact_email: leeg(e.target.value) })} />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="org-meld-url">Meldplek voor &quot;Melden&quot; (https of mailto:)</label>
                        <input id="org-meld-url" type="text" inputMode="url" className="form-input" maxLength={500}
                            value={form.meld_url ?? ''} aria-describedby="org-meld-url-uitleg"
                            onChange={e => zet({ meld_url: leeg(e.target.value) })} />
                        <small id="org-meld-url-uitleg" className="text-secondary">
                            Waar een melding bij een AI-resultaat heen gaat: een nieuw issue (standaard bij D-OmniTwin),
                            een eigen formulier of een functioneel e-mailadres. Leeg = de standaard.
                        </small>
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="org-oin">OIN (optioneel, 20 cijfers)</label>
                        <input id="org-oin" className="form-input" inputMode="numeric" pattern="\d{20}" value={form.oin ?? ''}
                            onChange={e => zet({ oin: leeg(e.target.value) })} />
                    </div>
                    <div className="form-group">
                        <label className="form-label" htmlFor="org-provincie">Standaard-benchmark (provincie)</label>
                        <input id="org-provincie" className="form-input" list="org-provincies" maxLength={100}
                            value={form.benchmark_provincie ?? ''} onChange={e => zet({ benchmark_provincie: leeg(e.target.value) })} />
                        <datalist id="org-provincies">{provincies.map(p => <option key={p} value={p} />)}</datalist>
                    </div>
                </div>

                <h4 className="form-label" style={{ marginTop: 'var(--spacing-sm)' }}>Gemeenten van het eigen gebied (de standaard is de referentie in rapporten)</h4>
                <ul aria-label="Gemeentecodes" style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 'var(--spacing-xs)', marginBottom: 'var(--spacing-sm)' }}>
                    {form.gemeente_codes.map((code, i) => (
                        <li key={code} style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-xs)' }}>
                                <input type="radio" name="standaardgemeente" checked={i === 0} onChange={() => maakStandaard(code)} />
                                <span>{code}{gemeenteNaam(code) ? ` ${gemeenteNaam(code)}` : ''}{i === 0 ? ' (standaard)' : ''}</span>
                            </label>
                            <button type="button" className="btn btn-secondary" aria-label={`Gemeente ${code} verwijderen`}
                                onClick={() => zet({ gemeente_codes: form.gemeente_codes.filter(c => c !== code) })}>
                                <Trash2 size={14} />
                            </button>
                        </li>
                    ))}
                </ul>
                <div style={{ display: 'flex', gap: 'var(--spacing-sm)', maxWidth: 420 }}>
                    <input aria-label="Gemeentecode toevoegen" className="form-input" list="org-gemeenten" placeholder="bijv. 0080"
                        value={nieuweCode} onChange={e => setNieuweCode(e.target.value)} />
                    <datalist id="org-gemeenten">{gemeenten.map(g => <option key={g.code} value={g.code}>{g.naam}</option>)}</datalist>
                    <button type="button" className="btn btn-secondary" onClick={voegCodeToe}><Plus size={14} /> Toevoegen</button>
                </div>
            </section>

            <section className="card" aria-labelledby="kop-logos">
                <h3 id="kop-logos" className="card-title" style={{ marginBottom: 'var(--spacing-md)' }}>Logo's in de footer</h3>
                <ol aria-label="Footer-logo's" style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                    {form.logos.map((l, i) => (
                        <li key={l.pad} style={{
                            display: 'grid', alignItems: 'center', gap: 'var(--spacing-sm)',
                            gridTemplateColumns: '64px minmax(160px, 1fr) minmax(160px, 260px) 110px repeat(3, auto)',
                        }}>
                            {/* Logo's zijn vaak gemaakt voor een lichte achtergrond, zoals de footer */}
                            <img src={l.pad} alt="" style={{ height: 32, width: 64, objectFit: 'contain', background: '#ffffff', borderRadius: 4 }} />
                            <code title={l.pad} style={{ fontSize: '0.75rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {l.pad.replace('/static/images/', '')}
                            </code>
                            <input aria-label={`Naam van logo ${i + 1}`} className="form-input" maxLength={200}
                                value={l.naam ?? ''} onChange={e => zetLogo(i, { naam: leeg(e.target.value) })} />
                            <select aria-label={`Rol van logo ${i + 1}`} className="form-select" value={l.rol}
                                onChange={e => zetLogo(i, { rol: e.target.value })}>
                                <option value="eigen">eigen</option>
                                <option value="partner">partner</option>
                            </select>
                            <button type="button" className="btn btn-secondary" aria-label={`Logo ${i + 1} omhoog`} disabled={i === 0} onClick={() => verplaats(i, -1)}><ArrowUp size={14} /></button>
                            <button type="button" className="btn btn-secondary" aria-label={`Logo ${i + 1} omlaag`} disabled={i === form.logos.length - 1} onClick={() => verplaats(i, 1)}><ArrowDown size={14} /></button>
                            <button type="button" className="btn btn-secondary" aria-label={`Logo ${i + 1} verwijderen`} onClick={() => zet({ logos: form.logos.filter((_, n) => n !== i) })}><Trash2 size={14} /></button>
                        </li>
                    ))}
                </ol>
                <div style={{ display: 'flex', gap: 'var(--spacing-sm)', marginTop: 'var(--spacing-md)', maxWidth: 520 }}>
                    <select aria-label="Logo toevoegen" className="form-select" value={nieuwLogo} onChange={e => setNieuwLogo(e.target.value)}>
                        <option value="">Kies een bestand uit /static/images/</option>
                        {beschikbaar.map(p => <option key={p} value={p}>{p.replace('/static/images/', '')}</option>)}
                    </select>
                    <button type="button" className="btn btn-secondary" disabled={!nieuwLogo}
                        onClick={() => { zet({ logos: [...form.logos, { pad: nieuwLogo, naam: null, rol: 'partner' }] }); setNieuwLogo(''); }}>
                        <Plus size={14} /> Toevoegen
                    </button>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: 'var(--spacing-sm)' }}>
                    Alleen bestaande bestanden; een nieuw logo zet je onder <code>static/images/</code> (of mount je), zie de installatiegids.
                </p>
            </section>

            {/* Meldingen en knoppen blijven onderaan in beeld, ook bij een lange pagina */}
            <div style={{
                position: 'sticky', bottom: 0, background: 'var(--color-background)', padding: 'var(--spacing-md) 0',
                borderTop: '1px solid var(--color-border)', display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)',
            }}>
                {fout && <div role="alert" className="login-melding login-melding-fout">{fout}</div>}
                {melding && (
                    <div role="status" className="login-melding" style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', flexWrap: 'wrap' }}>
                        {melding}
                        <button type="button" className="btn btn-secondary" onClick={() => window.location.reload()}>Nu herladen</button>
                    </div>
                )}
                <div style={{ display: 'flex', gap: 'var(--spacing-sm)', flexWrap: 'wrap' }}>
                    <button type="submit" className="btn btn-primary" disabled={bezig}><Save size={16} /> {bezig ? 'Bezig...' : 'Opslaan'}</button>
                    <button type="button" className="btn btn-secondary" onClick={exporteer}><Download size={16} /> Exporteren (JSON)</button>
                    <button type="button" className="btn btn-secondary" onClick={() => bestandRef.current?.click()}><Upload size={16} /> Importeren (JSON)</button>
                    <input ref={bestandRef} type="file" accept="application/json,.json" aria-label="Exportbestand importeren"
                        style={{ display: 'none' }} onChange={e => importeer(e.target.files?.[0])} />
                </div>
            </div>
        </form>
    );
};
