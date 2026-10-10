/**
 * Label "AI" bij elk AI-resultaat (#312): wat het is, dat het onjuist of onvolledig kan zijn,
 * de bronnen (waar bekend), "Meer informatie" (static/ai.html: status en verklaring, #307/#314) en "Melden"
 * (static/js/core/melden.js). Alleen DOM-API (textContent), geen HTML uit data.
 *
 *   const label = OmniAI.label({ usecase: 'A', vraag, resultaat, bronnen: ['65+ jaar (%)'], pagina: 'Assistent' });
 *   bubble.appendChild(label);
 */
(function (root) {
    'use strict';

    const TEKST = {
        A: 'Dit antwoord is gemaakt met een taalmodel (AI-assistent).',
        B: 'Deze samenvatting is gemaakt met een taalmodel.',
        C: 'Deze zoekresultaten zijn mede gevonden op betekenis, met een AI-model.',
    };
    const NAAM = { A: 'Assistent', B: 'Samenvatting/rapport', C: 'Zoeken (semantisch)' };

    function maak(tag, klasse, tekst) {
        const el = document.createElement(tag);
        if (klasse) el.className = klasse;
        if (tekst !== undefined) el.textContent = tekst;
        return el;
    }

    function label(opties) {
        const o = opties || {};
        const code = o.usecase;
        const doos = maak('div', 'ai-label');
        doos.setAttribute('role', 'note');
        doos.setAttribute('aria-label', `AI-resultaat, usecase ${code} (${NAAM[code] || ''})`);
        doos.dataset.usecase = code || '';

        const kop = maak('p', 'ai-label__kop');
        const badge = maak('span', 'ai-label__badge', 'AI');
        badge.setAttribute('aria-hidden', 'true');
        kop.appendChild(badge);
        kop.appendChild(maak('span', 'ai-label__tekst',
            `${TEKST[code] || 'Dit resultaat is gemaakt met AI.'} Het kan onjuist of onvolledig zijn; controleer belangrijke gegevens via de bron.`));
        doos.appendChild(kop);

        if (Array.isArray(o.bronnen) && o.bronnen.length) {
            doos.appendChild(maak('p', 'ai-label__bronnen', `Bronnen: ${o.bronnen.slice(0, 8).join(', ')}`));
        }

        const links = maak('p', 'ai-label__links');
        // Uitleg per usecase met status, verklaring (PDF) en melden (static/ai.html, #314)
        const info = maak('a', 'ai-label__link', 'Meer informatie');
        info.href = `/static/ai.html#usecase-${encodeURIComponent(code || '')}`;
        info.target = '_blank';
        info.rel = 'noopener';
        info.setAttribute('aria-label', `Meer informatie over AI-usecase ${code}: status en verklaring (opent in een nieuw venster)`);
        links.appendChild(info);

        const melding = { onderwerp: 'ai', usecase: code, vraag: o.vraag, resultaat: o.resultaat,
                          bronnen: o.bronnen, pagina: o.pagina };
        const meld = maak('a', 'ai-label__link ai-label__melden', 'Melden');
        meld.href = root.OmniMelden ? root.OmniMelden.meldUrl(melding) : '#';
        meld.target = '_blank';
        meld.rel = 'noopener';
        meld.setAttribute('aria-label', `Melden: dit AI-resultaat (usecase ${code}) klopt niet of iets werkt niet (opent in een nieuw venster)`);
        meld.addEventListener('click', (e) => {
            // Een aangesloten meldkanaal (#311) gaat voor; anders volgt de link
            if (root.OmniMelden && root.OmniMelden.heeftKanaal()) {
                e.preventDefault();
                root.OmniMelden.meld(melding);
            } else if (root.OmniMelden) {
                meld.href = root.OmniMelden.meldUrl(melding);  // meldplek kan intussen geladen zijn
            }
        });
        links.appendChild(meld);
        doos.appendChild(links);
        return doos;
    }

    root.OmniAI = { label };
})(typeof window !== 'undefined' ? window : globalThis);
