// AI-usecases vrijgeven (#307) en het AI-logboek inzien (#313). Alleen voor beheerders (vereis_admin).
// Een usecase gaat open met een verklaring (PDF + versie + geldig tot) en gaat dicht na geldig tot of
// met de noodstop. Wie (login) en wanneer staat bij de usecase en in het vrijgavelogboek.
import React, { useCallback, useEffect, useState } from 'react';
import { Download, FileText, Power, PowerOff, ShieldCheck, Upload } from 'lucide-react';
import { aiVrijgaveAPI } from '../services/api';
import type { AIKetencontrole, AILogFilter, AILogRegel, AIUsecase, AIUsecaseCode, AIVrijgaveRegel } from '../services/api';
import { foutmelding } from './OrganisatiePage';

const PAGINA = 50;

export const REDEN: Record<AIUsecase['reden'], string> = {
    open: 'Open',
    geen_verklaring: 'Dicht: geen verklaring',
    verlopen: 'Dicht: verklaring verlopen',
    stilgezet: 'Dicht: stilgezet (noodstop)',
};

const ACTIE: Record<AIVrijgaveRegel['actie'], string> = {
    verklaring_geupload: 'Verklaring geüpload, actief gemaakt',
    noodstop: 'Noodstop',
    hervat: 'Noodstop opgeheven',
    verlopen: 'Verlopen (automatisch)',
    bewaartermijn: 'Bewaartermijn gewijzigd',
};

/** De applicatie zet A, B en C zelf stil als loggen mislukt of de hashketen niet klopt (#313). */
export const SYSTEEM = 'systeem';
export const isAutomatisch = (u: AIUsecase) => u.stilgezet && u.status_door === SYSTEEM;

export const tijd = (w: string | null) => (w ? new Date(w).toLocaleString('nl-NL') : '–');
export const datum = (w: string | null) => (w ? new Date(`${w}T00:00:00`).toLocaleDateString('nl-NL') : '–');

const UploadFormulier: React.FC<{ code: AIUsecaseCode; klaar: (melding: string) => void; fout: (m: string) => void }> = ({ code, klaar, fout }) => {
    const [bestand, setBestand] = useState<File | null>(null);
    const [versie, setVersie] = useState('');
    const [geldigTot, setGeldigTot] = useState('');
    const [bezig, setBezig] = useState(false);
    const [invoerSleutel, setInvoerSleutel] = useState(0);  // leegt het bestandsveld na een upload
    const id = (veld: string) => `ai-${code}-${veld}`;

    const verstuur = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!bestand || !versie.trim() || !geldigTot) return;
        setBezig(true);
        try {
            await aiVrijgaveAPI.upload(code, bestand, versie.trim(), geldigTot);
            setBestand(null); setVersie(''); setGeldigTot(''); setInvoerSleutel(k => k + 1);
            klaar(`Verklaring voor usecase ${code} geüpload; de usecase is open tot en met ${datum(geldigTot)}.`);
        } catch (err) {
            fout(foutmelding(err, 'Uploaden mislukt'));
        } finally {
            setBezig(false);
        }
    };

    return (
        <form onSubmit={verstuur} style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div className="form-group">
                <label className="form-label" htmlFor={id('pdf')}>Verklaring (PDF)</label>
                <input key={invoerSleutel} id={id('pdf')} type="file" accept="application/pdf" className="form-input"
                    onChange={e => setBestand(e.target.files?.[0] ?? null)} aria-required="true" />
            </div>
            <div className="form-group">
                <label className="form-label" htmlFor={id('versie')}>Versie</label>
                <input id={id('versie')} className="form-input" value={versie} maxLength={100}
                    onChange={e => setVersie(e.target.value)} placeholder="bijv. 0.4.0" required />
            </div>
            <div className="form-group">
                <label className="form-label" htmlFor={id('tot')}>Geldig tot en met</label>
                <input id={id('tot')} type="date" className="form-input" value={geldigTot}
                    onChange={e => setGeldigTot(e.target.value)} required />
            </div>
            <button type="submit" className="btn btn-primary" disabled={bezig || !bestand || !versie.trim() || !geldigTot}>
                <Upload size={16} /> {bezig ? 'Bezig...' : 'Uploaden en vrijgeven'}
            </button>
        </form>
    );
};

