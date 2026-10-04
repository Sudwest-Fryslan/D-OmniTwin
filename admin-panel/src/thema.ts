// Thema van de organisatie (#89, #251), zoals in de viewer: GET /api/organisatie geeft de
// themanaam, het stijlblad is /static/css/themes/<thema>.css (NL Design System-tokens).
// admin.css leest de tokens met de oude kleuren als terugval; zonder thema verandert er niets.
//
// Licht of donker (#284): het thema kiest de standaardweergave van het beheerscherm met het token
// --d-omnitwin-beheer-modus (licht/donker; zonder thema donker, zoals het altijd was). Een eigen
// keuze van de gebruiker (menu rechtsboven) gaat voor en staat in localStorage.
const THEMA = /^[a-z0-9-]+$/;
const KEUZE_SLEUTEL = 'omnitwin-beheer-modus';

export type BeheerModus = 'licht' | 'donker';

function eigenKeuze(): BeheerModus | null {
    try {
        const k = localStorage.getItem(KEUZE_SLEUTEL);
        return k === 'licht' || k === 'donker' ? k : null;
    } catch {
        return null;
    }
}

/** De standaardweergave volgens het thema (admin.css: --beheer-modus). */
function themaModus(): BeheerModus {
    const waarde = getComputedStyle(document.documentElement).getPropertyValue('--beheer-modus').trim();
    return waarde === 'licht' ? 'licht' : 'donker';
}

function zetDataTheme(modus: BeheerModus) {
    document.documentElement.dataset.theme = modus === 'licht' ? 'light' : 'dark';
}

export function huidigeModus(): BeheerModus {
    return document.documentElement.dataset.theme === 'light' ? 'licht' : 'donker';
}

/** Kies licht of donker en onthoud die keuze voor deze browser. */
export function kiesModus(modus: BeheerModus) {
    try {
        localStorage.setItem(KEUZE_SLEUTEL, modus);
    } catch {
        // Geen opslag (privévenster): alleen voor deze pagina
    }
    zetDataTheme(modus);
}

function pasModusToe() {
    zetDataTheme(eigenKeuze() ?? themaModus());
}

export async function laadThema(): Promise<void> {
    // Eigen keuze direct toepassen (geen flits); de themakeuze volgt als het stijlblad er is
    const keuze = eigenKeuze();
    if (keuze) zetDataTheme(keuze);
    try {
        const r = await fetch('/api/organisatie', { headers: { Accept: 'application/json' } });
        if (!r.ok) return;
        const thema = (await r.json())?.thema;
        if (typeof thema !== 'string' || !THEMA.test(thema)) return;
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `/static/css/themes/${thema}.css`;
        link.dataset.thema = thema;
        link.addEventListener('load', pasModusToe);
        document.head.appendChild(link);
    } catch {
        // Geen organisatie of geen netwerk: standaardkleuren
    }
}
