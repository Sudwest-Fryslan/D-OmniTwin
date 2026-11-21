import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ExterneKaartlagenPage } from './ExterneKaartlagenPage';
import { externeKaartlagenAPI } from '../services/api';
import type { ExterneKaartlaag, ExterneKaartlaagKoppelOpties } from '../types';

const ok = <T,>(data: T) => Promise.resolve({ data } as never);

const LAGEN: ExterneKaartlaag[] = [
    {
        id: 1,
        naam: 'Natura 2000',
        beschrijving: 'Natuurgebieden',
        laag_type: 'selectie',
        bron_type: 'WFS',
        url: 'https://service.pdok.nl/rvo/natura2000/wfs/v1_0',
        typename: 'natura2000:natura2000',
        srsname: 'EPSG:28992',
        versie: '2.0.0',
        filter_type: 'provincie',
        filter_waarde: 'Fryslân',
        koppel_veld: null,
        kleur_lijn: '#059669',
        kleur_fill: '#34ef99',
        opacity: 0.3,
        actief: true,
        volgorde: 0,
        groep_naam: null,
        groep_volgorde: 0,
        kompas_thema_naam: 'Klimaat',
        gekoppelde_indicatoren: ['11111111-1111-1111-1111-111111111111'],
        created_at: null,
        updated_at: null,
    },
    {
        id: 2,
        naam: 'Groenstroken',
        beschrijving: null,
        laag_type: 'selectie',
        bron_type: 'WFS',
        url: 'https://example.org/groen',
        typename: 'groen',
        srsname: 'EPSG:28992',
        versie: '2.0.0',
        filter_type: 'provincie',
        filter_waarde: 'Fryslân',
        koppel_veld: null,
        kleur_lijn: '#10b981',
        kleur_fill: '#10b981',
        opacity: 0.2,
        actief: true,
        volgorde: 10,
        groep_naam: null,
        groep_volgorde: 0,
        kompas_thema_naam: 'Klimaat',
        gekoppelde_indicatoren: [],
        created_at: null,
        updated_at: null,
    },
    {
        id: 3,
        naam: 'BAG Woonplaatsen',
        beschrijving: null,
        laag_type: 'selectie',
        bron_type: 'WFS',
        url: 'https://service.pdok.nl/kadaster/bag/wfs/v2_0',
        typename: 'bag:woonplaats',
        srsname: 'EPSG:28992',
        versie: '2.0.0',
        filter_type: 'provincie',
        filter_waarde: 'Fryslân',
        koppel_veld: null,
        kleur_lijn: '#8B5CF6',
        kleur_fill: '#8B5CF6',
        opacity: 0.15,
        actief: true,
        volgorde: 0,
        groep_naam: 'Gebiedsindelingen',
        groep_volgorde: 10,
        kompas_thema_naam: null,
        gekoppelde_indicatoren: [],
        created_at: null,
        updated_at: null,
    },
];

const OPTIES: ExterneKaartlaagKoppelOpties = {
    themas: ['Klimaat', 'Wonen'],
    groepen: ['Gebiedsindelingen'],
    indicatoren: [
        { uuid: '11111111-1111-1111-1111-111111111111', naam: 'Oppervlak groen per inwoner', thema: 'Klimaat' },
        { uuid: '22222222-2222-2222-2222-222222222222', naam: 'Woningdichtheid', thema: 'Wonen' },
    ],
};

beforeEach(() => {
    vi.spyOn(externeKaartlagenAPI, 'getAll').mockImplementation(() => ok({ lagen: LAGEN, totaal: LAGEN.length }));
    vi.spyOn(externeKaartlagenAPI, 'getKoppelOpties').mockImplementation(() => ok(OPTIES));
    vi.spyOn(externeKaartlagenAPI, 'getLokaalBestanden').mockImplementation(() => ok({ bestanden: [], totaal: 0 }));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

describe('ExterneKaartlagenPage (#527)', () => {
    it('toont kaartlagen gegroepeerd op groep_naam en kompas_thema_naam met badges', async () => {
        render(<ExterneKaartlagenPage />);

        const klimaatGroep = await screen.findByRole('region', { name: 'Groep Klimaat' });
        const indelingenGroep = screen.getByRole('region', { name: 'Groep Gebiedsindelingen' });

        expect(within(klimaatGroep).getByText('Natura 2000')).toBeInTheDocument();
        expect(within(klimaatGroep).getByText('Groenstroken')).toBeInTheDocument();
        expect(within(klimaatGroep).getByText('1 ind.')).toBeInTheDocument();
        expect(within(indelingenGroep).getByText('BAG Woonplaatsen')).toBeInTheDocument();
    });

    it('verstuurt bijgewerkte laag- en groepvolgorde bij klik op Omhoog/Omlaag', async () => {
        const updateVolgorde = vi.spyOn(externeKaartlagenAPI, 'updateVolgorde').mockImplementation(() => ok({ bijgewerkt: 2, status: 'bijgewerkt' }));
        render(<ExterneKaartlagenPage />);

        const naturaOmlaag = await screen.findByRole('button', { name: 'Natura 2000 omlaag verplaatsen' });
        await userEvent.click(naturaOmlaag);

        await waitFor(() =>
            expect(updateVolgorde).toHaveBeenCalledWith([
                { id: 2, volgorde: 0, groep_volgorde: 0 },
                { id: 1, volgorde: 10, groep_volgorde: 0 },
            ])
        );

        updateVolgorde.mockClear();
        const groepOmlaag = screen.getByRole('button', { name: 'Groep Klimaat omlaag verplaatsen' });
        await userEvent.click(groepOmlaag);

        await waitFor(() =>
            expect(updateVolgorde).toHaveBeenCalledWith([
                { id: 3, volgorde: 0, groep_volgorde: 0 },
                { id: 1, volgorde: 0, groep_volgorde: 10 },
                { id: 2, volgorde: 10, groep_volgorde: 10 },
            ])
        );
    });

    it('slaat kompas_thema_naam, optionele groep_naam en gekoppelde indicatoren op in het formulier', async () => {
        const createSpy = vi.spyOn(externeKaartlagenAPI, 'create').mockImplementation(() => ok({ id: 4, naam: 'Nieuw', status: 'aangemaakt' }));
        render(<ExterneKaartlagenPage />);

        await userEvent.click(await screen.findByRole('button', { name: /Nieuwe Laag/ }));

        await userEvent.type(screen.getByLabelText('Naam *'), 'Bomenkaart');
        await userEvent.type(screen.getByLabelText('WFS/WMS URL *'), 'https://example.org/bomen');
        await userEvent.selectOptions(screen.getByLabelText('Kompasthema'), 'Klimaat');
        await userEvent.type(screen.getByLabelText('Groepsnaam (optioneel)'), 'Natuur & Groen');

        await userEvent.type(screen.getByLabelText(/Gekoppelde indicatoren/), 'groen');
        const groep = screen.getByRole('group', { name: 'Kies gekoppelde indicatoren' });
        await userEvent.click(within(groep).getByLabelText(/Oppervlak groen per inwoner/));

        await userEvent.click(screen.getByRole('button', { name: 'Laag Toevoegen' }));

        await waitFor(() =>
            expect(createSpy).toHaveBeenCalledWith(
                expect.objectContaining({
                    naam: 'Bomenkaart',
                    url: 'https://example.org/bomen',
                    kompas_thema_naam: 'Klimaat',
                    groep_naam: 'Natuur & Groen',
                    gekoppelde_indicatoren: ['11111111-1111-1111-1111-111111111111'],
                })
            )
        );
    });
});
