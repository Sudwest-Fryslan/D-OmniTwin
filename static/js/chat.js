/**
 * D-Omni Assistant — Chat Zijpaneel
 * Sprint 10: Intent-based chat met Command Dispatch
 * #445: Interactieve contextuele suggestie-chips & kaartsturing
 *
 * Architectuur:
 * - POST /api/chat → Command Dispatch JSON
 * - Actie-knoppen en suggestie-chips dispatchen EventBus events naar kaart/kompas/rapportkeuze
 * - Chat-historiek groeit omhoog (standaard chat-gedrag)
 */

/**
 * Kort lange indicator- of buurtlabels netjes in voor compacte chips.
 */
function kortChatLabel(tekst, maxLen = 32) {
    const schoon = String(tekst || '').trim();
    if (!schoon || schoon.length <= maxLen) return schoon;
    return schoon.slice(0, Math.max(1, maxLen - 1)).trimEnd() + '…';
}

/**
 * Bouwt contextuele start-chips op basis van de actieve kaart- en selectiestatus (#445).
 * Geen hardcoded plaats- of indicatornamen (ADR 0007): alles komt uit de actuele state.
 */
function bouwStartSuggestieChips(ctx = {}) {
    const indicatorUuid = ctx.indicatorUuid ? String(ctx.indicatorUuid) : '';
    const indicatorNaam = ctx.indicatorNaam ? String(ctx.indicatorNaam).trim() : '';
    const gebiedIds = Array.isArray(ctx.gebiedIds) ? ctx.gebiedIds.map(String).filter(Boolean) : [];
    const gebiedNamen = Array.isArray(ctx.gebiedNamen) ? ctx.gebiedNamen.map(String).filter(Boolean) : [];
    const gemeenteNaam = ctx.gemeenteNaam ? String(ctx.gemeenteNaam).trim() : '';
    const gemeenteSuffix = gemeenteNaam && !gemeenteNaam.startsWith('code ') ? ` in ${gemeenteNaam}` : '';

    const heeftIndicator = Boolean(indicatorUuid && indicatorNaam);
    const heeftGebied = gebiedIds.length > 0;
    const indLabel = kortChatLabel(indicatorNaam, 32);
    const buurtNaam = gebiedNamen[0] || gebiedIds[0] || '';
    const buurtLabel = gebiedIds.length === 1
        ? kortChatLabel(buurtNaam, 26)
        : `${gebiedIds.length} gebieden`;

    const chips = [];

    if (heeftIndicator && heeftGebied) {
        const werkwoord = gebiedIds.length === 1 ? 'scoort' : 'scoren';
        chips.push({
            type: 'VRAAG',
            label: `📊 Hoe ${werkwoord} ${buurtLabel} op ${indLabel}?`,
            title: `Vraag cijfers op voor ${indicatorNaam}`,
            vraag: gebiedIds.length === 1
                ? `Hoe scoort ${buurtNaam} op ${indicatorNaam}?`
                : `Hoe scoren deze gebieden op ${indicatorNaam}?`,
            extraContext: {
                gebruik_actieve_indicator: true,
                huidige_indicator_uuid: indicatorUuid,
            },
        });
        chips.push({
            type: 'VRAAG',
            label: `📉 5 laagste buurten op ${indLabel}`,
            title: `Bekijk de 5 buurten met de laagste waarde voor ${indicatorNaam}`,
            vraag: `Welke 5 buurten${gemeenteSuffix} scoren het laagst op ${indicatorNaam}?`,
            extraContext: {
                gebruik_actieve_indicator: true,
                huidige_indicator_uuid: indicatorUuid,
                negeer_kaartselectie: true,
            },
        });
        chips.push({
            type: 'OPEN_KOMPAS',
            label: `🧭 Open Kompas voor ${buurtLabel}`,
            title: 'Open het D-Omni Kompas voor de geselecteerde gebieden',
            gebiedIds,
        });
        chips.push({
            type: 'MAAK_RAPPORT',
            label: `📄 Kies rapport voor ${buurtLabel}`,
            title: 'Open de rapportkeuze voor de geselecteerde gebieden',
            gebiedIds,
        });
    } else if (heeftIndicator) {
        chips.push({
            type: 'VRAAG',
            label: `📉 5 laagste buurten op ${indLabel}`,
            title: `Bekijk de 5 buurten met de laagste waarde voor ${indicatorNaam}`,
            vraag: `Welke 5 buurten${gemeenteSuffix} scoren het laagst op ${indicatorNaam}?`,
            extraContext: {
                gebruik_actieve_indicator: true,
                huidige_indicator_uuid: indicatorUuid,
            },
        });
        chips.push({
            type: 'VRAAG',
            label: `📈 5 hoogste buurten op ${indLabel}`,
            title: `Bekijk de 5 buurten met de hoogste waarde voor ${indicatorNaam}`,
            vraag: `Welke 5 buurten${gemeenteSuffix} scoren het hoogst op ${indicatorNaam}?`,
            extraContext: {
                gebruik_actieve_indicator: true,
                huidige_indicator_uuid: indicatorUuid,
            },
        });
        chips.push({
            type: 'BEKIJK_IN_KOMPAS',
            label: `🧭 Bekijk ${indLabel} in Kompas`,
            title: `Open ${indicatorNaam} in het D-Omni Kompas`,
            indicatorUuid,
            indicatorNaam,
        });
    } else if (heeftGebied) {
        chips.push({
            type: 'OPEN_KOMPAS',
            label: `🧭 Open Kompas voor ${buurtLabel}`,
            title: 'Open het D-Omni Kompas voor de geselecteerde gebieden',
            gebiedIds,
        });
        chips.push({
            type: 'MAAK_RAPPORT',
            label: `📄 Kies rapport voor ${buurtLabel}`,
            title: 'Open de rapportkeuze voor de geselecteerde gebieden',
            gebiedIds,
        });
        chips.push({
            type: 'VRAAG',
            label: '❓ Wat kan ik hier vragen?',
            title: 'Bekijk mogelijkheden en rolprofielen',
            vraag: 'Wat kan jij?',
        });
    } else {
        chips.push({
            type: 'VRAAG',
            label: '❓ Wat kan ik hier vragen?',
            title: 'Bekijk mogelijkheden en rolprofielen',
            vraag: 'Wat kan jij?',
        });
        chips.push({
            type: 'OPEN_KOMPAS',
            label: '🧭 Open het Kompas',
            title: 'Open het D-Omni Kompas',
        });
    }

    return chips;
}

