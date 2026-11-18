/**
 * Gedeelde buurtkiezer via postcode/adres of browserlocatie (#336, #442).
 *
 * Gebruikt POST /api/locatie/buurt (PDOK Locatieserver via backend, geen opslag).
 * Wordt gedeeld tussen de D-Omni Assistent (chat.js) en de welkomstmodal (app.js).
 */
(function () {
    'use strict';

    let _teller = 0;

    /**
     * Bouw een formulier om een buurt te zoeken op postcode/adres of locatie.
     *
     * @param {object} opts
     * @param {Function} opts.onGevonden  ({ gebied_id, naam, gemeente_code, gebiedstype_id, herkomst, statusEl }) => void | Promise<void>
     * @param {string}   [opts.idPrefix='chat-adres']
     * @param {string}   [opts.extraClass='']
     * @returns {HTMLFormElement}
     */
    function maak(opts = {}) {
        const onGevonden = opts.onGevonden;
        const prefix = opts.idPrefix || 'chat-adres';
        _teller += 1;
        const id = `${prefix}-${Date.now()}-${_teller}`;

        const form = document.createElement('form');
        form.className = opts.extraClass ? `chat-buurtkiezer ${opts.extraClass}` : 'chat-buurtkiezer';
        form.noValidate = true;

        const label = document.createElement('label');
        label.htmlFor = id;
        label.textContent = 'Postcode, adres of buurtnaam';

        const rij = document.createElement('div');
        rij.className = 'chat-buurtkiezer-rij';

        const input = document.createElement('input');
        input.id = id;
        input.type = 'text';
        input.autocomplete = 'postal-code';
        input.placeholder = 'bijv. 8601 CR of buurtnaam';
        input.maxLength = 200;

        const zoek = document.createElement('button');
        zoek.type = 'submit';
        zoek.className = 'chat-actie-btn';
        zoek.textContent = 'Zoek mijn buurt';
        rij.append(input, zoek);

        const status = document.createElement('p');
        status.className = 'chat-buurtkiezer-status';
        status.setAttribute('role', 'status');

        const privacy = document.createElement('p');
        privacy.className = 'chat-buurtkiezer-privacy';
        privacy.textContent = 'We gebruiken je postcode, adres of locatie alleen om je buurt te vinden '
            + '(via de PDOK Locatieserver) en bewaren die niet.';

        async function voerZoekUit(body, herkomst) {
            status.textContent = 'Buurt zoeken…';
            try {
                const r = await fetch('/api/locatie/buurt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                const data = await r.json().catch(() => ({}));
                if (!r.ok) {
                    const detail = typeof data.detail === 'string' ? data.detail : (data.melding || data.message);
                    status.textContent = detail || `Buurt niet gevonden (${r.status}).`;
                    return;
                }
                status.textContent = `Gevonden: ${data.naam}.`;
                if (typeof onGevonden === 'function') {
                    await onGevonden({
                        gebied_id: data.gebied_id,
                        naam: data.naam,
                        gemeente_code: data.gemeente_code || null,
                        gebiedstype_id: data.gebiedstype_id || null,
                        herkomst,
                        statusEl: status,
                    });
                }
            } catch (e) {
                status.textContent = 'Zoeken lukt nu niet. Selecteer je buurt op de kaart.';
            }
        }

        form.append(label, rij);
        if (navigator.geolocation) {
            const locatie = document.createElement('button');
            locatie.type = 'button';
            locatie.className = 'chat-actie-btn';
            locatie.textContent = '📍 Gebruik mijn locatie';
            locatie.addEventListener('click', () => {
                status.textContent = 'Je browser vraagt toestemming voor je locatie…';
                navigator.geolocation.getCurrentPosition(
                    pos => voerZoekUit({ lat: pos.coords.latitude, lon: pos.coords.longitude }, 'locatie'),
                    () => {
                        status.textContent = 'Geen locatie: geen toestemming of niet beschikbaar. Vul een postcode in of selecteer je buurt op de kaart.';
                    },
                    { enableHighAccuracy: false, timeout: 15000, maximumAge: 600000 }
                );
            });
            form.appendChild(locatie);
        }
        form.append(status, privacy);

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const adres = input.value.trim();
            if (!adres) {
                status.textContent = 'Vul een postcode, adres of buurtnaam in.';
                input.focus();
                return;
            }
            voerZoekUit({ adres }, 'adres');
        });

        return form;
    }

    window.BuurtKiezer = { maak };
})();
