/**
 * Centrale escaping voor data uit de API of de database (#65).
 *
 * Gebruik voor alles wat niet uit de eigen code komt:
 *   el.innerHTML = `<strong>${escapeHtml(gebied.naam)}</strong>`;
 *   link.href = safeUrl(indicator.bron_url);
 * Waar het kan is el.textContent = gebied.naam nog eenvoudiger.
 *
 * Laadt als gewoon script (window.escapeHtml, window.safeUrl) en als
 * CommonJS-module voor de unittest (tests/test_escape_html.py).
 */
(function (root) {
    'use strict';

    const ENTITIES = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
        '`': '&#96;',
    };

    /** Tekst veilig maken voor HTML-inhoud en attributen tussen aanhalingstekens. */
    function escapeHtml(value) {
        if (value === null || value === undefined) return '';
        return String(value).replace(/[&<>"'`]/g, (ch) => ENTITIES[ch]);
    }

    /** Alleen http(s) en relatieve URL's; javascript:, data: e.d. worden ''. */
    function safeUrl(value) {
        if (value === null || value === undefined) return '';
        const url = String(value).trim();
        // Browsers negeren tabs en regeleinden in het schema ("java\tscript:")
        const schema = url.replace(/[\u0000- ]/g, '').match(/^([a-z][a-z0-9+.-]*):/i);
        if (!schema) return url;
        return ['http', 'https'].includes(schema[1].toLowerCase()) ? url : '';
    }

    root.escapeHtml = escapeHtml;
    root.safeUrl = safeUrl;
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { escapeHtml, safeUrl };
    }
})(typeof window !== 'undefined' ? window : globalThis);
