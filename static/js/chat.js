/**
 * D-Omni Assistant — Chat Zijpaneel
 * Sprint 10: Intent-based chat met Command Dispatch
 * 
 * Architectuur:
 * - POST /api/chat → Command Dispatch JSON
 * - Actie-knoppen dispatchen EventBus events naar kaart/kompas
 * - Chat-historiek groeit omhoog (standaard chat-gedrag)
 */

class ChatPanel {
    constructor() {
        this.panelEl = document.getElementById('chat-panel');
        this.messagesEl = document.getElementById('chat-messages');
        this.inputEl = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('chat-send-btn');
        this.toggleBtn = document.getElementById('chat-toggle-btn');
        this.closeBtn = document.getElementById('chat-close-btn');
        
        this.isOpen = false;
        this.isLoading = false;
        
        this._setupEventListeners();
        console.log('🤖 D-Omni Assistant ChatPanel initialized');
    }

    // ========================================================================
    // Panel Open / Close / Toggle
    // ========================================================================

    open() {
        if (!this.panelEl) return;
        this.isOpen = true;
        this.panelEl.classList.add('open');
        this.toggleBtn?.classList.add('active');
        // Focus op input
        setTimeout(() => this.inputEl?.focus(), 300);
    }

    close() {
        if (!this.panelEl) return;
        this.isOpen = false;
        this.panelEl.classList.remove('open');
        this.toggleBtn?.classList.remove('active');
    }

    toggle() {
        this.isOpen ? this.close() : this.open();
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
    addAssistantMessage(response) {
        // Verwijder loading indicator
        const loading = document.getElementById('chat-loading');
        if (loading) loading.remove();

        const block = document.createElement('div');
        block.className = 'chat-message chat-message-assistant';
        
        let html = `<div class="chat-message-bubble assistant">`;
        
        // Track E: Bronlabel (governance)
        const mode = response.debug?.mode || 'unknown';
        const isLLM = mode === 'intelligent_dispatcher' || mode === 'legacy_fallback';
        const isRuleBased = mode === 'deterministic_onboarding';
        const sourceLabel = isRuleBased ? '📐 Rule-based' : isLLM ? '🤖 AI-gegenereerd' : '';
        const sourceClass = isRuleBased ? 'source-rule' : 'source-ai';

        if (sourceLabel) {
            html += `<span class="chat-source-badge ${sourceClass}">${sourceLabel}</span>`;
        }

        // Narrative tekst
        if (response.narrative) {
            html += `<p class="chat-narrative">${this._escapeHtml(response.narrative)}</p>`;
        }

        // Track E: Disclaimer bij LLM-responses
        if (isLLM) {
            html += `<p class="chat-disclaimer">⚠️ Dit antwoord is AI-gegenereerd. Controleer belangrijke gegevens altijd via de originele bron.</p>`;
        }

        // Actie-knoppen
        if (response.acties && response.acties.length > 0) {
            html += `<div class="chat-acties">`;
            for (const actie of response.acties) {
                html += `<button class="chat-actie-btn" 
                    data-type="${actie.type}" 
                    data-uuid="${actie.indicator_uuid || ''}"
                    data-gemeente-code="${actie.gemeente_code || ''}"
                    data-gebiedstype-id="${actie.gebiedstype_id || ''}"
                    data-config-id="${actie.config_id || ''}"
                    data-filters='${JSON.stringify(actie.filters || {})}'
                    data-thema="${actie.thema || ''}"
                    data-rol-code="${actie.rol_code || ''}"
                    title="${this._escapeHtml(actie.label)}"
                >${actie.label}</button>`;
            }
            html += `</div>`;
        }

        // Gevonden indicatoren (scrollbare lijst)
        if (response.indicatoren && response.indicatoren.length > 0) {
            html += `<div class="chat-indicatoren-lijst">`;
            html += `<span class="chat-indicatoren-label">${response.indicatoren.length} indicatoren gevonden</span>`;
            for (const ind of response.indicatoren) {
                const pct = Math.round(ind.relevantie * 100);
                html += `<div class="chat-indicator-item" data-uuid="${ind.uuid}" title="Klik om op kaart te tonen">
                    <span class="chat-ind-naam">${this._escapeHtml(ind.naam)}</span>
                    <span class="chat-ind-score">${pct}%</span>
                </div>`;
            }
            html += `</div>`;
        }

        html += `</div>`;
        block.innerHTML = html;
        
        // Event listeners voor actie-knoppen
        block.querySelectorAll('.chat-actie-btn').forEach(btn => {
            btn.addEventListener('click', () => this._handleActie(btn));
        });

        // Event listeners voor indicator items
        block.querySelectorAll('.chat-indicator-item').forEach(item => {
            item.addEventListener('click', () => this._handleIndicatorClick(item));
        });

        this.messagesEl.appendChild(block);
        this._scrollToBottom();
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
            const context = { ...this._getKaartContext(), ...extraContext };
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
            this.addAssistantMessage(data);

        } catch (error) {
            console.error('❌ Chat error:', error);
            this.addErrorMessage(error.message || 'Onbekende fout');
        } finally {
            this.isLoading = false;
            this._updateSendButton();
        }
    }

