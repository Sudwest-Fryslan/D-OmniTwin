import React from 'react';
import type { FactsheetPayload } from '../../types';
import { provincieNaam } from '../../hooks/useBenchmarkProvincie';

const BAG_KLEUREN = ['#0284c7', '#0ea5e9', '#38bdf8', '#93c5fd'];

interface FactsheetHeroProps {
    data: FactsheetPayload;
    referentie: 'gemeente' | 'fryslan';
    benchmarkProvincie: string | null;
    onReferentieChange: (nieuw: 'gemeente' | 'fryslan') => void;
}

function fmtGetal(n: number | null | undefined): string {
    if (n === null || n === undefined) return '—';
    return n.toLocaleString('nl-NL');
}

export const FactsheetHero: React.FC<FactsheetHeroProps> = ({
    data,
    referentie,
    benchmarkProvincie,
    onReferentieChange,
}) => {
    const { hero, contour_kaart } = data;
    const heeftKaartPaden =
        contour_kaart.achtergrond_paden.length > 0 || contour_kaart.geselecteerde_paden.length > 0;
    const eersteId = !data.is_meervoudig && data.geselecteerde_buurten.length === 1
        ? data.geselecteerde_buurten[0].id
        : null;

    return (
        <section className="factsheet-card" aria-labelledby="factsheet-hoofdtitel">
            <div className="factsheet-hero-grid">
                <div>
                    <div className="factsheet-hero-top">
                        <span className="factsheet-eyebrow">
                            Gebiedsfactsheet{data.is_meervoudig ? ` · ${data.aantal_actieve_buurten} buurten` : ''}
                        </span>
                        <div className="factsheet-ref-toggle" role="group" aria-label="Referentiegebied kiezen">
                            <button
                                type="button"
                                className={`factsheet-ref-btn ${referentie === 'gemeente' ? 'active' : ''}`}
                                aria-pressed={referentie === 'gemeente'}
                                onClick={() => onReferentieChange('gemeente')}
                            >
                                Gemeente
                            </button>
                            <button
                                type="button"
                                className={`factsheet-ref-btn ${referentie === 'fryslan' ? 'active' : ''}`}
                                aria-pressed={referentie === 'fryslan'}
                                onClick={() => onReferentieChange('fryslan')}
                            >
                                {provincieNaam(benchmarkProvincie)}
                            </button>
                        </div>
                    </div>

                    <h1 id="factsheet-hoofdtitel" className="factsheet-title">
                        {data.titel}
                        {eersteId ? (
                            <span style={{ fontWeight: 400, fontSize: '1.05rem', color: 'var(--color-text-secondary)', marginLeft: '0.5rem' }}>
                                ({eersteId})
                            </span>
                        ) : null}
                    </h1>

                    <p className="factsheet-meta">
                        Gemeente {data.gemeente_naam} · <strong>{data.referentie_label}</strong>
                    </p>

                    <div className="factsheet-kpi-grid">
                        <div className="factsheet-kpi-box">
                            <div className="factsheet-kpi-label">
                                <span>Inwoners</span>
                                {hero.inwoners?.jaar ? <span>({hero.inwoners.jaar})</span> : null}
                            </div>
                            <div className="factsheet-kpi-value">{fmtGetal(hero.inwoners?.waarde)}</div>
                        </div>

                        <div className="factsheet-kpi-box">
                            <div className="factsheet-kpi-label">
                                <span>Huishoudens</span>
                                {hero.huishoudens?.jaar ? <span>({hero.huishoudens.jaar})</span> : null}
                            </div>
                            <div className="factsheet-kpi-value">{fmtGetal(hero.huishoudens?.waarde)}</div>
                        </div>

                        <div className="factsheet-kpi-box">
                            <div className="factsheet-kpi-label">
                                <span>Woningen</span>
                                {hero.woningen?.jaar ? <span>({hero.woningen.jaar})</span> : null}
                            </div>
                            <div className="factsheet-kpi-value">{fmtGetal(hero.woningen?.waarde)}</div>
                        </div>
                    </div>

                    {hero.bouwperiodes.length > 0 && (
                        <div className="factsheet-bag-block">
                            <div className="factsheet-kpi-label">
                                <span style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                                    Woningbouwperiodes (BAG{hero.bouwperiodes_jaar ? ` ${hero.bouwperiodes_jaar}` : ''})
                                </span>
                            </div>
                            <div className="factsheet-bag-bar" aria-hidden="true">
                                {hero.bouwperiodes.map((bp, idx) => (
                                    <div
                                        key={bp.label}
                                        style={{
                                            width: `${bp.percentage}%`,
                                            backgroundColor: BAG_KLEUREN[idx % BAG_KLEUREN.length],
                                        }}
                                        title={`${bp.label}: ${bp.percentage.toLocaleString('nl-NL')}% (${fmtGetal(bp.aantal)})`}
                                    />
                                ))}
                            </div>
                            <div className="factsheet-bag-legend">
                                {hero.bouwperiodes.map((bp, idx) => (
                                    <span key={bp.label} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                                        <span
                                            className="factsheet-klasse-dot"
                                            style={{ backgroundColor: BAG_KLEUREN[idx % BAG_KLEUREN.length] }}
                                            aria-hidden="true"
                                        />
                                        <span>
                                            {bp.label}: <strong>{bp.percentage.toLocaleString('nl-NL', { minimumFractionDigits: 0, maximumFractionDigits: 1 })}%</strong>
                                        </span>
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                <div className="factsheet-contour-wrap" aria-label="Ligging binnen de gemeente">
                    {heeftKaartPaden ? (
                        <>
                            <svg
                                className="factsheet-contour-svg"
                                viewBox={contour_kaart.view_box}
                                role="img"
                                aria-label={`Contourkaart van ${data.titel} binnen gemeente ${data.gemeente_naam}`}
                            >
                                <title>{`Ligging van ${data.titel} in gemeente ${data.gemeente_naam}`}</title>
                                <g>
                                    {contour_kaart.achtergrond_paden.map((pad) => (
                                        <path
                                            key={pad.id}
                                            d={pad.d}
                                            fillRule="evenodd"
                                            className="factsheet-contour-bg-path"
                                        >
                                            <title>{pad.naam}</title>
                                        </path>
                                    ))}
                                </g>
                                <g>
                                    {contour_kaart.geselecteerde_paden.map((pad) => (
                                        <path
                                            key={pad.id}
                                            d={pad.d}
                                            fillRule="evenodd"
                                            className="factsheet-contour-sel-path"
                                        >
                                            <title>{`${pad.naam} (geselecteerd)`}</title>
                                        </path>
                                    ))}
                                </g>
                            </svg>
                            <div className="factsheet-contour-caption">
                                <span>Ligging in {data.gemeente_naam}</span>
                                <span>
                                    {contour_kaart.geselecteerde_paden.length} vlak{contour_kaart.geselecteerde_paden.length === 1 ? '' : 'ken'} getoond
                                </span>
                            </div>
                        </>
                    ) : (
                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                flex: 1,
                                color: 'var(--color-text-secondary)',
                                fontSize: '0.85rem',
                                textAlign: 'center',
                                padding: '1rem',
                            }}
                        >
                            Geen kaartgeometrie beschikbaar voor deze selectie.
                        </div>
                    )}
                </div>
            </div>
        </section>
    );
};
