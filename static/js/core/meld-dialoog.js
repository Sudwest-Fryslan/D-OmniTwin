/**
 * Terugmeldvoorziening dialoog (#311).
 *
 * Sluit aan op OmniMelden.zetKanaal() zodat alle meld-acties (centraal, AI-labels,
 * indicatorpaneel, chat) via deze toegankelijke native <dialog> verlopen.
 *
 * Toegankelijkheid (WCAG 2.1 AA / ADR 0011):
 * - Native HTML5 <dialog> met showModal() voor automatische focus-trapping en Escape-sluiting.
 * - Live-regio (role="status", aria-live="polite") voor statusbevestiging.
 * - Terugval-link naar de externe meldplek (OmniMelden.meldUrl) bij storing of netwerkfout.
 */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);

  let huidigeMelding = null;

  function initDialoog() {
    const dialoog = $('meld-dialoog');
    if (!dialoog) return;

    const form = $('meld-form');
    const sluitBtn = $('meld-dialoog-sluit');
    const annuleerBtn = $('meld-annuleer-btn');
    const verzendBtn = $('meld-verzend-btn');
    const statusBericht = $('meld-status-bericht');
    const terugvalWrap = $('meld-terugval-wrap');
    const terugvalLink = $('meld-terugval-link');
    const contextBanner = $('meld-context-banner');
    const contextTekst = $('meld-context-tekst');

    function resetFormulier() {
      form.reset();
      statusBericht.textContent = '';
      statusBericht.className = 'meld-status-bericht';
      terugvalWrap.hidden = true;
      verzendBtn.disabled = false;
      contextBanner.hidden = true;
      contextTekst.textContent = '';
      huidigeMelding = null;
    }

    function sluit() {
      dialoog.close();
      resetFormulier();
    }

    if (sluitBtn) sluitBtn.addEventListener('click', sluit);
    if (annuleerBtn) annuleerBtn.addEventListener('click', sluit);

    dialoog.addEventListener('cancel', () => {
      resetFormulier();
    });

    /**
     * Opent de dialoog, optioneel vooringevuld met context vanuit OmniMelden.
     * @param {Object} [m] - Meldingsobject { type, onderwerp, toelichting, context, titel, vraag, ... }
     */
    function openMeldDialoog(m) {
      resetFormulier();
      huidigeMelding = m || {};

      // Categorie bepalen
      let type = 'overig';
      if (huidigeMelding.onderwerp === 'ai' || huidigeMelding.usecase) {
        type = 'ai';
      } else if (huidigeMelding.indicator_id || huidigeMelding.type === 'data') {
        type = 'data';
      } else if (huidigeMelding.type === 'systeem') {
        type = 'systeem';
      } else if (huidigeMelding.type === 'overig') {
        type = 'overig';
      }
      $('meld-type').value = type;

      // Onderwerp vooringevuld
      if (huidigeMelding.titel) {
        $('meld-onderwerp').value = String(huidigeMelding.titel).slice(0, 120);
      } else if (huidigeMelding.onderwerp && huidigeMelding.onderwerp !== 'ai') {
        $('meld-onderwerp').value = String(huidigeMelding.onderwerp).slice(0, 120);
      }

      // Context tonen indien aanwezig
      const contextOmschrijving = [];
      if (huidigeMelding.usecase) {
        contextOmschrijving.push(`AI-usecase ${huidigeMelding.usecase}`);
      }
      if (huidigeMelding.indicator_naam) {
        let indTekst = `Indicator: ${huidigeMelding.indicator_naam}`;
        if (huidigeMelding.peiljaar) indTekst += ` (${huidigeMelding.peiljaar})`;
        contextOmschrijving.push(indTekst);
      } else if (huidigeMelding.indicator_id) {
        let indTekst = `Indicator: ${huidigeMelding.indicator_id}`;
        if (huidigeMelding.peiljaar) indTekst += ` (${huidigeMelding.peiljaar})`;
        contextOmschrijving.push(indTekst);
      }
      if (huidigeMelding.gebied_naam) {
        contextOmschrijving.push(`Gebied: ${huidigeMelding.gebied_naam}`);
      }
      if (huidigeMelding.pagina) {
        contextOmschrijving.push(`Pagina: ${huidigeMelding.pagina}`);
      }

      if (contextOmschrijving.length > 0) {
        contextTekst.textContent = contextOmschrijving.join(' | ');
        contextBanner.hidden = false;
      }

      // Toelichting vooringevuld met ingekort resultaat/vraag indien van toepassing
      if (huidigeMelding.toelichting) {
        $('meld-toelichting').value = huidigeMelding.toelichting;
      } else if (huidigeMelding.vraag || huidigeMelding.resultaat) {
        const toelichtingDelen = [];
        if (huidigeMelding.vraag) toelichtingDelen.push(`Vraag: ${huidigeMelding.vraag}`);
        if (huidigeMelding.resultaat) toelichtingDelen.push(`Resultaat: ${huidigeMelding.resultaat}`);
        $('meld-toelichting').value = toelichtingDelen.join('\n\n') + '\n\nToelichting: ';
      }

      // Toon als modale dialoog (focus trapping & backdrop van browser)
      if (typeof dialoog.showModal === 'function') {
        dialoog.showModal();
      } else {
        dialoog.setAttribute('open', '');
      }

      // Focus op eerste interactieve veld
      $('meld-onderwerp').focus();
    }

    // Registreer dit kanaal bij OmniMelden (#312)
    if (window.OmniMelden && typeof window.OmniMelden.zetKanaal === 'function') {
      window.OmniMelden.zetKanaal(openMeldDialoog);
    }

    // Formulier versturen
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const type = $('meld-type').value;
      const onderwerp = $('meld-onderwerp').value.trim();
      const toelichting = $('meld-toelichting').value.trim();
      const email = $('meld-email').value.trim();
      const website = $('meld-website').value.trim(); // honeypot

      if (!onderwerp || !toelichting) {
        statusBericht.textContent = 'Vul alstublieft een onderwerp en toelichting in.';
        statusBericht.className = 'meld-status-bericht meld-status-fout';
        return;
      }

      // Context samenstellen voor backend
      const state = window.state || {};
      const contextPayload = {
        pagina: window.location.pathname || 'viewer',
        versie: (document.querySelector('meta[name="d-omnitwin-versie"]') || {}).content || '',
      };

      if (huidigeMelding) {
        if (huidigeMelding.usecase) contextPayload.ai_usecase = huidigeMelding.usecase;
        if (huidigeMelding.vraag) contextPayload.vraag = String(huidigeMelding.vraag).slice(0, 300);
        if (huidigeMelding.resultaat) contextPayload.resultaat = String(huidigeMelding.resultaat).slice(0, 600);
        if (huidigeMelding.indicator_id) contextPayload.indicator_id = String(huidigeMelding.indicator_id);
        if (huidigeMelding.peiljaar) contextPayload.peiljaar = Number(huidigeMelding.peiljaar);
        if (huidigeMelding.bron) contextPayload.bron = String(huidigeMelding.bron).slice(0, 200);
      }

      if (state.currentIndicator && !contextPayload.indicator_id) {
        contextPayload.indicator_id = String(state.currentIndicator);
      }
      if (state.selectedGebiedIds && state.selectedGebiedIds.size > 0) {
        contextPayload.gebied_ids = Array.from(state.selectedGebiedIds).slice(0, 20);
      }

      const payload = {
        type: type,
        onderwerp: onderwerp,
        toelichting: toelichting,
        context: contextPayload,
        melder_email: email || null,
        website: website || null,
      };

      verzendBtn.disabled = true;
      statusBericht.textContent = 'Melding verzenden…';
      statusBericht.className = 'meld-status-bericht meld-status-bezig';
      terugvalWrap.hidden = true;

      try {
        const res = await fetch('/api/meldingen', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const foutData = await res.json().catch(() => ({}));
          throw new Error(foutData.detail || `Serverfout (${res.status})`);
        }

        statusBericht.textContent = '✓ Hartelijk dank! Uw melding is ontvangen.';
        statusBericht.className = 'meld-status-bericht meld-status-succes';

        setTimeout(() => {
          sluit();
        }, 1500);
      } catch (err) {
        statusBericht.textContent = `Verzenden mislukt: ${err.message || 'Server niet bereikbaar'}.`;
        statusBericht.className = 'meld-status-bericht meld-status-fout';
        verzendBtn.disabled = false;

        // Activeer terugval-link naar de instantie-meldplek (GitHub / mailto)
        if (window.OmniMelden && typeof window.OmniMelden.meldUrl === 'function') {
          const url = window.OmniMelden.meldUrl({
            titel: onderwerp,
            vraag: contextPayload.vraag,
            resultaat: toelichting,
            pagina: contextPayload.pagina,
          });
          terugvalLink.href = url;
          terugvalWrap.hidden = false;
        }
      }
    });

    // Koppel centrale trigger in Info-paneel
    const infoMeldBtn = $('info-meld-btn');
    if (infoMeldBtn) {
      infoMeldBtn.addEventListener('click', () => {
        openMeldDialoog({
          onderwerp: 'Algemene feedback of suggestie',
          pagina: 'Info-paneel',
        });
      });
    }

    // Koppel trigger in Indicatorpaneel
    const ipMeldBtn = $('ip-meld-btn');
    if (ipMeldBtn) {
      ipMeldBtn.addEventListener('click', () => {
        const s = window.state || {};
        const indNaam = ($('ip-naam') && $('ip-naam').textContent) || s.currentIndicator || '';
        openMeldDialoog({
          type: 'data',
          indicator_id: s.currentIndicator,
          indicator_naam: indNaam,
          titel: `Afwijking indicator ${indNaam}`.slice(0, 120),
          pagina: 'Indicatorpaneel',
        });
      });
    }

    // Koppel trigger in Kompas rechterpaneel (#311)
    const kompasMeldBtn = $('kompas-meld-btn');
    if (kompasMeldBtn) {
      kompasMeldBtn.addEventListener('click', () => {
        const s = window.state || {};
        const titleEl = $('details-title');
        const jaarEl = $('details-jaar');
        const bronEl = $('details-bron');
        const node = window.kompasViz && window.kompasViz.currentNode;

        const rawTitle = titleEl ? titleEl.textContent.trim() : '';
        const indNaam = (rawTitle && rawTitle !== 'Indicator Naam')
          ? rawTitle
          : (node && node.data && node.data.name) || '';
        const indUuid = (node && node.data && node.data.uuid) || s.currentIndicator || null;

        const rawJaar = jaarEl ? jaarEl.textContent.trim() : '';
        const jaar = (rawJaar && rawJaar !== '-') ? (parseInt(rawJaar, 10) || null) : null;

        const rawBron = bronEl ? bronEl.textContent.trim() : '';
        const bron = (rawBron && rawBron !== '-') ? rawBron : '';

        openMeldDialoog({
          type: 'data',
          indicator_id: indUuid,
          indicator_naam: indNaam,
          peiljaar: jaar,
          bron: bron,
          titel: indNaam ? `Afwijking indicator ${indNaam}`.slice(0, 120) : 'Afwijking in Kompas',
          pagina: 'Kompas',
        });
      });
    }

    // Koppel trigger in D-Omni Assistent header (#311)
    const chatMeldBtn = $('chat-meld-btn');
    if (chatMeldBtn) {
      chatMeldBtn.addEventListener('click', () => {
        // Haal eventueel laatste vraag en antwoord op uit het chat-venster
        const userMsgs = document.querySelectorAll('#chat-messages .chat-message-user p');
        const lastVraag = userMsgs.length > 0 ? userMsgs[userMsgs.length - 1].textContent.trim() : '';
        const assistantMsgs = document.querySelectorAll('#chat-messages .chat-message-assistant .chat-narrative');
        const lastAntwoord = (userMsgs.length > 0 && assistantMsgs.length > 0)
          ? assistantMsgs[assistantMsgs.length - 1].textContent.trim()
          : '';

        openMeldDialoog({
          type: 'ai',
          usecase: 'A',
          onderwerp: 'Feedback op D-Omni Assistent',
          titel: lastVraag ? `Feedback assistent: ${lastVraag}`.slice(0, 120) : 'Feedback op D-Omni Assistent',
          vraag: lastVraag || undefined,
          resultaat: lastAntwoord || undefined,
          pagina: 'D-Omni Assistent',
        });
      });
    }

    // Exporteer globale helper
    window.OmniMeldDialoog = { open: openMeldDialoog, sluit: sluit };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDialoog);
  } else {
    initDialoog();
  }
})();
