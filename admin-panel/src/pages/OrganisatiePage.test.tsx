import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { OrganisatiePage, foutmelding } from './OrganisatiePage';
import { gebiedenAPI, organisatieAPI } from '../services/api';
import type { Organisatie, ThemaInfo } from '../services/api';

const ORG: Organisatie = {
    code: 'swf', naam: 'Gemeente Súdwest-Fryslân', korte_naam: 'SWF', oin: null,
    gemeente_codes: ['0737'], standaard_gemeente_code: '0737', benchmark_provincie: 'Fryslân',
    contact_email: 'geo@voorbeeld.nl', thema: 'swf',
    logos: [
        { pad: '/static/images/SWF-logo.png', naam: 'SWF', rol: 'eigen' },
        { pad: '/static/images/DF.png', naam: 'Datafryslân', rol: 'partner' },
    ],
};

const THEMAS: ThemaInfo[] = [
    {
        naam: 'd-omnitwin', titel: 'de standaarduitstraling van D-OmniTwin',
        kleuren: {
            licht: { '--d-omnitwin-header-background-color-start': '#1e3a8a', '--d-omnitwin-header-background-color-end': '#15803d', '--basis-color-action-1-bg-default': '#1e3a8a' },
            donker: { '--d-omnitwin-header-background-color-start': '#3b82f6', '--d-omnitwin-header-background-color-end': '#22c55e', '--basis-color-action-1-bg-default': '#2563eb' },
        },
    },
    {
        naam: 'swf', titel: 'Gemeente Súdwest-Fryslân',
        kleuren: {
            licht: { '--d-omnitwin-header-background-color-start': '#bf0042', '--d-omnitwin-header-background-color-end': '#8c0030', '--basis-color-action-1-bg-default': '#bf0042' },
            donker: { '--d-omnitwin-header-background-color-start': '#8c0030', '--d-omnitwin-header-background-color-end': '#5c0020', '--basis-color-action-1-bg-default': '#bf0042' },
        },
    },
];

const ok = <T,>(data: T) => Promise.resolve({ data } as never);