export const UsecaseKaart: React.FC<{ u: AIUsecase; bijgewerkt: (m: string) => void; fout: (m: string) => void }> = ({ u, bijgewerkt, fout }) => {
    const [bezig, setBezig] = useState(false);
    const schakel = async () => {
        setBezig(true);
        try {
            if (u.stilgezet) {
                await aiVrijgaveAPI.hervatten(u.code);
                bijgewerkt(`Noodstop van usecase ${u.code} opgeheven.`);
            } else {
                await aiVrijgaveAPI.noodstop(u.code);
                bijgewerkt(`Usecase ${u.code} is stilgezet.`);
            }
        } catch (err) {
            fout(foutmelding(err, 'Wijzigen mislukt'));
        } finally {
            setBezig(false);
        }
    };

    return (
        <section className="card" aria-labelledby={`ai-${u.code}-titel`} data-testid={`usecase-${u.code}`}>
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
                <h2 className="card-title" id={`ai-${u.code}-titel`}>{u.code} – {u.naam}</h2>
                <span className={`badge ${u.open ? 'badge-positive' : 'badge-negative'}`} data-testid={`status-${u.code}`}>
                    {u.reden === 'stilgezet' && isAutomatisch(u) ? 'Dicht: automatische noodstop' : REDEN[u.reden]}
                </span>
            </div>
            <p className="text-secondary">{u.omschrijving}</p>
            {isAutomatisch(u) && (
                <div role="alert" className="login-melding login-melding-fout" data-testid={`automatisch-${u.code}`}>
                    <strong>Automatische noodstop</strong> ({tijd(u.status_op)}): {u.stilgezet_reden ?? 'reden onbekend'}.
                    {' '}Los de oorzaak op en zet de usecase daarna zelf weer aan met <em>Noodstop opheffen</em>.
                </div>
            )}
            <dl style={{ display: 'grid', gridTemplateColumns: 'max-content 1fr', gap: '0.25rem 1rem', margin: '1rem 0' }}>
                <dt>Verklaring</dt>
                <dd>
                    {u.verklaring_url
                        ? <a href={u.verklaring_url} target="_blank" rel="noreferrer"><FileText size={14} /> {u.bestandsnaam}</a>
                        : 'Geen verklaring geüpload'}
                </dd>
                <dt>Versie</dt><dd>{u.versie ?? '–'}</dd>
                <dt>Geldig tot en met</dt><dd>{datum(u.geldig_tot)}</dd>
                <dt>Geüpload en actief gemaakt</dt>
                <dd>{u.geupload_door ? `${u.geupload_door}, ${tijd(u.geupload_op)}` : '–'}</dd>
                <dt>Noodstop</dt>
                <dd>
                    {u.stilgezet ? (isAutomatisch(u) ? 'Aan (automatisch)' : 'Aan') : 'Uit'}
                    {u.status_door ? ` (laatst gewijzigd door ${u.status_door}, ${tijd(u.status_op)})` : ''}
                    {u.stilgezet && !isAutomatisch(u) && u.stilgezet_reden ? `: ${u.stilgezet_reden}` : ''}
                </dd>
            </dl>
            <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                <UploadFormulier code={u.code} klaar={bijgewerkt} fout={fout} />
                <button type="button" className="btn btn-secondary" onClick={schakel} disabled={bezig}>
                    {u.stilgezet ? <><Power size={16} /> Noodstop opheffen</> : <><PowerOff size={16} /> Noodstop: zet stil</>}
                </button>
            </div>
        </section>
    );
};

