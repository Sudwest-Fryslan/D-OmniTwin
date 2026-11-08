import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertTriangle, Info, Search, TrendingDown, TrendingUp } from 'lucide-react';
import { gebiedenAPI, reportAPI } from '../services/api';
import { useBenchmarkProvincie } from '../hooks/useBenchmarkProvincie';
import type { FactsheetPayload, FactsheetTopOnderdeel, GebiedListItem } from '../types';
import { FactsheetHero } from '../components/reports/FactsheetHero';
import { ThemaBenchmarkBalken } from '../components/reports/ThemaBenchmarkBalken';
import { ThemaDrilldown } from '../components/reports/ThemaDrilldown';
import '../styles/factsheet.css';

function fmtVoorbeeldWaarde(waarde: number | null, eenheid: string): string {
    if (waarde === null || waarde === undefined) return '—';
    const tekst = waarde.toLocaleString('nl-NL', { minimumFractionDigits: 0, maximumFractionDigits: 1 });
    const e = (eenheid || '').trim();
    if (!e || e.toLowerCase() === 'aantal') return tekst;
    if (e === '%') return `${tekst}%`;
    return `${tekst} ${e}`;
}

export const FactsheetPage: React.FC = () => {
    const [searchParams, setSearchParams] = useSearchParams();
    const benchmarkProvincie = useBenchmarkProvincie();

    const gebiedIds = useMemo(() => {
        const ruw = searchParams.get('gebieden') || searchParams.get('gebied') || '';
        return ruw
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean);
    }, [searchParams]);

    const deelgebiedNaam = searchParams.get('naam') || '';
    const gemeenteCode = searchParams.get('gemeente') || undefined;
    const refParam = searchParams.get('ref');
    const initieleRef: 'gemeente' | 'fryslan' = refParam === 'fryslan' ? 'fryslan' : 'gemeente';

    const [referentie, setReferentie] = useState<'gemeente' | 'fryslan'>(initieleRef);
    const [data, setData] = useState<FactsheetPayload | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [openThemaIds, setOpenThemaIds] = useState<Set<number>>(new Set());

    // Buurtzoeker wanneer de pagina zonder ?gebieden= wordt geopend
    const [zoekTerm, setZoekTerm] = useState('');
    const [zoekResultaten, setZoekResultaten] = useState<GebiedListItem[]>([]);
    const [bezigMetZoeken, setBezigMetZoeken] = useState(false);

    useEffect(() => {
        setReferentie(initieleRef);
    }, [initieleRef]);

    useEffect(() => {
        if (gebiedIds.length === 0) {
            setData(null);
            setError(null);
            return;
        }

        let actief = true;
        setLoading(true);
        setError(null);

        const aanroep =
            gebiedIds.length === 1 && !deelgebiedNaam
                ? reportAPI.getFactsheet(gebiedIds[0], {
                      referentie,
                      gemeente_code: gemeenteCode,
                  })
                : reportAPI.postFactsheet({
                      gebied_ids: gebiedIds,
                      referentie,
                      gemeente_code: gemeenteCode,
                      deelgebied_naam: deelgebiedNaam || undefined,
                  });

        aanroep
            .then((res) => {
                if (!actief) return;
                const payload = res.data;
                setData(payload);

                // Standaard het eerste aandachtspunt-thema (of eerste thema) openklappen
                const eersteThemaId =
                    payload.aandachtspunten[0]?.thema_id ??
                    payload.sterke_kanten[0]?.thema_id ??
                    payload.kwadranten[0]?.themas[0]?.thema_id;
                setOpenThemaIds(eersteThemaId !== undefined ? new Set([eersteThemaId]) : new Set());
            })
            .catch((err: unknown) => {
                if (!actief) return;
                const detail =
                    (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail ||
                    (err as { message?: string })?.message ||
                    'Fout bij het laden van de Gebiedsfactsheet.';
                setError(detail);
                setData(null);
            })
            .finally(() => {
                if (actief) setLoading(false);
            });

        return () => {
            actief = false;
        };
    }, [gebiedIds, referentie, gemeenteCode, deelgebiedNaam]);

    useEffect(() => {
        if (!data) return;
        const vorigeTitel = document.title;
        document.title = `Gebiedsfactsheet — ${data.titel}`;
        return () => {
            document.title = vorigeTitel;
        };
    }, [data]);

    // Voor afdrukken: klap automatisch alle thema's open en herstel nadien
    useEffect(() => {
        if (!data) return;
        let bewaardeSet: Set<number> | null = null;
        const voorPrint = () => {
            bewaardeSet = new Set(openThemaIds);
            const alle = new Set<number>();
            for (const kw of data.kwadranten) {
                for (const th of kw.themas) {
                    alle.add(th.thema_id);
                }
            }
            setOpenThemaIds(alle);
        };
        const naPrint = () => {
            if (bewaardeSet) {
                setOpenThemaIds(bewaardeSet);
                bewaardeSet = null;
            }
        };
        window.addEventListener('beforeprint', voorPrint);
        window.addEventListener('afterprint', naPrint);
        return () => {
            window.removeEventListener('beforeprint', voorPrint);
            window.removeEventListener('afterprint', naPrint);
        };
    }, [data, openThemaIds]);

    const handleReferentieChange = useCallback(
        (nieuw: 'gemeente' | 'fryslan') => {
            setReferentie(nieuw);
            const volgende = new URLSearchParams(searchParams);
            if (nieuw === 'gemeente') {
                volgende.delete('ref');
            } else {
                volgende.set('ref', nieuw);
            }
            setSearchParams(volgende, { replace: true });
        },
        [searchParams, setSearchParams]
    );

    const springNaarThema = useCallback((themaId: number) => {
        setOpenThemaIds((prev) => {
            const kopie = new Set(prev);
            kopie.add(themaId);
            return kopie;
        });
        window.requestAnimationFrame(() => {
            const el = document.getElementById(`factsheet-thema-${themaId}`);
            if (el && typeof el.scrollIntoView === 'function') {
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }, []);

    const toggleThema = useCallback((themaId: number) => {
        setOpenThemaIds((prev) => {
            const kopie = new Set(prev);
            if (kopie.has(themaId)) {
                kopie.delete(themaId);
            } else {
                kopie.add(themaId);
            }
            return kopie;
        });
    }, []);

    const openAlleThemas = useCallback(() => {
        if (!data) return;
        const alle = new Set<number>();
        for (const kw of data.kwadranten) {
            for (const th of kw.themas) {
                alle.add(th.thema_id);
            }
        }
        setOpenThemaIds(alle);
    }, [data]);

    const sluitAlleThemas = useCallback(() => {
        setOpenThemaIds(new Set());
    }, []);

    useEffect(() => {
        if (gebiedIds.length > 0 || zoekTerm.trim().length < 2) {
            setZoekResultaten([]);
            return;
        }
        let actief = true;
        setBezigMetZoeken(true);
        gebiedenAPI
            .zoekGebieden(zoekTerm.trim())
            .then((res) => {
                if (!actief) return;
                // Toon bij voorkeur buurten (BU...)
                const buurten = res.data.gebieden.filter((g) => g.id.toUpperCase().startsWith('BU'));
                setZoekResultaten(buurten.length > 0 ? buurten : res.data.gebieden);
            })
            .catch(() => {
                if (actief) setZoekResultaten([]);
            })
            .finally(() => {
                if (actief) setBezigMetZoeken(false);
            });
        return () => {
            actief = false;
        };
    }, [zoekTerm, gebiedIds.length]);

    // ── Lege staat: kies een buurt ──────────────────────────────────────────
    if (gebiedIds.length === 0) {
        return (
            <main className="factsheet-page">
                <section className="factsheet-card">
                    <h1 className="factsheet-title" style={{ fontSize: '1.4rem' }}>
                        Gebiedsfactsheet
                    </h1>
                    <p className="factsheet-meta">
                        Selecteer een buurt op de kaart (via de knop <strong>Rapport</strong>) of zoek hieronder op buurtnaam of CBS-buurtcode.
                    </p>
                    <div style={{ maxWidth: '460px', position: 'relative' }}>
                        <label htmlFor="factsheet-buurt-zoek" style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                            Zoek een buurt
                        </label>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Search size={18} aria-hidden="true" style={{ color: 'var(--color-text-secondary)' }} />
                            <input
                                id="factsheet-buurt-zoek"
                                type="search"
                                className="form-input"
                                placeholder="Bijv. Workum of BU1900..."
                                value={zoekTerm}
                                onChange={(e) => setZoekTerm(e.target.value)}
                                style={{ width: '100%', padding: '0.5rem 0.75rem' }}
                            />
                        </div>
                        {bezigMetZoeken && (
                            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginTop: '0.4rem' }}>
                                Bezig met zoeken...
                            </p>
                        )}
                        {zoekResultaten.length > 0 && (
                            <ul
                                style={{
                                    listStyle: 'none',
                                    marginTop: '0.5rem',
                                    border: '1px solid var(--color-border)',
                                    borderRadius: 'var(--radius-md)',
                                    overflow: 'hidden',
                                }}
                            >
                                {zoekResultaten.map((g) => (
                                    <li key={g.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                                        <button
                                            type="button"
                                            onClick={() => setSearchParams({ gebieden: g.id })}
                                            style={{
                                                width: '100%',
                                                textAlign: 'left',
                                                padding: '0.55rem 0.85rem',
                                                background: 'var(--color-surface-light)',
                                                border: 'none',
                                                color: 'var(--color-text-primary)',
                                                cursor: 'pointer',
                                                fontFamily: 'inherit',
                                            }}
                                        >
                                            <strong>{g.naam}</strong>{' '}
                                            <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>
                                                ({g.id})
                                            </span>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                </section>
            </main>
        );
    }

    if (loading) {
        return (
            <main className="factsheet-page" aria-busy="true">
                <section className="factsheet-card">
                    <p style={{ color: 'var(--color-text-secondary)' }}>Gebiedsfactsheet wordt opgebouwd...</p>
                </section>
            </main>
        );
    }

    if (error) {
        return (
            <main className="factsheet-page">
                <section className="factsheet-card" role="alert">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--color-error)', marginBottom: '0.4rem' }}>
                        <AlertTriangle size={20} aria-hidden="true" />
                        <strong>Kon de Gebiedsfactsheet niet openen</strong>
                    </div>
                    <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>{error}</p>
                </section>
            </main>
        );
    }

    if (!data) return null;

    const toonRangKolom = !data.is_meervoudig && data.referentie_modus === 'gemeente';

    const renderTopKaart = (item: FactsheetTopOnderdeel, index: number) => (
        <button
            key={item.onderdeel_id}
            type="button"
            className="factsheet-top-item"
            onClick={() => springNaarThema(item.thema_id)}
        >
            <div className="factsheet-top-item-head">
                <strong>
                    {index + 1}. {item.onderdeel_naam}
                </strong>
                <span className="factsheet-klasse-badge">
                    <span
                        className="factsheet-klasse-dot"
                        style={{ backgroundColor: item.klasse_kleur }}
                        aria-hidden="true"
                    />
                    <span>
                        Kl. {item.klasse} · {item.duiding}
                    </span>
                </span>
            </div>
            <div className="factsheet-top-item-meta">
                Thema: <strong>{item.thema_naam}</strong> ({item.kwadrant_naam})
            </div>
            {item.voorbeeld_indicator && (
                <div className="factsheet-top-item-meta" style={{ marginTop: '0.2rem' }}>
                    Voorbeeld: {item.voorbeeld_indicator.naam} (
                    {fmtVoorbeeldWaarde(item.voorbeeld_indicator.waarde, item.voorbeeld_indicator.eenheid)} vs. gem.{' '}
                    {fmtVoorbeeldWaarde(item.voorbeeld_indicator.ref_gemiddelde, item.voorbeeld_indicator.eenheid)})
                </div>
            )}
        </button>
    );

    return (
        <main className="factsheet-page">
            {/* 1. Hero Header + React SVG Contourkaart */}
            <FactsheetHero
                data={data}
                referentie={referentie}
                benchmarkProvincie={benchmarkProvincie}
                onReferentieChange={handleReferentieChange}
            />

            {/* Eventuele aandachtsmeldingen (waterbuurt, ontbrekende geometrie) */}
            {data.meldingen.length > 0 && (
                <div className="factsheet-alert" role="status">
                    <Info size={18} aria-hidden="true" style={{ color: 'var(--color-primary)', flexShrink: 0, marginTop: '0.1rem' }} />
                    <div>
                        {data.meldingen.map((m, idx) => (
                            <p key={idx} style={{ marginBottom: idx < data.meldingen.length - 1 ? '0.25rem' : 0 }}>
                                {m}
                            </p>
                        ))}
                    </div>
                </div>
            )}

            {/* 2. Thema-benchmarkbalken (Ring 2) */}
            {!data.is_waterbuurt && (
                <ThemaBenchmarkBalken
                    kwadranten={data.kwadranten}
                    toonRangKolom={toonRangKolom}
                    onSelectThema={springNaarThema}
                />
            )}

            {/* 3. Top 3 Sterke kanten & Top 3 Aandachtspunten (Onderdeel-niveau / Ring 3) */}
            {!data.is_waterbuurt && (
                <section className="factsheet-card" aria-labelledby="factsheet-top3-titel">
                    <div className="factsheet-section-header">
                        <div>
                            <h2 id="factsheet-top3-titel" className="factsheet-section-title">
                                Belangrijkste sterke kanten & aandachtspunten (op onderdeel-niveau)
                            </h2>
                            <p className="factsheet-section-subtitle">
                                Geaggregeerde Kompas-onderdelen uit de drie normatieve kwadranten. Samenstelling telt niet normatief mee.
                            </p>
                        </div>
                    </div>

                    <div className="factsheet-top-grid">
                        <div>
                            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.45rem', marginBottom: '0.65rem' }}>
                                <TrendingUp size={17} aria-hidden="true" style={{ color: 'var(--color-success)' }} />
                                <span>Top 3 Sterke kanten (klasse ≥ 6)</span>
                            </h3>
                            {data.sterke_kanten.length > 0 ? (
                                <div className="factsheet-top-list">
                                    {data.sterke_kanten.map((item, idx) => renderTopKaart(item, idx))}
                                </div>
                            ) : (
                                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                                    Geen onderdelen in klasse 6, 7 of 8 ten opzichte van deze referentie.
                                </p>
                            )}
                        </div>

                        <div>
                            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.45rem', marginBottom: '0.65rem' }}>
                                <TrendingDown size={17} aria-hidden="true" style={{ color: 'var(--color-warning)' }} />
                                <span>Top 3 Aandachtspunten (klasse ≤ 3)</span>
                            </h3>
                            {data.aandachtspunten.length > 0 ? (
                                <div className="factsheet-top-list">
                                    {data.aandachtspunten.map((item, idx) => renderTopKaart(item, idx))}
                                </div>
                            ) : (
                                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                                    Geen onderdelen in klasse 1, 2 of 3 ten opzichte van deze referentie.
                                </p>
                            )}
                        </div>
                    </div>
                </section>
            )}

            {/* 4. Uitklapbare detailtabel met trendlijnen (Ring 3 & Ring 4) */}
            {!data.is_waterbuurt && (
                <ThemaDrilldown
                    kwadranten={data.kwadranten}
                    isMeervoudig={data.is_meervoudig}
                    openThemaIds={openThemaIds}
                    onToggleThema={toggleThema}
                    onOpenAlles={openAlleThemas}
                    onSluitAlles={sluitAlleThemas}
                />
            )}

            {/* Methodologische verantwoording */}
            <footer className="factsheet-card" style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
                <strong>Methodische toelichting:</strong> Scores zijn berekend volgens de Kompas-boom en percentielklassen 1–8 (elk 12,5% van de referentiegroep van landbuurten; klasse 8 = gunstigste 12,5%, klasse 1 = ongunstigste 12,5%). Waarden gebaseerd op te weinig waarnemingen zijn afgeschermd. Ruwe aantallen en het kwadrant <em>Samenstelling</em> wegen niet normatief mee.
            </footer>
        </main>
    );
};

