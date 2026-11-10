import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { DeelgebiedPage } from './DeelgebiedPage';
import { organisatieAPI, reportAPI } from '../services/api';

describe('DeelgebiedPage', () => {
    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
    });

    it('rendert kwadrant Samenstelling foutloos wanneer gem_zscore null is', async () => {
        vi.spyOn(organisatieAPI, 'get').mockResolvedValue({
            data: { benchmark_provincie: 'Fryslân' },
        } as never);
        vi.spyOn(globalThis, 'fetch').mockResolvedValue({
            ok: false,
            json: async () => null,
        } as Response);
        vi.spyOn(reportAPI, 'getMultiGebiedGeoJSON').mockResolvedValue({
            data: { type: 'FeatureCollection', features: [] },
        } as never);
        vi.spyOn(reportAPI, 'getDeelgebied').mockResolvedValue({
            data: {
                deelgebied_naam: 'Sneek',
                referentie_label: 'Gemeente Súdwest-Fryslân',
                referentie_modus: 'gemeente',
                gemeente_code: '1900',
                gemeente_naam: 'Súdwest-Fryslân',
                totaal_buurten: 2,
                buurten_met_data: 2,
                geselecteerde_buurten: [
                    { id: 'BU19000101', naam: 'Sneek binnen de grachten', inwoners: 1500, gewicht: 0.5, is_fallback: false },
                    { id: 'BU19000102', naam: 'Stationsbuurt', inwoners: 1500, gewicht: 0.5, is_fallback: false },
                ],
                kwadranten: [
                    {
                        kwadrant_naam: 'Kwaliteit van leven',
                        kwadrant_kleur: '#10b981',
                        gem_zscore: -0.45,
                        n_indicatoren: 5,
                        n_uitschieters: 2,
                        n_aandachtspunten: 3,
                        n_kansen: 2,
                        themas: [],
                    },
                    {
                        kwadrant_naam: 'Samenstelling',
                        kwadrant_kleur: '#3B82F6',
                        gem_zscore: null,
                        n_indicatoren: 12,
                        n_uitschieters: 4,
                        n_aandachtspunten: 5,
                        n_kansen: 7,
                        themas: [
                            {
                                thema_naam: 'Bevolking',
                                totaal_indicatoren: 12,
                                totaal_aandachtspunten: 5,
                                totaal_kansen: 7,
                                top10_aandachtspunten: [],
                                top10_kansen: [],
                            },
                        ],
                    },
                ],
                methodologie: {
                    aggregatie: 'inwonergewogen',
                    gewicht_bron: 'CBS Inwoners',
                    referentie: 'Gemeente Súdwest-Fryslân',
                    referentie_modus: 'gemeente',
                    gemeente_code: '1900',
                    gemeente_naam: 'Súdwest-Fryslân',
                    totaal_geselecteerde_buurten: 2,
                    waterbuurten_uitgesloten: [],
                    actieve_buurten_telling: 2,
                    fallback_buurten: [],
                    nul_inwoners_buurten: [],
                    totaal_inwoners_gebied: 3000,
                    z_score_formule: '(x - gem) / std',
                    statistisch_effect: 'gewogen',
                    scoringtype_disclaimer: 'polariteitsbewust',
                },
                bronverantwoording: [],
            },
        } as never);

        render(
            <MemoryRouter initialEntries={['/rapport/deelgebied?gebieden=BU19000101,BU19000102&naam=Sneek']}>
                <Routes>
                    <Route path="/rapport/deelgebied" element={<DeelgebiedPage />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByRole('heading', { name: 'Sneek' })).toBeInTheDocument();
        });

        expect(screen.getByText('-0.45 Z')).toBeInTheDocument();
        expect(screen.getByText('Neutraal')).toBeInTheDocument();
        expect(screen.getByText(/Beschrijvend \(geen normatief gemiddelde\)/)).toBeInTheDocument();
    });
});

