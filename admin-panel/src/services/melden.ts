// Melden (#312): één generiek meldmechanisme, gelijk aan static/js/core/melden.js in de viewer.
// Een melding wordt een vooringevuld issue op de meldplek van de instantie (`meld_url` uit
// GET /api/organisatie; standaard een nieuw issue bij D-OmniTwin), of een e-mail bij mailto:.
// Geen persoonsgegevens: vraag en resultaat worden ingekort, de melder ziet alles voor verzenden.
// Aansluiten (bijv. de terugmeldvoorziening van #311): zetMeldkanaal(fn) neemt het openen over.

export const STANDAARD_MELD_URL = 'https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/new';

export type AIUsecaseCodeMelding = 'A' | 'B' | 'C';

export interface Melding {
    onderwerp: 'ai' | string;
    usecase?: AIUsecaseCodeMelding | null;
    titel?: string;
    vraag?: string;
    resultaat?: string;
    bronnen?: string[];
    pagina?: string;
    versie?: string;
}

const USECASES: Record<AIUsecaseCodeMelding, string> = {
    A: 'A – Assistent',
    B: 'B – Samenvatting/rapport',
    C: 'C – Zoeken (semantisch)',
};

const inkorten = (tekst: string | undefined, max: number) => {
    const t = String(tekst ?? '').replace(/\s+/g, ' ').trim();
    return t.length > max ? `${t.slice(0, max - 1)}…` : t;
};

export function meldtekst(m: Melding): { titel: string; tekst: string } {
    const usecase = m.usecase ? USECASES[m.usecase] : null;
    const titel = m.titel || (usecase ? `Melding AI-resultaat (usecase ${m.usecase})` : 'Melding');
    const regels = [
        '**Soort** (kies wat past):',
        '- [ ] AI-fout: het antwoord is onjuist, onvolledig of misleidend',
        '- [ ] Systeemfout: iets werkt niet of geeft een foutmelding',
        '',
    ];
    if (usecase) regels.push(`**AI-usecase:** ${usecase}`);
    if (m.pagina) regels.push(`**Waar:** ${inkorten(m.pagina, 100)}`);
    if (m.versie) regels.push(`**Versie D-OmniTwin:** ${m.versie}`);
    if (m.vraag) regels.push('', `**Vraag of zoekterm:** ${inkorten(m.vraag, 300)}`);
    if (m.resultaat) regels.push('', `**Resultaat (ingekort):** ${inkorten(m.resultaat, 600)}`);
    if (m.bronnen && m.bronnen.length) regels.push('', `**Bronnen:** ${inkorten(m.bronnen.join(', '), 300)}`);
    regels.push('', '**Wat klopt er niet?**', '', '',
        '_Zet hier geen persoonsgegevens (namen, adressen, e-mail) in. Controleer de tekst hierboven voordat je verstuurt._');
    return { titel: inkorten(titel, 120), tekst: regels.join('\n') };
}

export function meldUrl(m: Melding, plek?: string | null): string {
    const basis = plek || STANDAARD_MELD_URL;
    const { titel, tekst } = meldtekst(m);
    const sep = basis.includes('?') ? '&' : '?';
    if (/^mailto:/i.test(basis)) {
        return `${basis}${sep}subject=${encodeURIComponent(titel)}&body=${encodeURIComponent(tekst)}`;
    }
    if (!/^https:\/\//i.test(basis)) return meldUrl(m, STANDAARD_MELD_URL);
    return `${basis}${sep}title=${encodeURIComponent(titel)}&body=${encodeURIComponent(tekst)}`;
}

let kanaal: ((m: Melding) => void) | null = null;

/** Ander meldkanaal aansluiten (#311); null = weer de meldplek. */
export function zetMeldkanaal(fn: ((m: Melding) => void) | null): void {
    kanaal = fn;
}

export function heeftMeldkanaal(): boolean {
    return kanaal !== null;
}

export function meld(m: Melding): void {
    if (kanaal) kanaal(m);
}
