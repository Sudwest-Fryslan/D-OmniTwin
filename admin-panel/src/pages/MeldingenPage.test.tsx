import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MeldingenPage } from './MeldingenPage';
import { meldingenAPI } from '../services/api';
import type { Melding, MeldingenResponse } from '../types';

const MELDINGEN: Melding[] = [
    {
        id: '11111111-1111-1111-1111-111111111111',
        type: 'data',
        onderwerp: 'Verkeerde armoede definitie',
        toelichting: 'In Sneek Centrum lijkt het cijfer te hoog.',
        context: { indicator_id: 'armoede_pct', gebied_ids: ['BU001'] },
        melder_email: 'inwoner@voorbeeld.nl',
        status: 'nieuw',
        notitie_beheer: null,
        aangemaakt_op: '2026-10-11T12:00:00Z',
        bijgewerkt_op: '2026-10-11T12:00:00Z',
    },
    {
        id: '22222222-2222-2222-2222-222222222222',
        type: 'ai',
        onderwerp: 'Chat antwoord incompleet',
        toelichting: 'De assistent noemde geen cijfers voor Bolsward.',
        context: { ai_usecase: 'A', vraag: 'Hoeveel inwoners heeft Bolsward?' },
        melder_email: null,
        status: 'in_behandeling',
        notitie_beheer: 'Navragen bij team data',
        aangemaakt_op: '2026-10-11T13:00:00Z',
        bijgewerkt_op: '2026-10-11T13:30:00Z',
    },
];

const mockResponse: MeldingenResponse = {
    items: MELDINGEN,
    tellingen: {
        nieuw: 1,
        doorgestuurd_naar_bron: 0,
        in_behandeling: 1,
        afgehandeld: 0,
        afgewezen: 0,
    },
    totaal: 2,
    limit: 50,
    offset: 0,
};

const ok = <T,>(data: T) => Promise.resolve({ data } as never);

beforeEach(() => {
    vi.spyOn(meldingenAPI, 'getMeldingen').mockImplementation(() => ok(mockResponse));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

describe('MeldingenPage', () => {
    it('toont meldingenoverzicht met tellers en statustabs', async () => {
        render(<MeldingenPage />);

        expect(await screen.findByText(/Terugmeldvoorziening & Regielogboek/)).toBeInTheDocument();
        expect(screen.getByText('Verkeerde armoede definitie')).toBeInTheDocument();
        expect(screen.getByText('Chat antwoord incompleet')).toBeInTheDocument();
    });

    it('toont detailweergave en staat statuswijziging toe', async () => {
        const updateSpy = vi.spyOn(meldingenAPI, 'updateMelding').mockImplementation((id: string, data: { status?: string; notitie_beheer?: string }) => {
            const geüpdatet: Melding = {
                ...MELDINGEN[0],
                status: (data.status as any) || MELDINGEN[0].status,
                notitie_beheer: data.notitie_beheer || null,
            };
            return ok(geüpdatet);
        });

        render(<MeldingenPage />);

        const item = await screen.findByText('Verkeerde armoede definitie');
        await userEvent.click(item);

        expect(screen.getByText(/Toelichting van melder/)).toBeInTheDocument();
        expect(screen.getAllByText('In Sneek Centrum lijkt het cijfer te hoog.').length).toBe(2);
        expect(screen.getByText('inwoner@voorbeeld.nl')).toBeInTheDocument();

        const opslaanBtn = screen.getByRole('button', { name: /Wijzigingen opslaan/ });
        await userEvent.click(opslaanBtn);

        await waitFor(() => {
            expect(updateSpy).toHaveBeenCalledWith('11111111-1111-1111-1111-111111111111', {
                status: 'nieuw',
                notitie_beheer: '',
            });
        });
    });
});
