/**
 * Kleur en duiding van een afwijking ten opzichte van een referentie (#323).
 *
 * De kleur volgt de polariteit van de indicator (indicator_meta.richting uit de
 * API: 'hoger_is_beter' | 'lager_is_beter' | 'neutraal'). Een hogere waarde is
 * dus alleen rood als hoger ongunstig is; neutraal blijft neutraal.
 *
 * Laadt als gewoon script (window.afwijkingDuiding) en als CommonJS-module voor
 * de unittest (tests/test_afwijking_js.py).
 */
(function (root) {
    'use strict';

    /** { kleur: CSS-variabele, oordeel: 'gunstig'|'ongunstig'|'neutraal'|'gelijk' } */
    function afwijkingDuiding(diff, richting) {
        if (!diff) return { kleur: '--text-secondary', oordeel: 'gelijk' };
        if (richting !== 'hoger_is_beter' && richting !== 'lager_is_beter') {
            return { kleur: '--text-secondary', oordeel: 'neutraal' };
        }
        const gunstig = (diff > 0) === (richting === 'hoger_is_beter');
        return gunstig
            ? { kleur: '--color-success', oordeel: 'gunstig' }
            : { kleur: '--color-danger', oordeel: 'ongunstig' };
    }

    root.afwijkingDuiding = afwijkingDuiding;
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { afwijkingDuiding };
    }
})(typeof window !== 'undefined' ? window : globalThis);
