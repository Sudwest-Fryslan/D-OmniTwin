import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import { MeldModal } from './MeldModal';

vi.mock('axios');

describe('MeldModal', () => {
    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
    });

    it('rendert niet als isOpen false is', () => {
        render(<MeldModal isOpen={false} onClose={vi.fn()} />);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('opent met titel, context en default waarden', () => {
        render(
            <MeldModal
                isOpen={true}
                onClose={vi.fn()}
                context={{
                    rapport_type: 'Gebiedsdossier',
                    gebied_id: 'BU19000113',
                    url: 'http://localhost/rapport/BU19000113',
                }}
            />
        );

        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Melding doorgeven' })).toBeInTheDocument();
        expect(screen.getByText(/Context:/)).toBeInTheDocument();
        expect(screen.getByText(/Rapport: Gebiedsdossier \| Gebied: BU19000113/)).toBeInTheDocument();
        expect(screen.getByLabelText('Categorie')).toHaveValue('data');
        expect(screen.getByLabelText('Onderwerp')).toHaveValue('Afwijking in Gebiedsdossier - BU19000113');
    });

    it('sluit bij klikken op sluitknop of annuleren', async () => {
        const onClose = vi.fn();
        const user = userEvent.setup();

        render(<MeldModal isOpen={true} onClose={onClose} />);

        await user.click(screen.getByRole('button', { name: 'Annuleren' }));
        expect(onClose).toHaveBeenCalledTimes(1);

        await user.click(screen.getByRole('button', { name: 'Sluiten' }));
        expect(onClose).toHaveBeenCalledTimes(2);
    });

    it('verzendt melding via POST /api/meldingen met context', async () => {
        const onClose = vi.fn();
        const user = userEvent.setup();
        const postSpy = vi.spyOn(axios, 'post').mockResolvedValue({ data: { id: 'm1', status: 'ontvangen' } });

        render(
            <MeldModal
                isOpen={true}
                onClose={onClose}
                context={{
                    rapport_type: 'Benchmark Vergelijker',
                    url: 'http://localhost/rapport/benchmark?gebied_a=BU19000113',
                }}
            />
        );

        const toelichtingInput = screen.getByLabelText('Toelichting');
        await user.type(toelichtingInput, 'De waarde van indicator X klopt niet.');

        const emailInput = screen.getByLabelText(/E-mailadres/);
        await user.type(emailInput, 'test@example.com');

        await user.click(screen.getByRole('button', { name: 'Versturen' }));

        expect(postSpy).toHaveBeenCalledWith('/api/meldingen', {
            type: 'data',
            onderwerp: 'Afwijking in Benchmark Vergelijker',
            toelichting: 'De waarde van indicator X klopt niet.',
            melder_email: 'test@example.com',
            context: {
                rapport_type: 'Benchmark Vergelijker',
                url: 'http://localhost/rapport/benchmark?gebied_a=BU19000113',
                bron: 'rapport',
            },
        });

        await waitFor(() => {
            expect(screen.getByText(/Bedankt! Uw melding is geregistreerd/)).toBeInTheDocument();
        });
    });
});
