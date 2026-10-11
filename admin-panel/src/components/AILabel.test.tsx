import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AILabel } from './AILabel';
import { organisatieAPI } from '../services/api';
import { meldUrl, meldtekst, STANDAARD_MELD_URL, zetMeldkanaal } from '../services/melden';

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    zetMeldkanaal(null);
});

describe('melden', () => {
    it('maakt een vooringevuld issue met usecase, soort en het ingekorte resultaat', () => {
        const url = new URL(meldUrl({ onderwerp: 'ai', usecase: 'B', resultaat: 'x'.repeat(2000), vraag: 'hoe groen?' }));
        expect(`${url.origin}${url.pathname}`).toBe(STANDAARD_MELD_URL);
        expect(url.searchParams.get('title')).toBe('Melding AI-resultaat (usecase B)');
        const body = url.searchParams.get('body') ?? '';
        expect(body).toContain('B – Samenvatting/rapport');
        expect(body).toContain('AI-fout');
        expect(body).toContain('Systeemfout');
        expect(body).toContain('hoe groen?');
        expect(body).toContain('geen persoonsgegevens');
        expect(body.length).toBeLessThan(1500);
    });

    it('gebruikt de meldplek van de instantie, ook mailto', () => {
        expect(meldUrl({ onderwerp: 'ai', usecase: 'A' }, 'https://meld.voorbeeld.nl/form?x=1')).toMatch(/^https:\/\/meld\.voorbeeld\.nl\/form\?x=1&title=/);
        expect(meldUrl({ onderwerp: 'ai', usecase: 'A' }, 'mailto:ai@voorbeeld.nl')).toMatch(/^mailto:ai@voorbeeld\.nl\?subject=/);
        expect(meldUrl({ onderwerp: 'ai' }, 'javascript:alert(1)')).toMatch(/^https:\/\/github\.com\//);
    });

    it('zet geen accountgegevens in de melding', () => {
        const { tekst } = meldtekst({ onderwerp: 'ai', usecase: 'C', vraag: 'groen' });
        expect(tekst).not.toMatch(/gebruiker|account|ip-adres/i);
    });
});

describe('AILabel', () => {
    it('toont label, waarschuwing, bronnen, verklaring en melden', async () => {
        vi.spyOn(organisatieAPI, 'get').mockImplementation(() =>
            Promise.resolve({ data: { meld_url: 'https://meld.voorbeeld.nl/nieuw' } } as never));
        render(<AILabel usecase="B" resultaat="Samenvatting" bronnen={['65+ jaar (%)']} />);
        const label = screen.getByRole('note', { name: /AI-resultaat, usecase B/ });
        expect(label).toHaveTextContent('AI');
        expect(label).toHaveTextContent('onjuist of onvolledig');
        expect(label).toHaveTextContent('Bronnen: 65+ jaar (%)');
        expect(screen.getByRole('link', { name: /Meer informatie/ })).toHaveAttribute('href', '/static/ai.html#usecase-B');
        await waitFor(() => expect(screen.getByRole('link', { name: /Melden/ }).getAttribute('href'))
            .toMatch(/^https:\/\/meld\.voorbeeld\.nl\/nieuw\?title=/));
    });

    it('een aangesloten meldkanaal gaat voor (#311)', async () => {
        vi.spyOn(organisatieAPI, 'get').mockImplementation(() => Promise.resolve({ data: {} } as never));
        const kanaal = vi.fn();
        zetMeldkanaal(kanaal);
        render(<AILabel usecase="C" vraag="groen" />);
        await userEvent.click(screen.getByRole('link', { name: /Melden/ }));
        expect(kanaal).toHaveBeenCalledWith(expect.objectContaining({ onderwerp: 'ai', usecase: 'C', vraag: 'groen' }));
    });
});