/**
 * Bouwt contextuele vervolgchips onder een assistent-antwoord (#445).
 * Voorkomt duplicaten met al meegeleverde backend-acties.
 */
function bouwVervolgChips(response = {}, ctx = {}) {
    if (!response || response.intent === 'HELP_ONBOARDING' || response.vraag_buurt) {
        return [];
    }

    const bestaandeTypes = new Set(
        Array.isArray(response.acties) ? response.acties.map(a => a?.type).filter(Boolean) : []
    );
    const antwoordGebieden = Array.isArray(response.kaart_actie?.gebied_ids)
        ? response.kaart_actie.gebied_ids.map(String).filter(Boolean)
        : [];
    const ctxGebieden = Array.isArray(ctx.gebiedIds) ? ctx.gebiedIds.map(String).filter(Boolean) : [];
    const gebiedIds = antwoordGebieden.length > 0 ? antwoordGebieden : ctxGebieden;

    const indicatoren = Array.isArray(response.indicatoren) ? response.indicatoren : [];
    const eersteInd = indicatoren[0] || null;
    const chips = [];

    if (eersteInd?.uuid && eersteInd?.naam && !bestaandeTypes.has('TOON_OP_KAART')) {
        chips.push({
            type: 'TOON_OP_KAART',
            label: `🗺️ Toon op kaart: ${kortChatLabel(eersteInd.naam, 28)}`,
            title: `Toon ${eersteInd.naam} op de kaart`,
            indicatorUuid: String(eersteInd.uuid),
            indicatorNaam: String(eersteInd.naam),
            gebiedIds: antwoordGebieden,
        });
    }

    if (gebiedIds.length > 0 && !bestaandeTypes.has('OPEN_KOMPAS')) {
        chips.push({
            type: 'OPEN_KOMPAS',
            label: '🧭 Open Kompas',
            title: 'Open het D-Omni Kompas voor deze selectie',
            gebiedIds,
        });
    }

    if (gebiedIds.length > 0 && !bestaandeTypes.has('MAAK_RAPPORT')) {
        chips.push({
            type: 'MAAK_RAPPORT',
            label: '📄 Kies rapport',
            title: 'Open de rapportkeuze voor deze selectie',
            gebiedIds,
        });
    }

    const topInd = (eersteInd?.uuid && eersteInd?.naam)
        ? { uuid: String(eersteInd.uuid), naam: String(eersteInd.naam) }
        : (ctx.indicatorUuid && ctx.indicatorNaam
            ? { uuid: String(ctx.indicatorUuid), naam: String(ctx.indicatorNaam) }
            : null);

    if (
        chips.length < 3
        && topInd
        && response.intent === 'DATAVRAAG'
        && response.debug?.gebieden_bron === 'kaart'
    ) {
        const gemNaam = ctx.gemeenteNaam ? String(ctx.gemeenteNaam).trim() : '';
        const gemSuffix = gemNaam && !gemNaam.startsWith('code ') ? ` in ${gemNaam}` : '';
        chips.push({
            type: 'VRAAG',
            label: `📉 5 laagste buurten op ${kortChatLabel(topInd.naam, 28)}`,
            title: `Bekijk de 5 laagste buurten voor ${topInd.naam}`,
            vraag: `Welke 5 buurten${gemSuffix} scoren het laagst op ${topInd.naam}?`,
            extraContext: {
                gebruik_actieve_indicator: true,
                huidige_indicator_uuid: topInd.uuid,
                negeer_kaartselectie: true,
            },
        });
    }

    return chips.slice(0, 3);
}

