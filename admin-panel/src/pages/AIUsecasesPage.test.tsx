import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AIUsecasesPage } from './AIUsecasesPage';
import { aiVrijgaveAPI } from '../services/api';
import type { AIUsecase } from '../services/api';

const basis = { stilgezet: false, status_door: null, status_op: null, verklaring_id: null, versie: null, geldig_tot: null,
    bestandsnaam: null, grootte: null, sha256: null, geupload_door: null, geupload_op: null, verklaring_url: null };

const USECASES: AIUsecase[] = [
    { ...basis, code: 'A', naam: 'Assistent', omschrijving: 'Chat', open: true, reden: 'open',
      verklaring_id: 'v1', versie: '0.4.0', geldig_tot: '2027-01-31', bestandsnaam: 'DPIA.pdf',
      geupload_door: 'fb-beheer', geupload_op: '2026-10-10T10:00:00Z', verklaring_url: '/api/ai/usecases/A/verklaring' },
    { ...basis, code: 'B', naam: 'Samenvatting/rapport', omschrijving: 'Rapport', open: false, reden: 'geen_verklaring' },
    { ...basis, code: 'C', naam: 'Zoeken (semantisch)', omschrijving: 'Zoeken', open: false, reden: 'stilgezet', stilgezet: true },
];

const ok = <T,>(data: T) => Promise.resolve({ data } as never);

beforeEach(() => {
    vi.spyOn(aiVrijgaveAPI, 'usecases').mockImplementation(() => ok(USECASES));
    vi.spyOn(aiVrijgaveAPI, 'vrijgavelog').mockImplementation(() => ok([]));
    vi.spyOn(aiVrijgaveAPI, 'logboek').mockImplementation(() => ok({ totaal: 0, regels: [] }));
    vi.spyOn(aiVrijgaveAPI, 'bewaartermijn').mockImplementation(() => ok({ bewaartermijn_dagen: 365, gewijzigd_door: null, gewijzigd_op: null }));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

describe('AIUsecasesPage', () => {
    it('toont per usecase open of dicht, met de verklaring en wie hem uploadde', async () => {
        render(<AIUsecasesPage />);
        expect(await screen.findByTestId('status-A')).toHaveTextContent('Open');
        expect(screen.getByTestId('status-B')).toHaveTextContent('Dicht: geen verklaring');
        expect(screen.getByTestId('status-C')).toHaveTextContent('noodstop');
        const a = screen.getByTestId('usecase-A');
        expect(within(a).getByRole('link', { name: /DPIA.pdf/ })).toHaveAttribute('href', '/api/ai/usecases/A/verklaring');
        expect(within(a).getByText(/fb-beheer/)).toBeInTheDocument();
    });

    it('noodstop en opheffen roepen de beheer-API aan', async () => {
        const stop = vi.spyOn(aiVrijgaveAPI, 'noodstop').mockImplementation(() => ok({}));
        const hervat = vi.spyOn(aiVrijgaveAPI, 'hervatten').mockImplementation(() => ok({}));
        render(<AIUsecasesPage />);
        const a = await screen.findByTestId('usecase-A');
        await userEvent.click(within(a).getByRole('button', { name: /Noodstop: zet stil/ }));
        await waitFor(() => expect(stop).toHaveBeenCalledWith('A'));
        await userEvent.click(within(screen.getByTestId('usecase-C')).getByRole('button', { name: /Noodstop opheffen/ }));
        await waitFor(() => expect(hervat).toHaveBeenCalledWith('C'));
    });

    it('uploaden kan pas met PDF, versie en geldig tot', async () => {
        const upload = vi.spyOn(aiVrijgaveAPI, 'upload').mockImplementation(() => ok({ verklaring_id: 'v2', sha256: 'x' }));
        render(<AIUsecasesPage />);
        const b = await screen.findByTestId('usecase-B');
        const knop = within(b).getByRole('button', { name: /Uploaden en vrijgeven/ });
        expect(knop).toBeDisabled();
        const pdf = new File(['%PDF-1.4'], 'iama.pdf', { type: 'application/pdf' });
        await userEvent.upload(within(b).getByLabelText('Verklaring (PDF)'), pdf);
        await userEvent.type(within(b).getByLabelText('Versie'), '0.4.0');
        fireEvent.change(within(b).getByLabelText('Geldig tot en met'), { target: { value: '2027-06-30' } });
        expect(knop).toBeEnabled();
        await userEvent.click(knop);
        await waitFor(() => expect(upload).toHaveBeenCalledWith('B', pdf, '0.4.0', '2027-06-30'));
    });
});