const AILogboek: React.FC = () => {
    const [filter, setFilter] = useState<AILogFilter>({});
    const [offset, setOffset] = useState(0);
    const [data, setData] = useState<{ totaal: number; regels: AILogRegel[] }>({ totaal: 0, regels: [] });
    const [controle, setControle] = useState<AIKetencontrole | null>(null);
    const [dagen, setDagen] = useState<number | ''>('');
    const [melding, setMelding] = useState<string | null>(null);
    const [fout, setFout] = useState<string | null>(null);

    const laad = useCallback(async () => {
        try {
            setData((await aiVrijgaveAPI.logboek(filter, PAGINA, offset)).data);
        } catch (err) {
            setFout(foutmelding(err, 'AI-logboek laden mislukt'));
        }
    }, [filter, offset]);

    useEffect(() => { laad(); }, [laad]);
    useEffect(() => {
        aiVrijgaveAPI.bewaartermijn().then(r => setDagen(r.data.bewaartermijn_dagen)).catch(() => undefined);
        // De keten meteen narekenen bij het openen (klopt hij niet, dan zet de backend AI stil)
        aiVrijgaveAPI.controle().then(r => setControle(r.data)).catch(() => undefined);
    }, []);

    const zetFilter = (veld: keyof AILogFilter, w: string) => { setOffset(0); setFilter(f => ({ ...f, [veld]: w })); };

    const controleer = async () => {
        try { setControle((await aiVrijgaveAPI.controle()).data); } catch (err) { setFout(foutmelding(err, 'Controle mislukt')); }
    };

    const bewaar = async () => {
        if (dagen === '') return;
        try {
            await aiVrijgaveAPI.zetBewaartermijn(dagen);
            setMelding(`Bewaartermijn op ${dagen} dagen gezet.`);
        } catch (err) {
            setFout(foutmelding(err, 'Bewaartermijn opslaan mislukt'));
        }
    };

    return (
        <section className="card" id="ai-logboek" aria-labelledby="ai-logboek-titel">
            <div className="card-header"><h2 className="card-title" id="ai-logboek-titel">AI-logboek</h2></div>
            <p className="text-secondary">
                Elke AI-actie, ook een geweigerde (usecase dicht). Zonder gebruikersgegevens: geen login, sessie of IP-adres.
                Alleen toevoegen; elke regel bevat een hash van de inhoud en de vorige regel.
            </p>
            {fout && <div role="alert" className="login-melding login-melding-fout">{fout}</div>}
            {melding && <div role="status" className="login-melding">{melding}</div>}
            <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: '1rem' }}>
                <div className="form-group">
                    <label className="form-label" htmlFor="log-usecase">Usecase</label>
                    <select id="log-usecase" className="form-select" value={filter.usecase ?? ''} onChange={e => zetFilter('usecase', e.target.value)}>
                        <option value="">Alle</option><option value="A">A</option><option value="B">B</option>
                        <option value="C">C</option><option value="X">Buiten A/B/C</option><option value="-">Opschonen</option>
                    </select>
                </div>
                <div className="form-group">
                    <label className="form-label" htmlFor="log-status">Status</label>
                    <select id="log-status" className="form-select" value={filter.status ?? ''} onChange={e => zetFilter('status', e.target.value)}>
                        <option value="">Alle</option><option value="uitgevoerd">Uitgevoerd</option><option value="geweigerd">Geweigerd</option>
                        <option value="fout">Fout</option><option value="opgeschoond">Opgeschoond</option>
                    </select>
                </div>
                <div className="form-group">
                    <label className="form-label" htmlFor="log-van">Van</label>
                    <input id="log-van" type="date" className="form-input" value={filter.van ?? ''} onChange={e => zetFilter('van', e.target.value)} />
                </div>
                <div className="form-group">
                    <label className="form-label" htmlFor="log-tot">Tot en met</label>
                    <input id="log-tot" type="date" className="form-input" value={filter.tot ?? ''} onChange={e => zetFilter('tot', e.target.value)} />
                </div>
                <a className="btn btn-secondary" href={aiVrijgaveAPI.exportUrl(filter)}><Download size={16} /> CSV</a>
                <button type="button" className="btn btn-secondary" onClick={controleer}><ShieldCheck size={16} /> Controleer keten</button>
            </div>
            {controle && (
                <div role="status" className={`login-melding ${controle.ok ? '' : 'login-melding-fout'}`}>
                    {controle.ok
                        ? `Keten klopt: ${controle.aantal} regels (id ${controle.eerste_id ?? '–'} t/m ${controle.laatste_id ?? '–'}).`
                        : `Keten klopt niet: ${controle.fouten.map(f => `id ${f.id}: ${f.reden}`).join('; ')}`}
                </div>
            )}
            <div style={{ overflowX: 'auto' }}>
                <table className="table">
                    <thead>
                        <tr><th>Tijdstip</th><th>Usecase</th><th>Functie</th><th>Status</th><th>Vraag of taak</th>
                            <th>Bronnen</th><th>Model</th><th>Resultaat of fout</th><th>Versie</th></tr>
                    </thead>
                    <tbody>
                        {data.regels.map(r => (
                            <tr key={r.id}>
                                <td>{tijd(r.tijdstip)}</td><td>{r.usecase}</td><td>{r.functie}</td><td>{r.status}</td>
                                <td>{r.taak}</td><td title={r.bronnen.join(', ')}>{r.bronnen.length}</td>
                                <td>{r.model}{r.modelversie ? ` (${r.modelversie})` : ''}</td>
                                <td>{r.foutmelding ?? r.resultaat}</td><td>{r.app_versie}</td>
                            </tr>
                        ))}
                        {data.regels.length === 0 && <tr><td colSpan={9}>Geen regels.</td></tr>}
                    </tbody>
                </table>
            </div>
            <div style={{ display: 'flex', gap: 'var(--spacing-md)', alignItems: 'center', marginTop: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGINA))}>Vorige</button>
                <span>{data.totaal === 0 ? '0' : `${offset + 1}–${Math.min(offset + PAGINA, data.totaal)}`} van {data.totaal}</span>
                <button type="button" className="btn btn-secondary" disabled={offset + PAGINA >= data.totaal} onClick={() => setOffset(offset + PAGINA)}>Volgende</button>
            </div>
            <div style={{ display: 'flex', gap: 'var(--spacing-md)', alignItems: 'flex-end', marginTop: '1.5rem', flexWrap: 'wrap' }}>
                <div className="form-group">
                    <label className="form-label" htmlFor="log-bewaartermijn">Bewaartermijn (dagen, 30 tot 3650)</label>
                    <input id="log-bewaartermijn" type="number" min={30} max={3650} className="form-input" value={dagen}
                        onChange={e => setDagen(e.target.value === '' ? '' : Number(e.target.value))} />
                </div>
                <button type="button" className="btn btn-secondary" onClick={bewaar} disabled={dagen === ''}>Opslaan</button>
                <small className="text-secondary">Regels ouder dan de bewaartermijn worden dagelijks verwijderd; dat komt zelf in het logboek.</small>
            </div>
        </section>
    );
};

