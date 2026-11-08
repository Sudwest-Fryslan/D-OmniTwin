import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FactsheetPage } from './FactsheetPage';
import { gebiedenAPI, organisatieAPI, reportAPI } from '../services/api';
import type { FactsheetPayload } from '../types';

const voorbeeldPayload: FactsheetPayload = {
    titel: 'Workum',
    is_meervoudig: false,
    is_waterbuurt: false,
    totaal_geselecteerd: 1,
    aantal_actieve_buurten: 1,
    geselecteerde_buurten: [{ id: 'BU00800200', naam: 'Workum', is_waterbuurt: false, inwoners: 4430 }],
    waterbuurten_uitgesloten: [],
    gemeente_code: '0080',
    gemeente_naam: 'Testgemeente',
    referentie_modus: 'gemeente',
    referentie_label: '⌀ Buurtgemiddelde gemeente Testgemeente',
    n_referentie_buurten: 8,
    config_id: 1,
    hero: {
        inwoners: { waarde: 4430, jaar: 2024, aantal_buurten_met_data: 1 },
        huishoudens: { waarde: 1985, jaar: 2024, aantal_buurten_met_data: 1 },
        woningen: { waarde: 2110, jaar: 2025, aantal_buurten_met_data: 1 },
        bouwperiodes: [
            { label: 'Vóór 1915', aantal: 460, percentage: 22.0 },
            { label: '1915–1945', aantal: 335, percentage: 16.0 },
            { label: '1945–1984', aantal: 860, percentage: 41.0 },
            { label: 'Vanaf 1985', aantal: 440, percentage: 21.0 },
        ],
        bouwperiodes_jaar: 2024,
    },
    contour_kaart: {
        view_box: '0 0 400 320',
        achtergrond_paden: [{ id: 'BU00800100', naam: 'Noord', d: 'M 10 10 L 50 10 L 50 50 Z' }],
        geselecteerde_paden: [{ id: 'BU00800200', naam: 'Workum', d: 'M 60 10 L 100 10 L 100 50 Z' }],
        ontbrekende_geometrie_buurten: [],
    },
    kwadranten: [
        {
            kwadrant_id: 1,
            kwadrant_naam: 'Kwaliteit fysieke leefomgeving',
            kwadrant_kleur: '#10b981',
            is_neutraal: false,
            klasse: 7,
            score: 7.0,
            klasse_kleur: '#0077b6',
            duiding: 'Gunstig',
            themas: [
                {
                    thema_id: 10,
                    thema_naam: 'Openbare ruimte',
                    is_neutraal: false,
                    klasse: 7,
                    score: 7.0,
                    klasse_kleur: '#0077b6',
                    duiding: 'Gunstig',
                    aantal_indicatoren_met_score: 2,
                    aantal_indicatoren_totaal: 3,
                    rang: { positie: 2, totaal_met_score: 8, min_indicatoren_vereist: 1 },
                    onderdelen: [
                        {
                            onderdeel_id: 100,
                            onderdeel_naam: 'Klimaat & groen',
                            is_neutraal: false,
                            klasse: 7,
                            score: 7.0,
                            klasse_kleur: '#0077b6',
                            duiding: 'Gunstig',
                            aantal_indicatoren_met_score: 2,
                            indicatoren: [
                                {
                                    indicator_uuid: 'u-koele-plek',
                                    naam: 'Afstand tot koele plek',
                                    eenheid: 'm',
                                    polariteit: 'lager_is_beter',
                                    is_aantal: false,
                                    is_neutraal: false,
                                    status: 'ok',
                                    jaar: 2024,
                                    waarde: 140,
                                    waarde_per_buurt: null,
                                    ref_gemiddelde: 210,
                                    verschil: -70,
                                    n_referentie: 8,
                                    klasse: 7,
                                    score: 7.0,
                                    klasse_kleur: '#0077b6',
                                    duiding: 'Gunstig',
                                    historie: [
                                        { jaar: 2020, waarde: 205 },
                                        { jaar: 2024, waarde: 140 },
                                    ],
                                    trend: {
                                        richting: 'dalend',
                                        duiding: 'gunstig',
                                        delta: -65,
                                        van_jaar: 2020,
                                        tot_jaar: 2024,
                                        label: '2020: 205 m → 2024: 140 m',
                                    },
                                    bron: 'SWF',
                                },
                                {
                                    indicator_uuid: 'u-bushaltes',
                                    naam: 'Aantal bushaltes',
                                    eenheid: 'aantal',
                                    polariteit: 'neutraal',
                                    is_aantal: true,
                                    is_neutraal: true,
                                    status: 'context_aantal',
                                    jaar: 2024,
                                    waarde: 12,
                                    waarde_per_buurt: null,
                                    ref_gemiddelde: 8.4,
                                    verschil: 3.6,
                                    n_referentie: 8,
                                    klasse: null,
                                    score: null,
                                    klasse_kleur: '#94A3B8',
                                    duiding: 'Context (aantal)',
                                    historie: [],
                                    trend: null,
                                    bron: 'OSM',
                                },
                                {
                                    indicator_uuid: 'u-klein',
                                    naam: 'Kleine-n meldingen',
                                    eenheid: '%',
                                    polariteit: 'lager_is_beter',
                                    is_aantal: false,
                                    is_neutraal: false,
                                    status: 'onderdrukt',
                                    jaar: null,
                                    waarde: null,
                                    waarde_per_buurt: null,
                                    ref_gemiddelde: 12.0,
                                    verschil: null,
                                    n_referentie: 7,
                                    klasse: null,
                                    score: null,
                                    klasse_kleur: '#94A3B8',
                                    duiding: 'Afgeschermd (kleine aantallen)',
                                    historie: [],
                                    trend: null,
                                    bron: 'SWF',
                                },
                            ],
                        },
                    ],
                },
            ],
        },
        {
            kwadrant_id: 4,
            kwadrant_naam: 'Samenstelling',
            kwadrant_kleur: '#64748b',
            is_neutraal: true,
            klasse: 5,
            score: 5.0,
            klasse_kleur: '#4292c6',
            duiding: 'Midden (neutraal)',
            themas: [
                {
                    thema_id: 40,
                    thema_naam: 'Bebouwing',
                    is_neutraal: true,
                    klasse: 5,
                    score: 5.0,
                    klasse_kleur: '#4292c6',
                    duiding: 'Midden (neutraal)',
                    aantal_indicatoren_met_score: 1,
                    aantal_indicatoren_totaal: 1,
                    rang: null,
                    onderdelen: [],
                },
            ],
        },
    ],
    sterke_kanten: [
        {
            onderdeel_id: 100,
            onderdeel_naam: 'Klimaat & groen',
            thema_id: 10,
            thema_naam: 'Openbare ruimte',
            kwadrant_naam: 'Kwaliteit fysieke leefomgeving',
            klasse: 7,
            score: 7.0,
            klasse_kleur: '#0077b6',
            duiding: 'Gunstig',
            aantal_indicatoren_met_score: 2,
            voorbeeld_indicator: {
                naam: 'Afstand tot koele plek',
                waarde: 140,
                ref_gemiddelde: 210,
                eenheid: 'm',
                jaar: 2024,
                klasse: 7,
            },
        },
    ],
    aandachtspunten: [],
    klassen_legenda: [],
    klassen_legenda_neutraal: [],
    meldingen: [],
};