class ChatPanel {
    constructor() {
        this.panelEl = document.getElementById('dock-panel-chat') || document.getElementById('chat-panel');
        this.dockEl = document.getElementById('rechter-dock');
        this.contextBarEl = document.getElementById('chat-context-bar');
        this.startChipsEl = document.getElementById('chat-start-chips');
        this.messagesEl = document.getElementById('chat-messages');
        this.inputEl = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('chat-send-btn');
        this.toggleBtn = document.getElementById('chat-toggle-btn');
        this.closeBtn = document.getElementById('chat-close-btn');

        this.isOpen = false;
        this.isLoading = false;

        this._setupEventListeners();
        this.refreshContext();
        console.log('🤖 D-Omni Assistant ChatPanel initialized');
    }

    // ========================================================================
    // Panel Open / Close / Toggle
    // ========================================================================

    open() {
        this.isOpen = true;
        if (typeof window.openRechterDock === 'function') {
            window.openRechterDock('chat');
        } else if (this.panelEl) {
            this.panelEl.classList.add('open');
        }
        this.toggleBtn?.classList.add('active');
        this.refreshContext();
        setTimeout(() => this.inputEl?.focus(), 300);
    }

    close() {
        this.isOpen = false;
        if (typeof window.closeRechterDock === 'function') {
            window.closeRechterDock();
        } else if (this.panelEl) {
            this.panelEl.classList.remove('open');
        }
        this.toggleBtn?.classList.remove('active');
    }

    toggle() {
        const isDockOpen = this.dockEl && !this.dockEl.classList.contains('collapsed');
        const isChatActive = document.getElementById('dock-panel-chat')?.classList.contains('active');
        if (isDockOpen && isChatActive) {
            this.close();
        } else {
            this.open();
        }
    }

    // ========================================================================
    // Chat Berichten
    // ========================================================================

    /**
     * Voegt een gebruikersbericht toe aan de historiek.
     */
    addUserMessage(text) {
        const block = document.createElement('div');
        block.className = 'chat-message chat-message-user';
        block.innerHTML = `
            <div class="chat-message-bubble user">
                <p>${this._escapeHtml(text)}</p>
            </div>
        `;
        this.messagesEl.appendChild(block);
        this._scrollToBottom();
    }