    // ========================================================================
    // Actie Handlers (Command Dispatch → EventBus)
    // ========================================================================

    _handleActie(btn) {
        const type = btn.dataset.type;
        const uuid = btn.dataset.uuid;
        const thema = btn.dataset.thema;

        console.log(`🎯 Chat actie: ${type}`, { 
            uuid, 
            gemeente: btn.dataset.gemeenteCode,
            gebiedstype: btn.dataset.gebiedstypeId,
            config: btn.dataset.configId
        });

        // Visuele feedback: voeg vinkje toe en verander stijl
        const originalText = btn.textContent;
        if (!originalText.startsWith('✅')) {
            btn.textContent = '✅ ' + originalText;
            btn.classList.add('actie-activated');
        }

        switch (type) {
            case 'TOON_OP_KAART':
                if (uuid && window.EventBus) {
                    window.EventBus.emit('INDICATOR_SELECTED', {
                        uuid: uuid,
                        name: originalText.replace(/^[🗺📋📄\s]+/, '').replace('Toon: ', '')
                    });
                }
                break;

            case 'SELECTEER_BUURTEN':
                if (uuid && window.EventBus) {
                    window.EventBus.emit('INDICATOR_SELECTED', {
                        uuid: uuid,
                        name: originalText.replace(/^[🗺📋📄\s]+/, '')
                    });
                }
                break;

            case 'MAAK_RAPPORT': {
                // Gebruik geselecteerde gebieden van de kaart indien beschikbaar
                const geselecteerd = window.state?.selectedGebiedIds
                    ? [...window.state.selectedGebiedIds]
                    : [];

                if (geselecteerd.length === 0) {
                    // Geen selectie: open lege benchmark pagina
                    window.open('/admin/rapport/benchmark', '_blank');
                } else if (geselecteerd.length === 1) {
                    // Eén gebied: open gebiedsdossier
                    window.open(`/admin/rapport/${geselecteerd[0]}`, '_blank');
                } else {
                    // Multi-selectie: open benchmark met alle gebieden
                    const [a, ...rest] = geselecteerd;
                    window.open(
                        `/admin/rapport/benchmark?gebied_a=${a}&gebieden_b=${rest.join(',')}`,
                        '_blank'
                    );
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
                if (window.EventBus) {
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
                window.open('/static/help.html', '_blank');
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
    // Interne Helpers
    // ========================================================================

    _setupEventListeners() {
        // Toggle knop
        this.toggleBtn?.addEventListener('click', () => this.toggle());

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
    }

    _updateSendButton() {
        if (!this.sendBtn) return;
        const hasText = this.inputEl?.value.trim().length > 0;
        this.sendBtn.disabled = !hasText || this.isLoading;
    }

    _getKaartContext() {
        // Haal huidige kaart-staat op als context voor de LLM
        const context = {};
        if (window.state?.selectedGebiedId) {
            context.huidig_gebied_id = window.state.selectedGebiedId;
        }
        if (window.state?.currentIndicator) {
            context.huidige_indicator_uuid = window.state.currentIndicator;
        }
        return context;
    }

    _scrollToBottom() {
        if (this.messagesEl) {
            this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
        }
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
        const existing = btn.parentElement?.querySelector(`.chat-info-card[data-title="${titel}"]`);
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