export const AIUsecasesPage: React.FC = () => {
    const [usecases, setUsecases] = useState<AIUsecase[] | null>(null);
    const [log, setLog] = useState<AIVrijgaveRegel[]>([]);
    const [melding, setMelding] = useState<string | null>(null);
    const [fout, setFout] = useState<string | null>(null);

    const laad = useCallback(async () => {
        try {
            const [u, l] = await Promise.all([aiVrijgaveAPI.usecases(), aiVrijgaveAPI.vrijgavelog()]);
            setUsecases(u.data);
            setLog(l.data);
        } catch (err) {
            setFout(foutmelding(err, 'AI-usecases laden mislukt'));
        }
    }, []);

    useEffect(() => { laad(); }, [laad]);
    // Directe link naar een onderdeel (bijv. /admin/ai-usecases#ai-logboek)
    useEffect(() => {
        const doel = window.location.hash.slice(1);
        if (usecases && doel) document.getElementById(doel)?.scrollIntoView({ block: 'start' });
    }, [usecases]);

    const bijgewerkt = (m: string) => { setFout(null); setMelding(m); laad(); };
    const mislukt = (m: string) => { setMelding(null); setFout(m); };

    return (
        <div className="page-container">
            <header className="page-header">
                <div>
                    <h1>AI-usecases</h1>
                    <p className="text-secondary">
                        Een AI-usecase staat standaard uit. Hij gaat aan als functioneel beheer de verklaring van de
                        eigen toetsing (DPIA, IAMA of besluit) als PDF uploadt, met de versie waarop die slaat en de datum
                        tot wanneer hij geldt. Na die datum gaat hij vanzelf uit; de noodstop zet hem direct uit.
                        Dicht werkt de applicatie zonder AI.
                    </p>
                </div>
            </header>
            {fout && <div role="alert" className="login-melding login-melding-fout">{fout}</div>}
            {melding && <div role="status" className="login-melding">{melding}</div>}
            {!usecases && !fout && <p>Bezig met laden...</p>}
            <div style={{ display: 'grid', gap: 'var(--spacing-lg, 1.5rem)' }}>
                {usecases && (
                    <section className="card" aria-labelledby="ai-overzicht-titel">
                        <div className="card-header"><h2 className="card-title" id="ai-overzicht-titel">Overzicht</h2></div>
                        <div style={{ overflowX: 'auto' }}>
                            <table className="table" data-testid="ai-overzicht">
                                <thead><tr><th>Usecase</th><th>Status</th><th>Versie verklaring</th><th>Geldig tot en met</th><th>Actief gemaakt door</th><th>Noodstop</th></tr></thead>
                                <tbody>
                                    {usecases.map(u => (
                                        <tr key={u.code}>
                                            <td>{u.code} – {u.naam}</td>
                                            <td><span className={`badge ${u.open ? 'badge-positive' : 'badge-negative'}`}>
                                                {u.reden === 'stilgezet' && isAutomatisch(u) ? 'Dicht: automatische noodstop' : REDEN[u.reden]}
                                            </span></td>
                                            <td>{u.versie ?? '–'}</td>
                                            <td>{datum(u.geldig_tot)}</td>
                                            <td>{u.geupload_door ? `${u.geupload_door}, ${tijd(u.geupload_op)}` : '–'}</td>
                                            <td>{u.stilgezet ? `Aan (${u.status_door ?? '?'}, ${tijd(u.status_op)})` : 'Uit'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>
                )}
                {usecases?.map(u => <UsecaseKaart key={u.code} u={u} bijgewerkt={bijgewerkt} fout={mislukt} />)}

                <section className="card" aria-labelledby="ai-vrijgavelog-titel">
                    <div className="card-header"><h2 className="card-title" id="ai-vrijgavelog-titel">Logboek aan- en uitzetten</h2></div>
                    <div style={{ overflowX: 'auto' }}>
                        <table className="table">
                            <thead><tr><th>Tijdstip</th><th>Usecase</th><th>Actie</th><th>Door</th><th>Versie</th><th>Geldig tot</th><th>Toelichting</th></tr></thead>
                            <tbody>
                                {log.map(r => (
                                    <tr key={r.id}>
                                        <td>{tijd(r.tijdstip)}</td><td>{r.usecase ?? '–'}</td><td>{r.actie === 'noodstop' && r.door === SYSTEEM ? 'Automatische noodstop' : (ACTIE[r.actie] ?? r.actie)}</td>
                                        <td>{r.door ?? 'automatisch'}</td><td>{r.versie ?? '–'}</td><td>{datum(r.geldig_tot)}</td><td>{r.toelichting}</td>
                                    </tr>
                                ))}
                                {log.length === 0 && <tr><td colSpan={7}>Nog niets vastgelegd.</td></tr>}
                            </tbody>
                        </table>
                    </div>
                </section>

                <AILogboek />
            </div>
        </div>
    );
};

export default AIUsecasesPage;
