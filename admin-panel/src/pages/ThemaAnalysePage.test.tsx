import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ThemaAnalysePage } from './ThemaAnalysePage';
import { hierarchyAPI, reportAPI } from '../services/api';
import type { HierarchyResponse } from '../types';

const voorbeeldTree: HierarchyResponse = {
    config_id: 1,
    stats: { themas: 2, onderdelen: 2, indicatoren: 4 },
    tree: [
        {
            id: 'titel-0',
            naam: 'Kwaliteit fysieke leefomgeving',
            type: 'thema',
            children: [
                {
                    id: 'thema-0',
                    naam: 'Openbare ruimte',
                    type: 'thema',
                    children: [
                        {
                            id: 'ond-0',
                            naam: 'Groen en water',
                            type: 'onderdeel',
                            children: []
                        }
                    ]
                }
            ]
        },
        {
            id: 'titel-1',
            naam: 'Samenstelling',
            type: 'thema',
            children: [
                {
                    id: 'thema-1',
                    naam: 'Bevolking',
                    type: 'thema',
                    children: [
                        {
                            id: 'ond-1',
                            naam: 'Leeftijdsopbouw',
                            type: 'onderdeel',
                            children: []
                        }
                    ]
                }
            ]
        }
    ]
};

describe('ThemaAnalysePage (#453)', () => {
    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
    });

    it('laadt de cascading categorie-, thema- en onderdeel-opties via de publieke hierarchy API zonder 401', async () => {
        const getStandaardTreeSpy = vi.spyOn(hierarchyAPI, 'getStandaardTree').mockResolvedValue({
            data: voorbeeldTree
        } as any);

        const getThemaAnalyseSpy = vi.spyOn(reportAPI, 'getThemaAnalyse').mockResolvedValue({
            data: {
                rapport_type: 'thema_analyse',
                filter_beschrijving: 'Alle categorieën',
                deelgebied_naam: 'Sneek',
                referentie_label: 'Gemeentegemiddelde',
                referentie_modus: 'gemeente',
                totaal_buurten: 1,
                buurten_met_data: 1,
                buurten_analyse: []
            }
        } as any);

        vi.spyOn(reportAPI, 'getThemaAnalyseGeoJSON').mockResolvedValue({
            data: { type: 'FeatureCollection', metadata: {}, features: [] }
        } as any);

        render(
            <MemoryRouter initialEntries={['/rapport/thema-analyse?gebieden=BU19000101&naam=Sneek']}>
                <Routes>
                    <Route path="/rapport/thema-analyse" element={<ThemaAnalysePage />} />
                </Routes>
            </MemoryRouter>
        );

        // 1. Verifieer dat getStandaardTree wordt aangeroepen
        await waitFor(() => {
            expect(getStandaardTreeSpy).toHaveBeenCalled();
        });

        // 2. Categorie select element moet gevuld zijn met de categorieën uit de boom
        const categorieSelect = screen.getByLabelText('Categorie') as HTMLSelectElement;
        await waitFor(() => {
            expect(categorieSelect.options.length).toBe(3); // placeholder + 2 categorieën
        });

        expect(screen.getByRole('option', { name: 'Kwaliteit fysieke leefomgeving' })).toBeInTheDocument();
        expect(screen.getByRole('option', { name: 'Samenstelling' })).toBeInTheDocument();

        // 3. Thema select is initieel gedeactiveerd
        const themaSelect = screen.getByLabelText('Thema') as HTMLSelectElement;
        expect(themaSelect).toBeDisabled();

        // 4. Selecteer 'Kwaliteit fysieke leefomgeving'
        const user = userEvent.setup();
        await user.selectOptions(categorieSelect, 'Kwaliteit fysieke leefomgeving');

        // Thema select moet nu geactiveerd worden en Openbare ruimte bevatten
        await waitFor(() => {
            expect(themaSelect).not.toBeDisabled();
        });
        expect(screen.getByRole('option', { name: 'Openbare ruimte' })).toBeInTheDocument();

        // 5. Selecteer 'Openbare ruimte'
        await user.selectOptions(themaSelect, 'Openbare ruimte');

        // Onderdeel select moet nu geactiveerd worden en Groen en water bevatten
        const onderdeelSelect = screen.getByLabelText('Onderdeel') as HTMLSelectElement;
        await waitFor(() => {
            expect(onderdeelSelect).not.toBeDisabled();
        });
        expect(screen.getByRole('option', { name: 'Groen en water' })).toBeInTheDocument();
    });
});
