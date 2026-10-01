/**
 * Toegankelijkheidshulpen (WCAG 2.1, #67)
 *
 * - A11y.openDialog(): focusbeheer voor dialogen. Focus gaat de dialoog in, blijft
 *   er bij een modale dialoog in (Tab/Shift+Tab), Escape sluit, en bij sluiten gaat
 *   de focus terug naar het element dat de dialoog opende.
 * - A11y.prefersReducedMotion() / motionDuration() / cameraTransition(): animaties
 *   in JS (deck.gl-camera, D3) volgen de systeeminstelling "minder beweging".
 *
 * Geen afhankelijkheden; publiceert window.A11y.
 */
(function () {
    'use strict';

    const FOCUSABLE = [
        'a[href]', 'area[href]', 'button:not([disabled])', 'input:not([disabled]):not([type="hidden"])',
        'select:not([disabled])', 'textarea:not([disabled])', 'iframe',
        '[tabindex]:not([tabindex="-1"])', '[contenteditable="true"]'
    ].join(',');

    const motionQuery = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;

    // Open dialogen; de bovenste krijgt Escape en Tab
    const stack = [];

    function prefersReducedMotion() {
        return !!(motionQuery && motionQuery.matches);
    }

    /** Duur van een animatie in ms; 0 bij "minder beweging". */
    function motionDuration(ms) {
        return prefersReducedMotion() ? 0 : ms;
    }

    /**
     * Overgangsvelden voor een deck.gl-viewState. Bij "minder beweging" springt de
     * camera direct (duur 0, geen FlyToInterpolator).
     * @param {number} ms       duur zonder reduced motion
     * @param {boolean} flyTo   FlyToInterpolator gebruiken
     */
    function cameraTransition(ms, flyTo = false) {
        if (prefersReducedMotion()) {
            return { transitionDuration: 0, transitionInterpolator: undefined };
        }
        const t = { transitionDuration: ms };
        if (flyTo && typeof deck !== 'undefined' && deck.FlyToInterpolator) {
            t.transitionInterpolator = new deck.FlyToInterpolator();
        }
        return t;
    }

    function isVisible(el) {
        return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
            && getComputedStyle(el).visibility !== 'hidden';
    }

    function focusables(container) {
        return [...container.querySelectorAll(FOCUSABLE)].filter(isVisible);
    }

    /**
     * Maak van een element een (modale) dialoog met focusbeheer.
     *
     * @param {HTMLElement} dialog  het dialoogvenster (krijgt role="dialog")
     * @param {object} [opts]
     * @param {boolean} [opts.modal=true]      focus vasthouden en aria-modal="true"
     * @param {string}  [opts.labelledBy]      id van de titel (aria-labelledby)
     * @param {HTMLElement} [opts.initialFocus] element dat als eerste focus krijgt
     * @param {HTMLElement} [opts.returnFocus]  element voor focus bij sluiten (standaard: het actieve element bij openen)
     * @param {Function} [opts.onEscape]       aangeroepen bij Escape; moet zelf handle.close() aanroepen
     *                                         (standaard: handle.close())
     * @returns {{close: Function, dialog: HTMLElement}} handle; close() ruimt op en zet de focus terug
     */
    function openDialog(dialog, opts = {}) {
        const modal = opts.modal !== false;
        const trigger = opts.returnFocus || document.activeElement;

        dialog.setAttribute('role', 'dialog');
        dialog.setAttribute('aria-modal', modal ? 'true' : 'false');
        if (opts.labelledBy) dialog.setAttribute('aria-labelledby', opts.labelledBy);
        if (!dialog.hasAttribute('tabindex')) dialog.setAttribute('tabindex', '-1');

        const handle = { dialog, closed: false };

        function onKeydown(e) {
            if (handle.closed || stack[stack.length - 1] !== handle) return;
            // Niet-modaal: alleen toetsen binnen het venster; een widget in het venster
            // die Escape zelf afhandelt (preventDefault) gaat voor
            if (!modal && !dialog.contains(e.target)) return;
            if (e.key === 'Escape') {
                if (e.defaultPrevented) return;
                e.preventDefault();
                e.stopPropagation();
                if (opts.onEscape) opts.onEscape(); else handle.close();
                return;
            }
            if (e.key !== 'Tab' || !modal) return;
            const items = focusables(dialog);
            if (items.length === 0) {
                e.preventDefault();
                dialog.focus();
                return;
            }
            const first = items[0];
            const last = items[items.length - 1];
            const active = document.activeElement;
            if (!dialog.contains(active)) {
                e.preventDefault();
                (e.shiftKey ? last : first).focus();
            } else if (e.shiftKey && (active === first || active === dialog)) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && active === last) {
                e.preventDefault();
                first.focus();
            }
        }

        // Modaal: capture op document (vóór andere Escape-handlers); niet-modaal: op het venster
        const target = modal ? document : dialog;
        target.addEventListener('keydown', onKeydown, modal);

        handle.close = function () {
            if (handle.closed) return;
            handle.closed = true;
            target.removeEventListener('keydown', onKeydown, modal);
            const i = stack.indexOf(handle);
            if (i >= 0) stack.splice(i, 1);
            // Focus alleen terugzetten als die nog in de dialoog stond (of nergens)
            const active = document.activeElement;
            const focusInDialog = !active || active === document.body || dialog.contains(active);
            if (focusInDialog && trigger && trigger !== document.body && document.contains(trigger)
                && typeof trigger.focus === 'function') {
                trigger.focus();
            }
        };

        stack.push(handle);

        const first = opts.initialFocus || (modal ? focusables(dialog)[0] : null) || dialog;
        // Na de huidige taak: het element kan net zichtbaar gemaakt zijn
        requestAnimationFrame(() => {
            if (!handle.closed) first.focus();
        });

        return handle;
    }

    window.A11y = { prefersReducedMotion, motionDuration, cameraTransition, openDialog, focusables };
})();
