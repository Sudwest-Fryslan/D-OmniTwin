/**
 * Melden (#312): één generiek meldmechanisme voor de viewer.
 *
 * Een melding is een gewoon object:
 *   { onderwerp: 'ai', usecase: 'A'|'B'|'C'|null, titel, vraag, resultaat, bronnen: [..], pagina }
 * Standaard wordt dat een vooringevuld issue op de meldplek van de instantie (`meld_url` uit
 * GET /api/organisatie, standaard een nieuw issue in de repository van D-OmniTwin); bij een
 * mailto:-adres een e-mail. Geen persoonsgegevens: geen naam, account of IP; vraag en resultaat
 * worden ingekort en de melder ziet alles voordat hij verstuurt.
 *
 * Aansluiten (bijv. de terugmeldvoorziening van #311): OmniMelden.zetKanaal(function (melding) {...})
 * neemt het openen over; meldUrl blijft beschikbaar voor een link als terugval.
 *
 * Laadt als gewoon script (window.OmniMelden) en als CommonJS-module voor de unittest
 * (tests/test_melden_js.py).
 */
(function (root) {
    'use strict';

    const STANDAARD_MELD_URL = 'https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/new';
    const USECASES = { A: 'A – Assistent', B: 'B – Samenvatting/rapport', C: 'C – Zoeken (semantisch)' };
    const MAX_VRAAG = 300;
    const MAX_RESULTAAT = 600;

    let meldplek = STANDAARD_MELD_URL;
    let versie = '';
    let kanaal = null;

    function inkorten(tekst, max) {
        const t = String(tekst || '').replace(/\s+/g, ' ').trim();
        return t.length > max ? `${t.slice(0, max - 1)}…` : t;
    }

    /** Titel en tekst van de melding (Markdown, zoals een issue). */
    function meldtekst(m) {
        const usecase = m.usecase ? (USECASES[m.usecase] || m.usecase) : null;
        const titel = m.titel || (usecase ? `Melding AI-resultaat (usecase ${m.usecase})` : 'Melding');
        const regels = [
            '**Soort** (kies wat past):',
            '- [ ] AI-fout: het antwoord is onjuist, onvolledig of misleidend',
            '- [ ] Systeemfout: iets werkt niet of geeft een foutmelding',
            '',
        ];
        if (usecase) regels.push(`**AI-usecase:** ${usecase}`);
        if (m.pagina) regels.push(`**Waar:** ${inkorten(m.pagina, 100)}`);
        if (m.versie || versie) regels.push(`**Versie D-OmniTwin:** ${m.versie || versie}`);
        if (m.vraag) regels.push('', `**Vraag of zoekterm:** ${inkorten(m.vraag, MAX_VRAAG)}`);
        if (m.resultaat) regels.push('', `**Resultaat (ingekort):** ${inkorten(m.resultaat, MAX_RESULTAAT)}`);
        if (Array.isArray(m.bronnen) && m.bronnen.length) {
            regels.push('', `**Bronnen:** ${inkorten(m.bronnen.join(', '), 300)}`);
        }
        regels.push('', '**Wat klopt er niet?**', '', '',
            '_Zet hier geen persoonsgegevens (namen, adressen, e-mail) in. Controleer de tekst hierboven voordat je verstuurt._');
        return { titel: inkorten(titel, 120), tekst: regels.join('\n') };
    }

    /** De URL voor de meldplek: issue (title/body) of e-mail (subject/body). */
    function meldUrl(m, plek) {
        const basis = plek || meldplek || STANDAARD_MELD_URL;
        const { titel, tekst } = meldtekst(m || {});
        if (/^mailto:/i.test(basis)) {
            const sep = basis.includes('?') ? '&' : '?';
            return `${basis}${sep}subject=${encodeURIComponent(titel)}&body=${encodeURIComponent(tekst)}`;
        }
        if (!/^https:\/\//i.test(basis)) return STANDAARD_MELD_URL;
        const sep = basis.includes('?') ? '&' : '?';
        return `${basis}${sep}title=${encodeURIComponent(titel)}&body=${encodeURIComponent(tekst)}`;
    }

    /** Een melding doen: via het aangesloten kanaal, anders de meldplek in een nieuw venster. */
    function meld(m) {
        if (typeof kanaal === 'function') return kanaal(m);
        if (typeof window !== 'undefined') window.open(meldUrl(m), '_blank', 'noopener,noreferrer');
        return undefined;
    }

    function zetKanaal(fn) { kanaal = typeof fn === 'function' ? fn : null; }
    function zetMeldplek(url) { meldplek = url || STANDAARD_MELD_URL; }
    function zetVersie(v) { versie = v || ''; }
    function heeftKanaal() { return typeof kanaal === 'function'; }

    const api = { meldUrl, meldtekst, meld, zetKanaal, zetMeldplek, zetVersie, heeftKanaal, STANDAARD_MELD_URL, USECASES };
    root.OmniMelden = api;
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }

    // In de browser: meldplek en versie van deze instantie ophalen
    if (typeof document !== 'undefined' && typeof fetch === 'function') {
        const meta = document.querySelector('meta[name="d-omnitwin-versie"]');
        if (meta) zetVersie(meta.getAttribute('content'));
        fetch('/api/organisatie', { credentials: 'same-origin' })
            .then(r => (r.ok ? r.json() : null))
            .then(org => { if (org && org.meld_url) zetMeldplek(org.meld_url); })
            .catch(() => undefined);
    }
})(typeof window !== 'undefined' ? window : globalThis);
