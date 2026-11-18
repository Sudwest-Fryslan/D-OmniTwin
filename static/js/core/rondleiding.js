/**
 * Interactieve Spotlight Rondleiding (#442, WCAG 2.1 AA).
 *
 * Lichtgewicht Vanilla-JS rondleiding in 4 stappen langs:
 * 1. De kaart & gebiedsselectie
 * 2. Indicator & legenda
 * 3. Het D-Omni Kompas & detailpaneel
 * 4. Rapport (Gebiedsfactsheet) & D-Omni Assistent
 *
 * Elke stap biedt drie vaste duidingsregels:
 * - Wat zie je
 * - Wat betekent het
 * - Probeer het
 *
 * Publiceert:
 * - window.RONDLEIDING_STAPPEN
 * - window.startRondleiding(triggerEl)
 * - window.stopRondleiding()
 */
(function () {
    'use strict';

    /**
     * Stappendefinitie als data.
     * Let op: ankers uitsluitend als '#id' of '[data-panel="x"]' (getoetst door tests/test_rondleiding.py).
     */
    const RONDLEIDING_STAPPEN = [
        {
            id: 'kaart',
            titel: '1. De kaart & gebiedsselectie',
            ankers: ['#hoofdinhoud'],
            wat: 'Elke vlek op de kaart is een gebied (zoals een buurt); de kleur volgt de gekozen indicator en grijs betekent geen data.',
            betekent: 'De kleur laat zien hoe een buurt scoort ten opzichte van andere gebieden.',
            probeer: 'Beweeg over buurten voor de exacte waarde of klik op een buurt om die te selecteren. Met Shift+klik selecteer je meerdere buurten (de vergelijking zie je onderaan in het Kompas-paneel).',
        },
        {
            id: 'legenda',
            titel: '2. Indicator & legenda',
            ankers: ['#panel-legenda', '[data-panel="controls"]'],
            wat: 'De legenda toont de kleurenschaal en gebiedsdekking van de actieve indicator.',
            betekent: 'Kies zelf tussen werkelijke waarde, percentielklasse 1–8 of label A–E. Een hoge waarde is niet altijd gunstig — kijk altijd naar de legenda.',
            probeer: 'Wissel de weergave in de legenda, of kies een andere gemeente of indicator via Kaartconfiguratie (tweede icoon links).',
        },
        {
            id: 'kompas',
            titel: '3. Het D-Omni Kompas',
            ankers: ['#rechter-dock'],
            wat: 'Het Kompas bundelt alle thema\'s in ringen. Eronder zie je direct de tijdreeks, definitie, bron, vergelijking met het gemeentegemiddelde en top-uitschieters.',
            betekent: 'De kleuren van rood (via oranje/geel) naar groen laten zien of een thema of indicator negatief of positief scoort. Blauw (Samenstelling) is puur beschrijvend zonder goed of slecht; grijs betekent geen data.',
            probeer: 'Klik op een segment in het wiel om in te zoomen op een thema, of scroll in dit paneel naar beneden voor de cijfers en de vergelijking tussen buurten.',
        },
        {
            id: 'rapport-assistent',
            titel: '4. Rapport & D-Omni Assistent',
            ankers: ['[data-panel="rapport"]', '#chat-toggle-btn'],
            wat: 'De knoppen voor Rapport (met bovenaan de Gebiedsfactsheet) en de D-Omni Assistent.',
            betekent: 'De Gebiedsfactsheet vat een buurt feitelijk samen per thema (zonder AI). De Assistent haalt antwoorden uit de beheerde data; schrijft een taalmodel de samenvatting, dan staat er een AI-label bij — controleer altijd de bron.',
            probeer: 'Open Rapport voor de geselecteerde buurt, of stel een vraag in gewone taal aan de Assistent.',
        },
    ];

    let huidigeStapIndex = 0;
    let overlayEl = null;
    let cutoutEl = null;
    let popoverEl = null;
    let dialogHandle = null;
    let startTriggerEl = null;
    let voorbeeldGebiedId = null;
    let voorbeeldGebiedNaam = null;
    let oorspronkelijkePanelId = null;

    function isZichtbaar(el) {
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && getComputedStyle(el).visibility !== 'hidden';
    }

    function kiesVoorbeeldBuurt() {
        const st = window.state;
        if (!st) return;

        // Gebruiker heeft zelf al een selectie: gebruik die en raak niets aan bij afsluiten
        if (st.selectedGebiedIds && st.selectedGebiedIds.size > 0) {
            voorbeeldGebiedId = null;
            const namen = typeof window.getSelectedGebiedNamen === 'function' ? window.getSelectedGebiedNamen() : [];
            voorbeeldGebiedNaam = namen[0] || [...st.selectedGebiedIds][0] || null;
            return;
        }

        const features = st.currentData?.features;
        if (!Array.isArray(features) || features.length === 0) {
            voorbeeldGebiedId = null;
            voorbeeldGebiedNaam = null;
            return;
        }

        // Sorteer deterministisch op naam en kies de eerste buurt met een geldige waarde (geen waterbuurt)
        const gesorteerd = [...features]
            .filter(f => f && f.properties && f.properties.id && f.properties.water !== 'JA')
            .sort((a, b) => String(a.properties.naam || a.properties.id).localeCompare(
                String(b.properties.naam || b.properties.id),
                'nl'
            ));

        const gekozen = gesorteerd.find(
            f => f.properties.value !== null && f.properties.value !== undefined && !Number.isNaN(Number(f.properties.value))
        ) || gesorteerd[0];

        if (!gekozen) return;

        voorbeeldGebiedId = String(gekozen.properties.id);
        voorbeeldGebiedNaam = String(gekozen.properties.naam || voorbeeldGebiedId);

        if (window.EventBus) {
            window.EventBus.emit('CHAT_GEBIEDEN_TONEN', {
                ids: [voorbeeldGebiedId],
                zoom: true,
            });
        }
        if (typeof window.loadKompasForSelection === 'function' && window.kompasViz?.currentConfigId) {
            window.loadKompasForSelection(window.kompasViz.currentConfigId);
        }
    }

    function herstelVoorbeeldBuurt() {
        const st = window.state;
        if (voorbeeldGebiedId && st?.selectedGebiedIds) {
            // Alleen wissen als de voorbeeldbuurt nog steeds de enige selectie is
            if (st.selectedGebiedIds.size === 1 && st.selectedGebiedIds.has(voorbeeldGebiedId)) {
                if (typeof window.clearGebiedSelection === 'function') {
                    window.clearGebiedSelection();
                } else {
                    st.selectedGebiedIds.clear();
                }
                if (typeof window.updateSelectionUI === 'function') window.updateSelectionUI();
                if (typeof window.updateButtonState === 'function') window.updateButtonState();
                if (st.currentData && typeof window.displayOnMap === 'function') {
                    window.displayOnMap(st.currentData);
                }
            }
        }
        voorbeeldGebiedId = null;
        voorbeeldGebiedNaam = null;
    }

    function bouwOverlayDom() {
        if (overlayEl && document.body.contains(overlayEl)) return;

        overlayEl = document.createElement('div');
        overlayEl.id = 'spotlight-tour-overlay';
        overlayEl.className = 'spotlight-tour-overlay';

        cutoutEl = document.createElement('div');
        cutoutEl.id = 'spotlight-cutout';
        cutoutEl.className = 'spotlight-cutout';
        cutoutEl.setAttribute('aria-hidden', 'true');

        popoverEl = document.createElement('div');
        popoverEl.id = 'spotlight-popover';
        popoverEl.className = 'spotlight-popover';
        popoverEl.setAttribute('role', 'dialog');
        popoverEl.setAttribute('aria-modal', 'false');
        popoverEl.setAttribute('aria-labelledby', 'spotlight-step-title');

        const header = document.createElement('div');
        header.className = 'spotlight-header';

        const stapBadge = document.createElement('span');
        stapBadge.id = 'spotlight-step-counter';
        stapBadge.className = 'spotlight-step-counter';

        const sluitKnop = document.createElement('button');
        sluitKnop.type = 'button';
        sluitKnop.id = 'spotlight-close-btn';
        sluitKnop.className = 'spotlight-close-btn';
        sluitKnop.setAttribute('aria-label', 'Rondleiding sluiten');
        sluitKnop.title = 'Rondleiding sluiten (Escape)';
        sluitKnop.textContent = '✕';
        sluitKnop.addEventListener('click', () => stopRondleiding());

        header.append(stapBadge, sluitKnop);

        const titel = document.createElement('h3');
        titel.id = 'spotlight-step-title';
        titel.className = 'spotlight-title';
        titel.setAttribute('aria-live', 'polite');

        const inhoud = document.createElement('div');
        inhoud.id = 'spotlight-step-body';
        inhoud.className = 'spotlight-body';

        const maakRegel = (id, labelTekst) => {
            const rij = document.createElement('div');
            rij.className = 'spotlight-row';
            const label = document.createElement('strong');
            label.className = 'spotlight-row-label';
            label.textContent = labelTekst;
            const tekst = document.createElement('p');
            tekst.id = id;
            tekst.className = 'spotlight-row-text';
            rij.append(label, tekst);
            return rij;
        };

        inhoud.append(
            maakRegel('spotlight-wat', 'Wat zie je'),
            maakRegel('spotlight-betekent', 'Wat betekent het'),
            maakRegel('spotlight-probeer', 'Probeer het')
        );

        const footer = document.createElement('div');
        footer.className = 'spotlight-footer';

        const overslaanKnop = document.createElement('button');
        overslaanKnop.type = 'button';
        overslaanKnop.id = 'spotlight-skip-btn';
        overslaanKnop.className = 'spotlight-btn spotlight-btn-ghost';
        overslaanKnop.textContent = 'Overslaan';
        overslaanKnop.addEventListener('click', () => stopRondleiding());

        const navGroep = document.createElement('div');
        navGroep.className = 'spotlight-nav-group';

        const vorigeKnop = document.createElement('button');
        vorigeKnop.type = 'button';
        vorigeKnop.id = 'spotlight-prev-btn';
        vorigeKnop.className = 'spotlight-btn spotlight-btn-secondary';
        vorigeKnop.textContent = 'Vorige';
        vorigeKnop.addEventListener('click', () => gaNaarStap(huidigeStapIndex - 1));

        const volgendeKnop = document.createElement('button');
        volgendeKnop.type = 'button';
        volgendeKnop.id = 'spotlight-next-btn';
        volgendeKnop.className = 'spotlight-btn spotlight-btn-primary';
        volgendeKnop.textContent = 'Volgende';
        volgendeKnop.addEventListener('click', () => {
            if (huidigeStapIndex < RONDLEIDING_STAPPEN.length - 1) {
                gaNaarStap(huidigeStapIndex + 1);
            } else {
                stopRondleiding();
            }
        });

        navGroep.append(vorigeKnop, volgendeKnop);
        footer.append(overslaanKnop, navGroep);

        popoverEl.append(header, titel, inhoud, footer);
        overlayEl.append(cutoutEl, popoverEl);
        document.body.appendChild(overlayEl);
    }

    function berekenCutoutRect(stap) {
        const vw = window.innerWidth;
        const vh = window.innerHeight;

        if (stap.id === 'kaart') {
            const hoofd = document.querySelector('#hoofdinhoud');
            const basis = hoofd ? hoofd.getBoundingClientRect() : { left: 70, top: 64, right: vw - 20, bottom: vh - 40 };
            let left = Math.max(basis.left + 72, 72);
            let right = Math.min(basis.right - 16, vw - 16);
            const top = Math.max(basis.top + 12, 68);
            const bottom = Math.min(basis.bottom - 36, vh - 36);

            const panelContainer = document.querySelector('.panel-container.open');
            if (panelContainer && isZichtbaar(panelContainer)) {
                const pr = panelContainer.getBoundingClientRect();
                if (pr.right < vw * 0.6) left = Math.max(left, pr.right + 12);
            }
            const dock = document.querySelector('#rechter-dock:not(.collapsed)');
            if (dock && isZichtbaar(dock) && vw > 900) {
                const dr = dock.getBoundingClientRect();
                if (dr.left > vw * 0.4) right = Math.min(right, dr.left - 12);
            }
            if (right - left < 160) {
                left = Math.max(72, Math.round(vw * 0.2));
                right = Math.min(vw - 16, Math.round(vw * 0.8));
            }
            return {
                left,
                top,
                width: Math.max(120, right - left),
                height: Math.max(120, bottom - top),
            };
        }

        const rects = [];
        for (const sel of stap.ankers) {
            const el = document.querySelector(sel);
            if (el && isZichtbaar(el)) {
                rects.push(el.getBoundingClientRect());
            }
        }

        if (rects.length === 0) {
            return {
                left: Math.round(vw * 0.25),
                top: Math.round(vh * 0.2),
                width: Math.round(vw * 0.5),
                height: Math.round(vh * 0.5),
            };
        }

        const pad = 6;
        const minLeft = Math.max(4, Math.min(...rects.map(r => r.left)) - pad);
        const minTop = Math.max(4, Math.min(...rects.map(r => r.top)) - pad);
        const maxRight = Math.min(vw - 4, Math.max(...rects.map(r => r.right)) + pad);
        const maxBottom = Math.min(vh - 4, Math.max(...rects.map(r => r.bottom)) + pad);

        return {
            left: Math.round(minLeft),
            top: Math.round(minTop),
            width: Math.max(40, Math.round(maxRight - minLeft)),
            height: Math.max(40, Math.round(maxBottom - minTop)),
        };
    }

    function positioneerStap() {
        if (!window.tourActief || !cutoutEl || !popoverEl) return;
        const stap = RONDLEIDING_STAPPEN[huidigeStapIndex];
        if (!stap) return;

        const reduceMotion = window.A11y && typeof window.A11y.prefersReducedMotion === 'function'
            ? window.A11y.prefersReducedMotion()
            : false;
        cutoutEl.classList.toggle('no-motion', reduceMotion);
        popoverEl.classList.toggle('no-motion', reduceMotion);

        const rect = berekenCutoutRect(stap);
        cutoutEl.style.left = `${rect.left}px`;
        cutoutEl.style.top = `${rect.top}px`;
        cutoutEl.style.width = `${rect.width}px`;
        cutoutEl.style.height = `${rect.height}px`;

        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const popRect = popoverEl.getBoundingClientRect();
        const popW = popRect.width || Math.min(380, vw - 24);
        const popH = popRect.height || 260;
        const marge = 14;

        let popLeft = marge;
        let popTop = marge;

        // Mobiel (< 900px): plaats het kaartje bovenin of onderin waar de meeste ruimte is
        if (vw <= 900) {
            popLeft = Math.max(12, Math.round((vw - popW) / 2));
            const ruimteBoven = rect.top;
            const ruimteOnder = vh - (rect.top + rect.height);
            if (ruimteBoven >= ruimteOnder) {
                popTop = Math.max(12, Math.min(rect.top - popH - 12, vh - popH - 12));
            } else {
                popTop = Math.max(12, Math.min(rect.top + rect.height + 12, vh - popH - 12));
            }
        } else if (stap.id === 'kaart') {
            // Op de kaart: gecentreerd onderin het kaartvlak
            popLeft = Math.round(rect.left + (rect.width - popW) / 2);
            popTop = Math.min(vh - popH - 28, Math.max(rect.top + 20, rect.top + rect.height - popH - 16));
        } else {
            const ruimteRechts = vw - (rect.left + rect.width);
            const ruimteLinks = rect.left;
            if (ruimteRechts >= popW + marge * 2) {
                popLeft = rect.left + rect.width + marge;
                popTop = Math.min(vh - popH - marge, Math.max(72, rect.top));
            } else if (ruimteLinks >= popW + marge * 2) {
                popLeft = rect.left - popW - marge;
                popTop = Math.min(vh - popH - marge, Math.max(72, rect.top));
            } else {
                popLeft = Math.round((vw - popW) / 2);
                popTop = Math.round((vh - popH) / 2);
            }
        }

        popLeft = Math.max(12, Math.min(popLeft, vw - popW - 12));
        popTop = Math.max(12, Math.min(popTop, vh - popH - 12));

        popoverEl.style.left = `${Math.round(popLeft)}px`;
        popoverEl.style.top = `${Math.round(popTop)}px`;
    }

    function voorbereidStap(stap) {
        if (stap.id === 'legenda') {
            // Zorg dat het Legenda-paneel zichtbaar is zonder onnodig te sluiten als het al open staat
            if (window.state && window.state.activePanelId !== 'legenda' && typeof window.togglePanel === 'function') {
                window.togglePanel('legenda');
            }
        } else if (stap.id === 'kompas') {
            if (typeof window.openRechterDock === 'function') {
                window.openRechterDock('kompas', false, false);
            }
        }
    }

    function gaNaarStap(index) {
        if (index < 0 || index >= RONDLEIDING_STAPPEN.length) return;
        huidigeStapIndex = index;
        const stap = RONDLEIDING_STAPPEN[index];

        voorbereidStap(stap);

        const counterEl = document.getElementById('spotlight-step-counter');
        const titleEl = document.getElementById('spotlight-step-title');
        const watEl = document.getElementById('spotlight-wat');
        const betekentEl = document.getElementById('spotlight-betekent');
        const probeerEl = document.getElementById('spotlight-probeer');
        const prevBtn = document.getElementById('spotlight-prev-btn');
        const nextBtn = document.getElementById('spotlight-next-btn');

        if (counterEl) counterEl.textContent = `Stap ${index + 1} van ${RONDLEIDING_STAPPEN.length}`;
        if (titleEl) titleEl.textContent = stap.titel;
        if (watEl) watEl.textContent = stap.wat;

        if (betekentEl) {
            let betekentTekst = stap.betekent;
            if (stap.id === 'kaart' && voorbeeldGebiedNaam) {
                betekentTekst += ` Voorbeeld: "${voorbeeldGebiedNaam}" is voor je geselecteerd.`;
            }
            betekentEl.textContent = betekentTekst;
        }
        if (probeerEl) probeerEl.textContent = stap.probeer;

        if (prevBtn) {
            prevBtn.disabled = index === 0;
        }
        if (nextBtn) {
            nextBtn.textContent = index === RONDLEIDING_STAPPEN.length - 1 ? 'Klaar' : 'Volgende';
        }

        positioneerStap();
        // Herbereken na eventuele layout/dock-transitie
        setTimeout(() => positioneerStap(), 320);
    }

    function onDocumentKeydownCapture(e) {
        if (!window.tourActief) return;

        if (e.key === 'Escape') {
            // Voorkom dat de globale Escape-listener in app.js de actieve indicator wist!
            e.preventDefault();
            e.stopPropagation();
            stopRondleiding();
            return;
        }

        const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target?.isContentEditable) {
            return;
        }

        if (e.key === 'ArrowRight') {
            if (huidigeStapIndex < RONDLEIDING_STAPPEN.length - 1) {
                e.preventDefault();
                gaNaarStap(huidigeStapIndex + 1);
            }
        } else if (e.key === 'ArrowLeft') {
            if (huidigeStapIndex > 0) {
                e.preventDefault();
                gaNaarStap(huidigeStapIndex - 1);
            }
        }
    }

    function onResizeOfTransition() {
        if (window.tourActief) {
            positioneerStap();
        }
    }

    async function startRondleiding(triggerEl) {
        const kandidaatTrigger = (triggerEl instanceof HTMLElement)
            ? triggerEl
            : (document.activeElement instanceof HTMLElement ? document.activeElement : document.getElementById('tour-start-btn'));

        // Sluit de welkomstmodal indien nog open
        const welcomeOverlay = document.getElementById('welcome-modal-overlay');
        if (welcomeOverlay && welcomeOverlay.style.display !== 'none' && typeof window.dismissWelcomeModal === 'function') {
            window.dismissWelcomeModal();
        }

        // Wacht tot de startkaart geladen is als de tour vroeg vanuit de welkomstmodal wordt gestart
        if (window.startKaartKlaar && typeof window.startKaartKlaar.then === 'function') {
            try {
                await window.startKaartKlaar;
            } catch (_) {
                // Ga door ook als de startkaart een fout gaf
            }
        }

        startTriggerEl = kandidaatTrigger;
        oorspronkelijkePanelId = window.state?.activePanelId || null;

        window.tourActief = true;
        if (typeof window.hideContextualTooltip === 'function') {
            window.hideContextualTooltip();
        }

        const tourBtn = document.getElementById('tour-start-btn');
        if (tourBtn) {
            tourBtn.classList.add('active');
            tourBtn.setAttribute('aria-expanded', 'true');
        }

        kiesVoorbeeldBuurt();
        bouwOverlayDom();

        overlayEl.style.display = 'block';

        window.addEventListener('keydown', onDocumentKeydownCapture, true);
        window.addEventListener('resize', onResizeOfTransition);
        document.getElementById('rechter-dock')?.addEventListener('transitionend', onResizeOfTransition);
        document.querySelector('.panel-container')?.addEventListener('transitionend', onResizeOfTransition);

        gaNaarStap(0);

        const nextBtn = document.getElementById('spotlight-next-btn');
        if (window.A11y && typeof window.A11y.openDialog === 'function') {
            dialogHandle = window.A11y.openDialog(popoverEl, {
                modal: false,
                labelledBy: 'spotlight-step-title',
                initialFocus: nextBtn || popoverEl,
                returnFocus: startTriggerEl,
                onEscape: () => stopRondleiding(),
            });
        } else if (nextBtn) {
            nextBtn.focus();
        }
    }

    function stopRondleiding() {
        if (!window.tourActief && (!overlayEl || overlayEl.style.display === 'none')) return;

        window.tourActief = false;

        window.removeEventListener('keydown', onDocumentKeydownCapture, true);
        window.removeEventListener('resize', onResizeOfTransition);
        document.getElementById('rechter-dock')?.removeEventListener('transitionend', onResizeOfTransition);
        document.querySelector('.panel-container')?.removeEventListener('transitionend', onResizeOfTransition);

        const tourBtn = document.getElementById('tour-start-btn');
        if (tourBtn) {
            tourBtn.classList.remove('active');
            tourBtn.setAttribute('aria-expanded', 'false');
        }

        if (overlayEl) {
            overlayEl.style.display = 'none';
        }

        herstelVoorbeeldBuurt();

        // Herstel oorspronkelijke linkerpaneel-stand als de tour het had gewijzigd
        if (oorspronkelijkePanelId && window.state && window.state.activePanelId !== oorspronkelijkePanelId && typeof window.togglePanel === 'function') {
            window.togglePanel(oorspronkelijkePanelId);
        }

        if (dialogHandle) {
            const h = dialogHandle;
            dialogHandle = null;
            h.close();
        }

        if (startTriggerEl && startTriggerEl !== document.body && document.contains(startTriggerEl) && typeof startTriggerEl.focus === 'function') {
            startTriggerEl.focus();
        }
        startTriggerEl = null;
    }

    window.RONDLEIDING_STAPPEN = RONDLEIDING_STAPPEN;
    window.startRondleiding = startRondleiding;
    window.stopRondleiding = stopRondleiding;
})();
