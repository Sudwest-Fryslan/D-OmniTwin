import React from 'react';
import { ChevronRight } from 'lucide-react';
import type { FactsheetKwadrant, FactsheetThema } from '../../types';

interface ThemaBenchmarkBalkenProps {
    kwadranten: FactsheetKwadrant[];
    toonRangKolom: boolean;
    onSelectThema: (themaId: number) => void;
}

function berekenNormatieveBalk(score: number | null): { left: string; width: string } | null {
    if (score === null || score === undefined) return null;
    const begrensd = Math.max(1, Math.min(8, score));
    const pct = ((begrensd - 1) / 7) * 100;
    if (Math.abs(pct - 50) < 1.5) {
        return { left: '48.5%', width: '3%' };
    }
    if (pct >= 50) {
        return { left: '50%', width: `${pct - 50}%` };
    }
    return { left: `${pct}%`, width: `${50 - pct}%` };
}

export const ThemaBenchmarkBalken: React.FC<ThemaBenchmarkBalkenProps> = ({
    kwadranten,
    toonRangKolom,
    onSelectThema,
}) => {
    if (!kwadranten.length) return null;

    const renderThemaRij = (thema: FactsheetThema) => {
        const heeftScore = thema.klasse !== null && thema.score !== null;
        const normBalk = !thema.is_neutraal ? berekenNormatieveBalk(thema.score) : null;
        const neutraleBreedte =
            thema.is_neutraal && thema.score !== null
                ? `${Math.max(6, (Math.min(8, Math.max(1, thema.score)) / 8) * 100)}%`
                : '0%';

        return (
            <button
                key={thema.thema_id}
                type="button"
                className="factsheet-thema-row"
                onClick={() => onSelectThema(thema.thema_id)}
                aria-label={`${thema.thema_naam}: ${
                    heeftScore ? `Klasse ${thema.klasse}, ${thema.duiding}` : 'Geen score'
                }. Klik om onderliggende indicatoren te bekijken.`}
            >
                <span className="factsheet-thema-name">
                    <ChevronRight size={15} aria-hidden="true" style={{ color: 'var(--color-text-secondary)', flexShrink: 0 }} />
                    <span>{thema.thema_naam}</span>
                </span>

                <div className="factsheet-bar-track" aria-hidden="true">
                    {!thema.is_neutraal && <div className="factsheet-bar-midline" />}
                    {heeftScore && !thema.is_neutraal && normBalk && (
                        <div
                            className="factsheet-bar-fill"
                            style={{
                                left: normBalk.left,
                                width: normBalk.width,
                                backgroundColor: thema.klasse_kleur,
                            }}
                        />
                    )}
                    {heeftScore && thema.is_neutraal && (
                        <div
                            className="factsheet-bar-fill"
                            style={{
                                left: 0,
                                width: neutraleBreedte,
                                backgroundColor: thema.klasse_kleur,
                            }}
                        />
                    )}
                </div>

                <div>
                    {heeftScore ? (
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
                    ) : (
                        <span className="factsheet-klasse-badge" style={{ color: 'var(--color-text-secondary)' }}>
                            Geen voldoende data
                        </span>
                    )}
                </div>

                <div className="factsheet-rang-cell">
                    {toonRangKolom ? (
                        thema.is_neutraal ? (
                            <span title="Samenstelling is beschrijvend en heeft geen goed/slecht-ranglijst">—</span>
                        ) : thema.rang ? (
                            <span title={`Positie ${thema.rang.positie} van ${thema.rang.totaal_met_score} buurten met voldoende dekking`}>
                                #{thema.rang.positie} van {thema.rang.totaal_met_score}
                            </span>
                        ) : (
                            <span title="Onvoldoende indicatordekking voor een betrouwbare rangpositie">—</span>
                        )
                    ) : null}
                </div>
            </button>
        );
    };

    return (
        <section className="factsheet-card" aria-labelledby="factsheet-themas-titel">
            <div className="factsheet-section-header">
                <div>
                    <h2 id="factsheet-themas-titel" className="factsheet-section-title">
                        Thema-overzicht (Kompas-percentielklassen 1–8)
                    </h2>
                    <p className="factsheet-section-subtitle">
                        Klasse 1 = ongunstigste 12,5% · middenlijn (4,5) = mediaan van de referentie · Klasse 8 = gunstigste 12,5%. Klik op een thema voor de detailtabel.
                    </p>
                </div>
            </div>

            {kwadranten.map((kw) => (
                <div key={kw.kwadrant_id} className="factsheet-kwadrant-group">
                    <div className="factsheet-kwadrant-header">
                        <div className="factsheet-kwadrant-title">
                            <span
                                className="factsheet-klasse-dot"
                                style={{ backgroundColor: kw.kwadrant_kleur }}
                                aria-hidden="true"
                            />
                            <span>{kw.kwadrant_naam}</span>
                            {kw.is_neutraal && (
                                <span style={{ fontSize: '0.76rem', fontWeight: 400, color: 'var(--color-text-secondary)' }}>
                                    (beschrijvend / neutraal — geen goed of slecht)
                                </span>
                            )}
                        </div>
                        {toonRangKolom && !kw.is_neutraal && (
                            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                                Rang in gemeente
                            </span>
                        )}
                    </div>
                    <div>{kw.themas.map(renderThemaRij)}</div>
                </div>
            ))}
        </section>
    );
};

