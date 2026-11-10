import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MultiGebiedPage } from './MultiGebiedPage';
import { organisatieAPI, reportAPI } from '../services/api';

describe('MultiGebiedPage', () => {
    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
    });

    it('toont Neutraal in plaats van z̄=null voor Samenstelling', async () => {
        vi.spyOn(organisatieAPI, 'get').mockResolvedValue({
            data: { benchmark_provincie: 'Fryslân', korte_naam: 'SWF', standaard_gemeente_code: '1900' },
        } as never);
        vi.spyOn(reportAPI, 'getMultiGebiedGeoJSON').mockResolvedValue({
            data: { type: 'FeatureCollection', features: [] },
        } as never);
        vi.spyOn(reportAPI, 'getMultiGebied').mockResolvedValue({
            data: {
                deelgebied_naam: 'Sneek',
                referentie_label: 'Gemeente Súdwest-Fryslân',
                referentie_modus: 'gemeente',
                totaal_buurten: 2,
                buurten_met_data: 2,
                buurten_analyse: [],
                thema_aggregaat: {
                    'Kwaliteit van leven': { gem_zscore: -0.62, n_uitschieters: 3, n_datapunten: 12 },
                    Samenstelling: { gem_zscore: null, n_uitschieters: 4, n_datapunten: 10 },
                },
                top_uitschieters: [],
            },
        } as never);

        render(
            <MemoryRouter initialEntries={['/rapport/multi-gebied?gebieden=BU19000101,BU19000102&naam=Sneek']}>
                <Routes>
                    <Route path="/rapport/multi-gebied" element={<MultiGebiedPage />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText(/z̄=-0.62 · 3 uitschieters/)).toBeInTheDocument();
        });

        expect(screen.getByText(/Neutraal · 4 uitschieters/)).toBeInTheDocument();
        expect(screen.queryByText(/z̄=null/)).not.toBeInTheDocument();
    });
});

