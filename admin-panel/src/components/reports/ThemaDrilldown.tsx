import React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type {
    FactsheetHistoriePunt,
    FactsheetIndicator,
    FactsheetKwadrant,
    FactsheetThema,
} from '../../types';

interface ThemaDrilldownProps {
    kwadranten: FactsheetKwadrant[];
    isMeervoudig: boolean;
    openThemaIds: Set<number>;
    onToggleThema: (themaId: number) => void;
    onOpenAlles: () => void;
    onSluitAlles: () => void;
}

function fmtWaarde(waarde: number | null, eenheid: string): string {
    if (waarde === null || waarde === undefined) return '—';
    const e = (eenheid || '').trim();
    const isGeheel = Math.abs(waarde - Math.round(waarde)) < 1e-6 && ['aantal', 'jaar', 'm'].includes(e.toLowerCase());
    const getal = isGeheel
        ? Math.round(waarde).toLocaleString('nl-NL')
        : waarde.toLocaleString('nl-NL', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    if (!e || e.toLowerCase() === 'aantal') return getal;
    if (e === '%') return `${getal} %`;
    return `${getal} ${e}`;
}

function fmtVerschil(verschil: number | null, eenheid: string): string {
    if (verschil === null || verschil === undefined) return '—';
    const teken = verschil > 0 ? '+' : '';
    const getal = verschil.toLocaleString('nl-NL', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const e = (eenheid || '').trim();
    if (e === '%') return `${teken}${getal} %-pt`;
    if (!e || e.toLowerCase() === 'aantal') return `${teken}${getal}`;
    return `${teken}${getal} ${e}`;
}

const Sparkline: React.FC<{ historie: FactsheetHistoriePunt[]; label: string }> = ({ historie, label }) => {
    if (historie.length < 2) return null;
    const w = 56;
    const h = 18;
    const padX = 2;
    const padY = 3;
    const waarden = historie.map((p) => p.waarde);
    const minV = Math.min(...waarden);
    const maxV = Math.max(...waarden);
    const span = maxV - minV;

    const punten = historie
        .map((p, idx) => {
            const x = padX + (idx / (historie.length - 1)) * (w - 2 * padX);
            const y =
                span < 1e-6
                    ? h / 2
                    : h - padY - ((p.waarde - minV) / span) * (h - 2 * padY);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(' ');

    return (
        <svg
            width={w}
            height={h}
            viewBox={`0 0 ${w} ${h}`}
            role="img"
            aria-label={`Tijdreeks: ${label}`}
            style={{ overflow: 'visible', flexShrink: 0 }}
        >
            <title>{label}</title>
            <polyline
                fill="none"
                stroke="var(--color-primary)"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={punten}
            />
        </svg>
    );
};

function renderTrend(ind: FactsheetIndicator): React.ReactNode {
    if (!ind.trend || ind.historie.length < 2) {
        return <span style={{ color: 'var(--color-text-secondary)' }}>—</span>;
    }
    const pijl =
        ind.trend.richting === 'stijgend' ? '↗' : ind.trend.richting === 'dalend' ? '↘' : '➔';
    const tekst =
        ind.trend.richting === 'stabiel'
            ? 'Stabiel'
            : ind.trend.duiding === 'gunstig'
              ? 'Gunstig'
              : ind.trend.duiding === 'ongunstig'
                ? 'Ongunstig'
                : ind.trend.richting === 'stijgend'
                  ? 'Stijgend'
                  : 'Dalend';

    return (
        <span className="factsheet-trend-cell" title={ind.trend.label}>
            <Sparkline historie={ind.historie} label={ind.trend.label} />
            <span className={`factsheet-trend-pill ${ind.trend.duiding}`}>
                {pijl} {tekst}
            </span>
        </span>
    );
}

function renderStatusBadge(ind: FactsheetIndicator): React.ReactNode {
    if (ind.status === 'ok' && ind.klasse !== null) {
        return (
            <span className="factsheet-klasse-badge">
                <span
                    className="factsheet-klasse-dot"
                    style={{ backgroundColor: ind.klasse_kleur }}
                    aria-hidden="true"
                />
                <span>
                    Kl. {ind.klasse} · {ind.duiding}
                </span>
            </span>
        );
    }
    if (ind.status === 'context_aantal') {
        return (
            <span className="factsheet-klasse-badge" style={{ color: 'var(--color-text-secondary)' }}>
                context (aantal)
            </span>
        );
    }
    if (ind.status === 'onderdrukt') {
        return (
            <span className="factsheet-klasse-badge" style={{ color: 'var(--color-text-secondary)' }}>
                onderdrukt
            </span>
        );
    }
    if (ind.status === 'geen_referentie') {
        return (
            <span className="factsheet-klasse-badge" style={{ color: 'var(--color-text-secondary)' }}>
                geen referentie
            </span>
        );
    }
    return (
        <span className="factsheet-klasse-badge" style={{ color: 'var(--color-text-secondary)' }}>
            geen data
        </span>
    );
}

export const ThemaDrilldown: React.FC<ThemaDrilldownProps> = ({
    kwadranten,
    isMeervoudig,
    openThemaIds,
    onToggleThema,
    onOpenAlles,
    onSluitAlles,
}) => {
    const alleThemas: { kwadrantNaam: string; kwadrantKleur: string; thema: FactsheetThema }[] = [];
    for (const kw of kwadranten) {
        for (const th of kw.themas) {
            alleThemas.push({ kwadrantNaam: kw.kwadrant_naam, kwadrantKleur: kw.kwadrant_kleur, thema: th });
        }
    }

    if (!alleThemas.length) return null;
    const allesOpen = alleThemas.every((x) => openThemaIds.has(x.thema.thema_id));

    return (
        <section className="factsheet-card" aria-labelledby="factsheet-detail-titel">
            <div className="factsheet-section-header">
                <div>
                    <h2 id="factsheet-detail-titel" className="factsheet-section-title">
                        Detailtabel per thema & onderdeel
                    </h2>
                    <p className="factsheet-section-subtitle">
                        Alle onderliggende Kompas-indicatoren met peiljaar, referentiegemiddelde en meerjarige trend. Aantal-indicatoren staan als feitelijke context en tellen niet mee in de normatieve score.
                    </p>
                </div>
                <button
                    type="button"
                    className="btn btn-secondary hide-on-print"
                    onClick={allesOpen ? onSluitAlles : onOpenAlles}
                    style={{ fontSize: '0.8125rem', padding: '0.35rem 0.75rem' }}
                >
                    {allesOpen ? 'Alles inklappen' : 'Alles uitklappen'}
                </button>
            </div>

            {alleThemas.map(({ kwadrantNaam, kwadrantKleur, thema }) => {
                const isOpen = openThemaIds.has(thema.thema_id);
                const paneelId = `factsheet-paneel-${thema.thema_id}`;
                return (
                    <div
                        key={thema.thema_id}
                        id={`factsheet-thema-${thema.thema_id}`}
                        className="factsheet-accordion"
                    >
                        <button
                            type="button"
                            className="factsheet-accordion-btn"
                            aria-expanded={isOpen}
                            aria-controls={paneelId}
                            onClick={() => onToggleThema(thema.thema_id)}
                        >
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                {isOpen ? <ChevronDown size={17} aria-hidden="true" /> : <ChevronRight size={17} aria-hidden="true" />}
                                <span
                                    className="factsheet-klasse-dot"
                                    style={{ backgroundColor: kwadrantKleur }}
                                    aria-hidden="true"
                                />
                                <span>{thema.thema_naam}</span>
                                <span style={{ fontWeight: 400, fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                                    ({kwadrantNaam})
                                </span>
                            </span>

                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.6rem' }}>
                                {thema.rang ? (
                                    <span style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--color-text-secondary)' }}>
                                        #{thema.rang.positie} van {thema.rang.totaal_met_score}
                                    </span>
                                ) : null}
                                {thema.klasse !== null ? (
                                    <span className="factsheet-klasse-badge">
                                        <span
                                            className="factsheet-klasse-dot"
                                            style={{ backgroundColor: thema.klasse_kleur }}
                                            aria-hidden="true"
                                        />
                                        <span>
                                            Kl. {thema.klasse} · {thema.duiding}
                                        </span>
                                    </span>
                                ) : null}
                            </span>
                        </button>

                        {isOpen && (
                            <div id={paneelId} className="factsheet-table-wrap">
                                <table className="factsheet-table">
                                    <thead>
                                        <tr>
                                            <th scope="col">Onderdeel / Indicator</th>
                                            <th scope="col" className="num">Peiljaar</th>
                                            <th scope="col" className="num">Selectie</th>
                                            <th scope="col" className="num">Buurtgem. ref.</th>
                                            <th scope="col" className="num">Verschil</th>
                                            <th scope="col">Klasse / Status</th>
                                            <th scope="col">Trend</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {thema.onderdelen.map((ond) => (
                                            <React.Fragment key={ond.onderdeel_id}>
                                                <tr className="factsheet-onderdeel-row">
                                                    <td colSpan={5}>
                                                        Onderdeel: {ond.onderdeel_naam}
                                                    </td>
                                                    <td colSpan={2}>
                                                        {ond.klasse !== null ? (
                                                            <span className="factsheet-klasse-badge">
                                                                <span
                                                                    className="factsheet-klasse-dot"
                                                                    style={{ backgroundColor: ond.klasse_kleur }}
                                                                    aria-hidden="true"
                                                                />
                                                                <span>
                                                                    Kl. {ond.klasse} · {ond.duiding}
                                                                </span>
                                                            </span>
                                                        ) : (
                                                            <span style={{ fontSize: '0.78rem', fontWeight: 400, color: 'var(--color-text-secondary)' }}>
                                                                Alleen context / geen normatieve score
                                                            </span>
                                                        )}
                                                    </td>
                                                </tr>

                                                {ond.indicatoren.map((ind) => (
                                                    <tr key={ind.indicator_uuid}>
                                                        <td>
                                                            <div>{ind.naam}</div>
                                                            {ind.polariteit === 'lager_is_beter' && !ind.is_aantal && !ind.is_neutraal && (
                                                                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                                                                    Lagere waarde is gunstiger
                                                                </div>
                                                            )}
                                                        </td>
                                                        <td className="num">{ind.jaar ?? '—'}</td>
                                                        <td className="num">
                                                            {ind.status === 'onderdrukt' ? (
                                                                <span style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)' }}>
                                                                    Afgeschermd (&lt; min. n)
                                                                </span>
                                                            ) : (
                                                                <>
                                                                    {fmtWaarde(ind.waarde, ind.eenheid)}
                                                                    {isMeervoudig && ind.is_aantal && ind.waarde_per_buurt !== null ? (
                                                                        <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                                                                            gem. {fmtWaarde(ind.waarde_per_buurt, ind.eenheid)} / buurt
                                                                        </div>
                                                                    ) : null}
                                                                </>
                                                            )}
                                                        </td>
                                                        <td className="num">
                                                            {fmtWaarde(ind.ref_gemiddelde, ind.eenheid)}
                                                        </td>
                                                        <td className="num">
                                                            {fmtVerschil(ind.verschil, ind.eenheid)}
                                                        </td>
                                                        <td>{renderStatusBadge(ind)}</td>
                                                        <td>{renderTrend(ind)}</td>
                                                    </tr>
                                                ))}
                                            </React.Fragment>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                );
            })}
        </section>
    );
};