    /**
     * Voegt een loading indicator toe (wordt vervangen door het antwoord).
     */
    addLoadingIndicator() {
        const block = document.createElement('div');
        block.className = 'chat-message chat-message-assistant';
        block.id = 'chat-loading';
        block.innerHTML = `
            <div class="chat-message-bubble assistant">
                <div class="chat-loading-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        this.messagesEl.appendChild(block);
        this._scrollToBottom();
    }

    /**
     * Vervangt de loading met het echte antwoord.
     */
    addAssistantMessage(response, vraag = '') {
        // Verwijder loading indicator
        const loading = document.getElementById('chat-loading');
        if (loading) loading.remove();

        // Alles via de DOM-API (textContent/dataset): API-data komt nooit als HTML binnen (#149)
        const el = (tag, className, text) => {
            const node = document.createElement(tag);
            if (className) node.className = className;
            if (text !== undefined && text !== null) node.textContent = text;
            return node;
        };

        const block = el('div', 'chat-message chat-message-assistant');
        const bubble = el('div', 'chat-message-bubble assistant');
        block.appendChild(bubble);

        // Track E: Bronlabel (governance). #312: welke AI meedeed, zegt de backend (ai_usecases)
        const mode = response.debug?.mode || 'unknown';
        const isDatavraag = mode === 'datavraag';
        const aiUsecases = Array.isArray(response.ai_usecases) ? response.ai_usecases : [];
        const isLLM = aiUsecases.includes('A');
        const isRuleBased = !isLLM && (mode === 'deterministic_onboarding' || mode === 'zonder_ai' || isDatavraag);

        if (isRuleBased) {
            bubble.appendChild(el('span', 'chat-source-badge source-rule', '📐 Zonder taalmodel'));
        }

        // #233: van welke buurt het antwoord uitgaat (selectie op de kaart), vóór het antwoord
        if (response.aanname) {
            bubble.appendChild(el('p', 'chat-aanname', response.aanname));
        }

        // Narrative tekst
        if (response.narrative) {
            bubble.appendChild(el('p', 'chat-narrative', response.narrative));
        }

        // #336: 'bij mij in de buurt' zonder selectie: eigen buurt via postcode/adres of locatie
        if (response.vraag_buurt) {
            bubble.appendChild(this._buurtKiezer(vraag));
        }

        // #149: bronregel bij een datavraag (indicator, jaar, bron)
        if (Array.isArray(response.bronnen) && response.bronnen.length > 0) {
            const regel = response.bronnen
                .map(b => `${b.indicator} (${(b.jaren || []).join(', ') || 'jaar onbekend'}): ${b.bron}`)
                .join(' · ');
            bubble.appendChild(el('p', 'chat-bronregel', `Bron: ${regel}`));
        }

        // #233: melding over de zekerheid (geen of alleen matige treffers)
        if (response.melding) {
            bubble.appendChild(el('p', 'chat-melding', response.melding));
        }

        // #312: label AI per usecase die meedeed (A taalmodel, C zoeken op betekenis), met de
        // verklaring ("Meer informatie") en "Melden"
        if (window.OmniAI) {
            const bronnen = (Array.isArray(response.bronnen) && response.bronnen.length)
                ? response.bronnen.map(b => `${b.indicator} (${b.bron})`)
                : (response.indicatoren || []).map(i => i.naam).filter(Boolean);
            for (const code of aiUsecases) {
                bubble.appendChild(window.OmniAI.label({
                    usecase: code, vraag,
                    resultaat: code === 'A' ? response.narrative : bronnen.join(', '),
                    bronnen, pagina: 'Viewer: D-Omni Assistent',
                }));
            }
        }

        // Actie-knoppen
        if (response.acties && response.acties.length > 0) {
            const acties = el('div', 'chat-acties');
            for (const actie of response.acties) {
                const btn = el('button', 'chat-actie-btn', actie.label || '');
                btn.type = 'button';
                btn.title = actie.label || '';
                btn.dataset.type = actie.type || '';
                btn.dataset.uuid = actie.indicator_uuid || '';
                btn.dataset.gemeenteCode = actie.gemeente_code || '';
                btn.dataset.gebiedstypeId = actie.gebiedstype_id || '';
                btn.dataset.configId = actie.config_id || '';
                btn.dataset.filters = JSON.stringify(actie.filters || {});
                btn.dataset.thema = actie.thema || '';
                btn.dataset.rolCode = actie.rol_code || '';
                btn.dataset.gebiedIds = Array.isArray(actie.gebied_ids) ? actie.gebied_ids.join(',') : '';
                btn.addEventListener('click', () => this._handleActie(btn));
                acties.appendChild(btn);
            }
            bubble.appendChild(acties);
        }

        // Gevonden indicatoren (scrollbare lijst)
        if (response.indicatoren && response.indicatoren.length > 0) {
            const lijst = el('div', 'chat-indicatoren-lijst');
            // #233: bij een datavraag zijn dit de indicatoren onder het antwoord, anders zoekresultaten
            const n = response.indicatoren.length;
            const kop = isDatavraag ? `Onderbouwing: ${n === 1 ? '1 indicator' : `${n} indicatoren`}`
                : `${n === 1 ? '1 indicator' : `${n} indicatoren`} gevonden`;
            lijst.appendChild(el('span', 'chat-indicatoren-label', kop));
            for (const ind of response.indicatoren) {
                const item = el('div', 'chat-indicator-item');
                item.setAttribute('role', 'button');
                item.tabIndex = 0;
                item.dataset.uuid = ind.uuid || '';
                item.title = 'Klik om op kaart te tonen';
                item.appendChild(el('span', 'chat-ind-naam', ind.naam || ''));
                // #233: relevantie als woord, geen percentage (dat lijkt een datawaarde, zoals '80 jaar of ouder 53%')
                if (ind.relevantie_label) {
                    const label = el('span', 'chat-ind-score', ind.relevantie_label);
                    label.title = 'Hoe goed deze indicator bij je vraag past';
                    item.appendChild(label);
                }
                item.addEventListener('click', () => this._handleIndicatorClick(item));

                // FE-5.3: Actiechip om indicator in Kompas te bekijken zonder gedwongen tabwissel
                const chip = el('button', 'chat-action-chip', '📊 Bekijk in Kompas');
                chip.type = 'button';
                chip.title = `Bekijk '${ind.naam || 'indicator'}' in het Kompas`;
                chip.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (typeof window.switchDockTab === 'function') {
                        window.switchDockTab('kompas');
                    }
                    if (ind.uuid && window.EventBus) {
                        window.EventBus.emit('INDICATOR_SELECTED', {
                            uuid: ind.uuid,
                            name: ind.naam || '',
                            bron: 'kompas-bekijken',
                        });
                    }
                });
                item.appendChild(chip);

                lijst.appendChild(item);
            }
            bubble.appendChild(lijst);
        }

        // #445: Contextuele vervolgchips onder het antwoord (zonder duplicaten met backend-acties)
        const vervolgChips = bouwVervolgChips(response, this._getUiContext());
        if (vervolgChips.length > 0) {
            const vervolgEl = el('div', 'chat-vervolg-chips');
            vervolgEl.appendChild(el('span', 'chat-vervolg-label', 'Vervolgacties'));
            for (const chip of vervolgChips) {
                vervolgEl.appendChild(this._maakChipKnop(chip, { markeerActief: true }));
            }
            bubble.appendChild(vervolgEl);
        }

        this.messagesEl.appendChild(block);
        this._scrollToBottom();

        // #149: de kaart beweegt mee met een antwoord op een datavraag (zonder klik);
        // de knoppen blijven staan om terug te gaan of verder te klikken.
        const ka = response.kaart_actie;
        if (ka && Array.isArray(ka.gebied_ids) && ka.gebied_ids.length > 0 && window.EventBus) {
            window.EventBus.emit('CHAT_GEBIEDEN_TONEN', {
                ids: ka.gebied_ids,
                uuid: ka.indicator_uuid || null,
                name: ka.indicator || '',
                gebiedstypeId: ka.gebiedstype_id || null,
                gemeenteCode: ka.gemeente_code || null,
                zoom: true
            });
        }
    }

    /**
     * Voegt een foutmelding toe.
     */
    addErrorMessage(error) {
        const loading = document.getElementById('chat-loading');
        if (loading) loading.remove();

        const block = document.createElement('div');
        block.className = 'chat-message chat-message-assistant';
        block.innerHTML = `
            <div class="chat-message-bubble assistant error">
                <p>⚠️ Er ging iets mis: ${this._escapeHtml(error)}</p>
            </div>
        `;
        this.messagesEl.appendChild(block);
        this._scrollToBottom();
    }

    // ========================================================================
    // API Communicatie
    // ========================================================================

    async sendVraag(tekst, extraContext = {}) {
        if (!tekst.trim() || this.isLoading) return;

        this.isLoading = true;
        this.inputEl.value = '';
        this._updateSendButton();

        // Gebruikersbericht toevoegen
        this.addUserMessage(tekst);
        this.addLoadingIndicator();

        try {
            const basisContext = this._getKaartContext();
            const { negeer_kaartselectie, ...restExtra } = extraContext || {};
            if (negeer_kaartselectie) {
                delete basisContext.huidig_gebied_id;
                delete basisContext.geselecteerde_gebied_ids;
            }
            const context = { ...basisContext, ...restExtra };
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    vraag: tekst,
                    context: context
                })
            });

            if (!response.ok) {
                throw new Error(`Server fout (${response.status})`);
            }

            const data = await response.json();
            console.log('🤖 Chat response:', data.intent, data.acties?.length, 'acties');
            this.addAssistantMessage(data, tekst);

        } catch (error) {
            console.error('❌ Chat error:', error);
            this.addErrorMessage(error.message || 'Onbekende fout');
        } finally {
            this.isLoading = false;
            this._updateSendButton();
        }
    }

    /**
     * #336 / #442: formulier "Welke buurt is jouw buurt?": postcode/adres of (na toestemming) de locatie.
     * Gedeeld via static/js/core/buurtkiezer.js.
     */
    _buurtKiezer(vraag) {
        return window.BuurtKiezer.maak({
            idPrefix: 'chat-adres',
            onGevonden: ({ gebied_id, gemeente_code, gebiedstype_id, herkomst }) => {
                if (window.EventBus) {
                    window.EventBus.emit('CHAT_GEBIEDEN_TONEN', {
                        ids: [gebied_id],
                        gemeenteCode: gemeente_code || null,
                        gebiedstypeId: gebiedstype_id || null,
                        zoom: true,
                    });
                }
                this.sendVraag(vraag, {
                    huidig_gebied_id: gebied_id,
                    geselecteerde_gebied_ids: [gebied_id],
                    buurt_herkomst: herkomst,
                });
            },
        });
    }

    // ========================================================================
    // Actie Handlers (Command Dispatch → EventBus)
    // ========================================================================

    _handleActie(btn, opts = {}) {
        const markeerActief = opts.markeerActief !== false;
        const type = btn.dataset.type;
        const uuid = btn.dataset.uuid;
        const thema = btn.dataset.thema;
        const gebiedIds = (btn.dataset.gebiedIds || '').split(',').filter(Boolean);

        console.log(`🎯 Chat actie: ${type}`, { 
            uuid, 
            gemeente: btn.dataset.gemeenteCode,
            gebiedstype: btn.dataset.gebiedstypeId,
            config: btn.dataset.configId
        });

        // Visuele feedback: voeg vinkje toe en verander stijl (behalve herbruikbare start-chips)
        const originalText = btn.textContent;
        if (markeerActief && !originalText.startsWith('✅')) {
            btn.textContent = '✅ ' + originalText;
            btn.classList.add('actie-activated');
        }

        switch (type) {
            case 'TOON_OP_KAART':
                if (gebiedIds.length > 0 && window.EventBus) {
                    // #149: indicator tonen én de gebieden uit het antwoord selecteren
                    window.EventBus.emit('CHAT_GEBIEDEN_TONEN', {
                        ids: gebiedIds,
                        gebiedstypeId: btn.dataset.gebiedstypeId || null, gemeenteCode: btn.dataset.gemeenteCode || null,
                        uuid: uuid || null,
                        zoom: true,
                        name: btn.dataset.indicatorNaam || originalText.replace(/^[🗺📋📄\s\uFE0F]+/, '').replace(/^Toon( op kaart)?: /, '')
                    });
                } else if (uuid && window.EventBus) {
                    window.EventBus.emit('INDICATOR_SELECTED', {
                        uuid: uuid,
                        name: btn.dataset.indicatorNaam || originalText.replace(/^[🗺📋📄\s\uFE0F]+/, '').replace(/^Toon( op kaart)?: /, '')
                    });
                }
                break;

            case 'SELECTEER_BUURTEN':
                if (uuid && window.EventBus) {
                    window.EventBus.emit('INDICATOR_SELECTED', {
                        uuid: uuid,
                        name: btn.dataset.indicatorNaam || originalText.replace(/^[🗺📋📄\s\uFE0F]+/, '')
                    });
                }
                break;

            case 'MAAK_RAPPORT': {
                // #445: Open de bestaande rapportkeuze-modal via EventBus (gebruiker kiest zelf het rapporttype)
                const geselecteerd = gebiedIds.length > 0
                    ? gebiedIds
                    : (window.state?.selectedGebiedIds ? [...window.state.selectedGebiedIds] : []);

                if (window.EventBus) {
                    window.EventBus.emit('MAAK_RAPPORT', {
                        ids: geselecteerd,
                        thema: thema || null,
                    });
                } else if (geselecteerd.length === 0) {
                    window.open('/rapport/benchmark', '_blank', 'noopener,noreferrer');
                } else if (geselecteerd.length === 1) {
                    window.open(`/rapport/${geselecteerd[0]}`, '_blank', 'noopener,noreferrer');
                } else {
                    const [a, ...rest] = geselecteerd;
                    window.open(
                        `/rapport/benchmark?gebied_a=${a}&gebieden_b=${rest.join(',')}`,
                        '_blank',
                        'noopener,noreferrer'
                    );
                }
                break;
            }

            case 'BEKIJK_IN_KOMPAS':
                if (typeof window.openRechterDock === 'function') {
                    window.openRechterDock('kompas', false, true);
                } else if (typeof window.switchDockTab === 'function') {
                    window.switchDockTab('kompas');
                }
                if (uuid && window.EventBus) {
                    window.EventBus.emit('INDICATOR_SELECTED', {
                        uuid,
                        name: btn.dataset.indicatorNaam || originalText,
                        bron: 'kompas-bekijken',
                    });
                }
                break;

            case 'VRAAG': {
                const vraagTekst = btn.dataset.vraag || '';
                let extraContext = {};
                if (btn.dataset.extraContext) {
                    try {
                        extraContext = JSON.parse(btn.dataset.extraContext);
                    } catch (e) {
                        extraContext = {};
                    }
                }
                if (vraagTekst) {
                    this.sendVraag(vraagTekst, extraContext);
                }
                break;
            }
            
            case 'SELECTEER_GEMEENTE':
                if (btn.dataset.gemeenteCode && window.EventBus) {
                    window.EventBus.emit('GEMEENTE_SELECTED', {
                        code: btn.dataset.gemeenteCode,
                        name: originalText.replace(/^[📍🗺🏙🧭✅\s\uFE0F]+(Gemeente: )?/, '')
                    });
                }
                break;
                
            case 'SELECTEER_GEBIEDSTYPE':
                if (window.EventBus) {
                    window.EventBus.emit('GEBIEDSTYPE_SELECTED', {
                        id: btn.dataset.gebiedstypeId || '',
                        name: originalText.replace(/^[📍🗺🏙🧭✅\s\uFE0F]+(Toon: )?/, '')
                    });
                }
                break;
                
            case 'SELECTEER_KOMPAS':
                if (btn.dataset.configId && window.EventBus) {
                    window.EventBus.emit('KOMPAS_CONFIG_SELECTED', {
                        id: parseInt(btn.dataset.configId),
                        name: originalText.replace(/^[📍🗺🏙🧭✅\s\uFE0F]+(Wissel: )?/, '')
                    });
                }
                break;
                
            case 'OPEN_KOMPAS':
                if (gebiedIds.length > 0 && window.EventBus) {
                    // #149: eerst de gebieden uit het antwoord selecteren, dan het Kompas daarvoor openen
                    window.EventBus.emit('CHAT_GEBIEDEN_TONEN', {
                        ids: gebiedIds, gebiedstypeId: btn.dataset.gebiedstypeId || null, gemeenteCode: btn.dataset.gemeenteCode || null, openKompas: true
                    });
                } else if (window.EventBus) {
                    window.EventBus.emit('KOMPAS_OPEN_REQUESTED');
                }
                break;

            case 'SEND_MESSAGE':
                if (btn.dataset.rolCode) {
                    const rolNaam = originalText.replace(/^[👤✅\s]+/, '');
                    this.sendVraag(rolNaam, { rol_code: btn.dataset.rolCode });
                }
                break;

            // ── Help / Onboarding acties (deterministic, geen LLM) ──
            case 'INFO_KAART':
                this._showInfoCard(btn,
                    '🗺️ Kaart & Gebieden',
                    'Selecteer een gemeente en gebiedstype (buurten, wijken) in de linker configuratiepaneel. ' +
                    'Kies een indicator om de kaart in te kleuren. Klik op een gebied voor details. ' +
                    'Gebruik de 3D-slider om patronen ruimtelijk te zien.'
                );
                break;

            case 'INFO_KOMPAS':
                this._showInfoCard(btn,
                    '🧭 Het D-Omni Kompas',
                    'Het Kompas is een interactieve zondiagram (Sunburst) dat 200+ indicatoren ordent in thema\'s. ' +
                    'Klik op een gebied op de kaart → het Kompas kleurt automatisch in. ' +
                    'Klik op een indicator in het Kompas → de kaart past zich aan.'
                );
                break;

            case 'INFO_RAPPORT':
                this._showInfoCard(btn,
                    '📄 Rapporten & Analyses',
                    'Selecteer één of meerdere gebieden op de kaart en klik op "Rapport" in de badge. ' +
                    'Eén selectie = Gebiedsdossier (AI-samenvatting). Meerdere selecties = Benchmark vergelijking. ' +
                    'Of vraag mij: "Maak een rapport".'
                );
                break;

            case 'OPEN_WIKI':
                window.open('/static/help.html', '_blank', 'noopener,noreferrer');
                break;

            default:
                console.warn('Onbekend actie type:', type);
        }
    }

    _handleIndicatorClick(item) {
        const uuid = item.dataset.uuid;
        const naam = item.querySelector('.chat-ind-naam')?.textContent || '';

        console.log(`📊 Chat indicator click: ${naam}`, uuid);

        if (uuid && window.EventBus) {
            window.EventBus.emit('INDICATOR_SELECTED', {
                uuid: uuid,
                name: naam
            });

            // Markeer als actief
            item.closest('.chat-indicatoren-lijst')
                ?.querySelectorAll('.chat-indicator-item')
                .forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        }
    }

    // ========================================================================
    // Contextbalk & Dynamische Suggestie-chips (#445)
    // ========================================================================

    _getUiContext() {
        const st = window.state || {};
        const gebiedIds = st.selectedGebiedIds ? [...st.selectedGebiedIds].map(String).filter(Boolean) : [];
        const gebiedNamen = typeof window.getSelectedGebiedNamen === 'function'
            ? window.getSelectedGebiedNamen()
            : [];
        const gemeenteCode = st.currentGemeenteCode ? String(st.currentGemeenteCode) : '';
        const gemeenteNaam = typeof window.getActieveGemeenteNaam === 'function'
            ? window.getActieveGemeenteNaam()
            : null;
        return {
            indicatorUuid: st.currentIndicator ? String(st.currentIndicator) : '',
            indicatorNaam: st.currentIndicatorNaam ? String(st.currentIndicatorNaam) : '',
            gebiedIds,
            gebiedNamen: Array.isArray(gebiedNamen) ? gebiedNamen : [],
            gemeenteCode,
            gemeenteNaam: gemeenteNaam || '',
        };
    }

    _maakChipKnop(chip, opts = {}) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'chat-suggestie-chip';
        btn.textContent = chip.label || '';
        btn.title = chip.title || chip.label || '';
        btn.dataset.type = chip.type || '';
        if (opts.dynamicStart) btn.dataset.dynamicChip = 'true';
        if (chip.indicatorUuid) btn.dataset.uuid = chip.indicatorUuid;
        if (chip.indicatorNaam) btn.dataset.indicatorNaam = chip.indicatorNaam;
        if (Array.isArray(chip.gebiedIds) && chip.gebiedIds.length > 0) {
            btn.dataset.gebiedIds = chip.gebiedIds.join(',');
        }
        if (chip.vraag) btn.dataset.vraag = chip.vraag;
        if (chip.extraContext) btn.dataset.extraContext = JSON.stringify(chip.extraContext);
        btn.addEventListener('click', () => this._handleActie(btn, { markeerActief: opts.markeerActief }));
        return btn;
    }

    refreshContext() {
        const ctx = this._getUiContext();
        this._renderContextBar(ctx);
        this._renderStartChips(ctx);
    }

    _renderContextBar(ctx) {
        if (!this.contextBarEl) return;
        this.contextBarEl.textContent = '';

        const pills = [];
        if (ctx.indicatorNaam) {
            pills.push({ tekst: `📊 ${kortChatLabel(ctx.indicatorNaam, 34)}`, title: `Actieve indicator: ${ctx.indicatorNaam}` });
        }
        if (ctx.gebiedIds.length === 1) {
            const naam = ctx.gebiedNamen[0] || ctx.gebiedIds[0];
            pills.push({ tekst: `📍 ${kortChatLabel(naam, 26)}`, title: `Geselecteerd gebied: ${naam}` });
        } else if (ctx.gebiedIds.length > 1) {
            pills.push({ tekst: `📍 ${ctx.gebiedIds.length} gebieden`, title: `${ctx.gebiedIds.length} gebieden geselecteerd` });
        } else if (ctx.gemeenteNaam) {
            pills.push({ tekst: `🗺️ ${kortChatLabel(ctx.gemeenteNaam, 26)}`, title: `Actief gemeentefilter: ${ctx.gemeenteNaam}` });
        }

        if (pills.length === 0) {
            this.contextBarEl.hidden = true;
            return;
        }

        const label = document.createElement('span');
        label.className = 'chat-context-label';
        label.textContent = 'Actief:';
        this.contextBarEl.appendChild(label);

        for (const p of pills) {
            const pill = document.createElement('span');
            pill.className = 'chat-context-pill';
            pill.textContent = p.tekst;
            pill.title = p.title;
            this.contextBarEl.appendChild(pill);
        }
        this.contextBarEl.hidden = false;
    }

    _renderStartChips(ctx) {
        if (!this.startChipsEl) return;
        // Verwijder alleen dynamische chips; behoud #chat-start-tour-btn en zijn click-listener (#442)
        this.startChipsEl.querySelectorAll('[data-dynamic-chip="true"]').forEach(el => el.remove());

        const tourBtn = this.startChipsEl.querySelector('#chat-start-tour-btn');
        const chips = bouwStartSuggestieChips(ctx);
        for (const chip of chips) {
            const btn = this._maakChipKnop(chip, { dynamicStart: true, markeerActief: false });
            if (tourBtn) {
                this.startChipsEl.insertBefore(btn, tourBtn);
            } else {
                this.startChipsEl.appendChild(btn);
            }
        }
    }

    // ========================================================================
    // Interne Helpers
    // ========================================================================

    _setupEventListeners() {
        // Toggle knop wordt gecoördineerd via initRechterDock() in app.js

        // Sluit knop
        this.closeBtn?.addEventListener('click', () => this.close());

        // Enter toets
        this.inputEl?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendVraag(this.inputEl.value);
            }
        });

        // Verstuur knop
        this.sendBtn?.addEventListener('click', () => {
            this.sendVraag(this.inputEl.value);
        });

        // Input state
        this.inputEl?.addEventListener('input', () => this._updateSendButton());

        // #445: Contextbalk en start-chips direct meebewegen met kaart-, selectie- en indicatorwijzigingen
        if (window.EventBus) {
            const ververs = () => this.refreshContext();
            window.EventBus.on('INDICATOR_SELECTED', ververs);
            window.EventBus.on('INDICATOR_CLEARED', ververs);
            window.EventBus.on('SELECTIE_GEWIJZIGD', ververs);
            window.EventBus.on('KAARTDATA_GELADEN', ververs);
            window.EventBus.on('GEMEENTE_GEWIJZIGD', ververs);
        }
    }

    _updateSendButton() {
        if (!this.sendBtn) return;
        const hasText = this.inputEl?.value.trim().length > 0;
        this.sendBtn.disabled = !hasText || this.isLoading;
    }

    _getKaartContext() {
        // Haal huidige kaart-staat op als context voor de LLM en datavraag-route
        const context = {};
        // #233: 'bij mij in de buurt' = de selectie op de kaart (ook een multi-selectie)
        if (window.state?.selectedGebiedId) {
            context.huidig_gebied_id = window.state.selectedGebiedId;
        }
        if (window.state?.selectedGebiedIds?.size > 0) {
            context.geselecteerde_gebied_ids = [...window.state.selectedGebiedIds].slice(0, 50);
        }
        if (window.state?.currentIndicator) {
            context.huidige_indicator_uuid = window.state.currentIndicator;
        }
        if (window.state?.currentGemeenteCode) {
            context.huidige_gemeente_code = window.state.currentGemeenteCode;
        }
        return context;
    }

    _scrollToBottom() {
        if (this.messagesEl) {
            this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
        }
    }

    _escapeHtml(text) {
        // Centrale escaping (static/js/core/escape.js); ook aanhalingstekens voor attributen
        return escapeHtml(text);
    }

    /**
     * Toont een inline info-card in de chat als reactie op een help-knop.
     * Vervangt de knop-tekst met een ✅ en toont de uitleg eronder.
     */
    _showInfoCard(btn, titel, tekst) {
        // Visuele feedback op de knop
        const originalText = btn.textContent;
        if (!originalText.startsWith('✅')) {
            btn.textContent = '✅ ' + originalText;
            btn.classList.add('actie-activated');
        }

        // Check of er al een info-card zit (voorkom duplicaten)
        const existing = btn.parentElement?.querySelector(`.chat-info-card[data-title="${CSS.escape(titel)}"]`);
        if (existing) return;

        // Maak de info-card
        const card = document.createElement('div');
        card.className = 'chat-info-card';
        card.dataset.title = titel;
        card.innerHTML = `
            <strong>${this._escapeHtml(titel)}</strong>
            <p>${this._escapeHtml(tekst)}</p>
        `;
        
        // Voeg toe na de knop (binnen de acties-container)
        btn.insertAdjacentElement('afterend', card);
        this._scrollToBottom();
    }
}

// ============================================================================
// Initialisatie — wacht op DOM
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    window.chatPanel = new ChatPanel();
});