describe('FactsheetPage (#441)', () => {
    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
    });

    it('toont buurtzoeker wanneer geen gebieden-parameter is meegegeven', () => {
        vi.spyOn(organisatieAPI, 'get').mockResolvedValue({
            data: { benchmark_provincie: 'Fryslân' },
        } as never);
        vi.spyOn(gebiedenAPI, 'zoekGebieden').mockResolvedValue({
            data: { gebieden: [], totaal: 0 },
        } as never);

        render(
            <MemoryRouter initialEntries={['/rapport/factsheet']}>
                <Routes>
                    <Route path="/rapport/factsheet" element={<FactsheetPage />} />
                </Routes>
            </MemoryRouter>
        );

        expect(screen.getByRole('heading', { name: 'Gebiedsfactsheet' })).toBeInTheDocument();
        expect(screen.getByLabelText('Zoek een buurt')).toBeInTheDocument();
    });

    it('rendert Hero, contour-SVG, themabalken met rang, Top 3 en detailtabel voor 1 buurt', async () => {
        vi.spyOn(organisatieAPI, 'get').mockResolvedValue({
            data: { benchmark_provincie: 'Fryslân' },
        } as never);
        const getSpy = vi.spyOn(reportAPI, 'getFactsheet').mockResolvedValue({
            data: voorbeeldPayload,
        } as never);

        const user = userEvent.setup();

        render(
            <MemoryRouter initialEntries={['/rapport/factsheet?gebieden=BU00800200']}>
                <Routes>
                    <Route path="/rapport/factsheet" element={<FactsheetPage />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: /Workum/ })).toBeInTheDocument();
        });

        expect(getSpy).toHaveBeenCalledWith('BU00800200', {
            referentie: 'gemeente',
            gemeente_code: undefined,
        });

        // Hero KPI's met individueel peiljaar & React SVG-contourkaart
        expect(screen.getByText('4.430')).toBeInTheDocument();
        expect(screen.getByText('(2025)')).toBeInTheDocument();
        expect(
            screen.getByRole('img', { name: /Contourkaart van Workum binnen gemeente Testgemeente/ })
        ).toBeInTheDocument();

        // Gemeentelijke rang op normatief thema (#2 van 8) met verklarende tooltip en neutrale Samenstelling zonder rang
        const rangItems = screen.getAllByText('#2 van 8');
        expect(rangItems.length).toBeGreaterThan(0);
        expect(rangItems[0].getAttribute('title')).toMatch(/onafgeronde themascore/i);
        expect(screen.getAllByText(/Kl\. 5 · Midden \(neutraal\)/).length).toBeGreaterThan(0);

        // Top 3 Sterke kanten op Onderdeel-niveau
        expect(screen.getByText(/1\. Klimaat & groen/)).toBeInTheDocument();

        // Detailtabel is geopend voor thema 10: toont polariteitsbewuste trend, context (aantal) en onderdrukt
        expect(screen.getByText('context (aantal)')).toBeInTheDocument();
        expect(screen.getByText('Afgeschermd (< min. n)')).toBeInTheDocument();
        expect(screen.getByText('↘ Gunstig')).toBeInTheDocument();

        // Wissel referentie naar Provincie Fryslân
        const provBtn = await screen.findByRole('button', { name: 'Provincie Fryslân' });
        await user.click(provBtn);

        await waitFor(() => {
            expect(getSpy).toHaveBeenCalledWith('BU00800200', {
                referentie: 'fryslan',
                gemeente_code: undefined,
            });
        });
    });

    it('roept postFactsheet aan bij meervoudige buurtselectie en verbergt gemeenterang', async () => {
        vi.spyOn(organisatieAPI, 'get').mockResolvedValue({
            data: { benchmark_provincie: 'Fryslân' },
        } as never);
        const postSpy = vi.spyOn(reportAPI, 'postFactsheet').mockResolvedValue({
            data: {
                ...voorbeeldPayload,
                titel: 'Zuidwesthoek',
                is_meervoudig: true,
                aantal_actieve_buurten: 2,
                kwadranten: voorbeeldPayload.kwadranten.map((kw) => ({
                    ...kw,
                    themas: kw.themas.map((th) => ({ ...th, rang: null })),
                })),
            },
        } as never);

        render(
            <MemoryRouter initialEntries={['/rapport/factsheet?gebieden=BU00800100,BU00800200&naam=Zuidwesthoek']}>
                <Routes>
                    <Route path="/rapport/factsheet" element={<FactsheetPage />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: 'Zuidwesthoek' })).toBeInTheDocument();
        });

        expect(postSpy).toHaveBeenCalledWith({
            gebied_ids: ['BU00800100', 'BU00800200'],
            referentie: 'gemeente',
            gemeente_code: undefined,
            deelgebied_naam: 'Zuidwesthoek',
        });
        expect(screen.queryByText('#2 van 8')).not.toBeInTheDocument();
    });
});
