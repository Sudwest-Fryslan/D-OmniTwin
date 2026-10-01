import { useEffect, useRef } from 'react';

const FOCUSABLE = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])', 'textarea:not([disabled])', '[tabindex]:not([tabindex="-1"])',
].join(',');

const focusables = (el: HTMLElement) =>
    Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE))
        .filter(e => e.offsetWidth > 0 || e.offsetHeight > 0 || e.getClientRects().length > 0);

/**
 * Focusbeheer voor een modale dialoog (WCAG 2.1, #67): bij openen gaat de focus de
 * dialoog in en blijft daar (Tab/Shift+Tab), Escape roept onClose aan en bij sluiten
 * gaat de focus terug naar het element dat de dialoog opende.
 *
 * Gebruik: const ref = useDialogFocus<HTMLDivElement>(isOpen, onClose);
 *          <div ref={ref} role="dialog" aria-modal="true" aria-labelledby="...">
 */
export function useDialogFocus<T extends HTMLElement>(isOpen: boolean, onClose: () => void) {
    const ref = useRef<T>(null);
    const onCloseRef = useRef(onClose);
    onCloseRef.current = onClose;

    useEffect(() => {
        if (!isOpen) return;
        const dialog = ref.current;
        if (!dialog) return;
        const trigger = document.activeElement as HTMLElement | null;

        if (!dialog.hasAttribute('tabindex')) dialog.setAttribute('tabindex', '-1');
        (focusables(dialog)[0] || dialog).focus();

        const onKeydown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                onCloseRef.current();
                return;
            }
            if (e.key !== 'Tab') return;
            const items = focusables(dialog);
            if (items.length === 0) {
                e.preventDefault();
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
        };
        document.addEventListener('keydown', onKeydown, true);
        return () => {
            document.removeEventListener('keydown', onKeydown, true);
            if (trigger && document.contains(trigger)) trigger.focus();
        };
    }, [isOpen]);

    return ref;
}