beforeEach(() => {
    vi.spyOn(organisatieAPI, 'get').mockImplementation(() => ok(ORG));
    vi.spyOn(organisatieAPI, 'themas').mockImplementation(() => ok(THEMAS));
    vi.spyOn(organisatieAPI, 'logos').mockImplementation(() => ok(['/static/images/DF.png', '/static/images/LWD.png', '/static/images/SWF-logo.png']));
    vi.spyOn(gebiedenAPI, 'getGemeenten').mockImplementation(() => ok({
        gemeenten: [{ code: '0737', naam: 'Tytsjerksteradiel', provincie: 'Fryslân' }, { code: '0080', naam: 'Leeuwarden', provincie: 'Fryslân' }],
        totaal: 2,
    }));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

const kopbalk = (modus: 'licht' | 'donker') => screen.getByTestId(`voorbeeld-${modus}-kopbalk`);

describe('OrganisatiePage', () => {
    it('toont het huidige thema met voorbeeld in licht en donker', async () => {
        render(<OrganisatiePage />);
        expect(await screen.findByLabelText('Naam')).toHaveValue('Gemeente Súdwest-Fryslân');
        expect(screen.getByRole('radio', { name: /swf/ })).toBeChecked();
        expect(kopbalk('licht').style.background).toContain('rgb(191, 0, 66)');
        expect(kopbalk('donker').style.background).toContain('rgb(140, 0, 48)');
        // Tokens staan als variabelen op het voorbeeld, zodat het beeldmerk ze erft
        expect(screen.getByTestId('voorbeeld-licht').style.getPropertyValue('--basis-color-action-1-bg-default')).toBe('#bf0042');
    });

    it('wisselt het voorbeeld live bij een ander thema en slaat op', async () => {
        const zet = vi.spyOn(organisatieAPI, 'zet').mockImplementation(data => ok({ ...ORG, ...data, standaard_gemeente_code: data.gemeente_codes[0] }));
        const user = userEvent.setup();
        render(<OrganisatiePage />);
        await user.click(await screen.findByRole('radio', { name: /d-omnitwin/ }));
        expect(kopbalk('licht').style.background).toContain('rgb(30, 58, 138)');
        expect(kopbalk('donker').style.background).toContain('rgb(59, 130, 246)');

        await user.click(screen.getByRole('button', { name: /Opslaan/ }));
        await waitFor(() => expect(zet).toHaveBeenCalledTimes(1));
        expect(zet.mock.calls[0][0]).toMatchObject({ thema: 'd-omnitwin', code: 'swf', gemeente_codes: ['0737'] });
        expect(zet.mock.calls[0][0]).not.toHaveProperty('standaard_gemeente_code');
        expect(await screen.findByRole('status')).toHaveTextContent(/Opgeslagen/);
    });

    it('logo\'s: volgorde, toevoegen uit bestaande bestanden en verwijderen', async () => {
        const zet = vi.spyOn(organisatieAPI, 'zet').mockImplementation(data => ok({ ...ORG, ...data }));
        const user = userEvent.setup();
        render(<OrganisatiePage />);
        await screen.findByLabelText('Naam');

        // Alleen bestanden die nog niet gekozen zijn
        const kies = screen.getByRole('combobox', { name: 'Logo toevoegen' });
        expect(within(kies).getAllByRole('option').map(o => o.textContent)).toEqual(['Kies een bestand uit /static/images/', 'LWD.png']);
        await user.selectOptions(kies, '/static/images/LWD.png');
        await user.click(screen.getAllByRole('button', { name: /Toevoegen/ })[1]);
        await user.click(screen.getByRole('button', { name: 'Logo 1 omlaag' }));
        await user.click(screen.getByRole('button', { name: 'Logo 3 verwijderen' }));
        await user.click(screen.getByRole('button', { name: /Opslaan/ }));

        await waitFor(() => expect(zet).toHaveBeenCalled());
        expect(zet.mock.calls[0][0].logos.map(l => l.pad)).toEqual(['/static/images/DF.png', '/static/images/SWF-logo.png']);
    });

    it('gemeentecodes: toevoegen, standaard kiezen en ongeldige code weigeren', async () => {
        const zet = vi.spyOn(organisatieAPI, 'zet').mockImplementation(data => ok({ ...ORG, ...data }));
        const user = userEvent.setup();
        render(<OrganisatiePage />);
        const invoer = await screen.findByLabelText('Gemeentecode toevoegen');

        await user.type(invoer, 'GM80');
        await user.click(screen.getAllByRole('button', { name: /Toevoegen/ })[0]);
        expect(screen.getByRole('alert')).toHaveTextContent(/vier cijfers/);

        await user.clear(invoer);
        await user.type(invoer, '0080');
        await user.click(screen.getAllByRole('button', { name: /Toevoegen/ })[0]);
        await user.click(screen.getByRole('radio', { name: /0080 Leeuwarden/ }));
        await user.click(screen.getByRole('button', { name: /Opslaan/ }));

        await waitFor(() => expect(zet).toHaveBeenCalled());
        expect(zet.mock.calls[0][0].gemeente_codes).toEqual(['0080', '0737']);
    });

    it('toont de melding van de backend bij 422', async () => {
        vi.spyOn(organisatieAPI, 'zet').mockRejectedValue({
            response: { status: 422, data: { detail: [{ loc: ['body', 'thema'], msg: "Value error, thema 'x' bestaat niet in static/css/themes/" }] } },
        });
        const user = userEvent.setup();
        render(<OrganisatiePage />);
        await user.click(await screen.findByRole('button', { name: /Opslaan/ }));
        expect(await screen.findByRole('alert')).toHaveTextContent("thema 'x' bestaat niet in static/css/themes/");
    });

    it('importeert een exportbestand', async () => {
        const importeer = vi.spyOn(organisatieAPI, 'importeer').mockImplementation(() => ok({ ...ORG, naam: 'Gemeente Leeuwarden', thema: 'd-omnitwin' }));
        const user = userEvent.setup();
        render(<OrganisatiePage />);
        await screen.findByLabelText('Naam');
        const inhoud = { formaat: 'd-omnitwin/organisatie', versie: 1, organisatie: { ...ORG, naam: 'Gemeente Leeuwarden' } };
        const bestand = new File([JSON.stringify(inhoud)], 'organisatie-lwd.json', { type: 'application/json' });
        await user.upload(screen.getByLabelText('Exportbestand importeren'), bestand);

        await waitFor(() => expect(importeer).toHaveBeenCalledWith(inhoud));
        expect(await screen.findByLabelText('Naam')).toHaveValue('Gemeente Leeuwarden');
        expect(screen.getByRole('radio', { name: /d-omnitwin/ })).toBeChecked();
        expect(screen.getByRole('status')).toHaveTextContent(/Geïmporteerd uit organisatie-lwd.json/);
    });

    it('meldt een bestand zonder geldige JSON', async () => {
        const importeer = vi.spyOn(organisatieAPI, 'importeer');
        const user = userEvent.setup();
        render(<OrganisatiePage />);
        await screen.findByLabelText('Naam');
        await user.upload(screen.getByLabelText('Exportbestand importeren'), new File(['{kapot'], 'x.json', { type: 'application/json' }));
        expect(await screen.findByRole('alert')).toHaveTextContent('geen geldige JSON');
        expect(importeer).not.toHaveBeenCalled();
    });
});

describe('foutmelding', () => {
    it('leest een tekst, een lijst of valt terug', () => {
        expect(foutmelding({ response: { data: { detail: 'Alleen voor beheerders.' } } }, 'x')).toBe('Alleen voor beheerders.');
        expect(foutmelding({ response: { data: { detail: [{ msg: 'Value error, a' }, { msg: 'b' }] } } }, 'x')).toBe('a; b');
        expect(foutmelding(new Error('netwerk'), 'standaard')).toBe('standaard');
    });
});
