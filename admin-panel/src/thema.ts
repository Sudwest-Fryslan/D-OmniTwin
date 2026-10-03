// Thema van de organisatie (#89, #251), zoals in de viewer: GET /api/organisatie geeft de
// themanaam, het stijlblad is /static/css/themes/<thema>.css (NL Design System-tokens).
// admin.css leest de tokens met de oude kleuren als terugval; zonder thema verandert er niets.
// Het beheerscherm is donker: index.html zet data-theme="dark", dus de donkere tokens gelden.
const THEMA = /^[a-z0-9-]+$/;

export async function laadThema(): Promise<void> {
    try {
        const r = await fetch('/api/organisatie', { headers: { Accept: 'application/json' } });
        if (!r.ok) return;
        const thema = (await r.json())?.thema;
        if (typeof thema !== 'string' || !THEMA.test(thema)) return;
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `/static/css/themes/${thema}.css`;
        link.dataset.thema = thema;
        document.head.appendChild(link);
    } catch {
        // Geen organisatie of geen netwerk: standaardkleuren
    }
}
