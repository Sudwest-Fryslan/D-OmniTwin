import { describe, expect, it } from 'vitest';
import { provincieNaam } from './useBenchmarkProvincie';

// #324: de referentie 'provincie' volgt de instelling, geen vaste provincie
describe('provincieNaam', () => {
    it('noemt de ingestelde provincie', () => {
        expect(provincieNaam('Fryslân')).toBe('Provincie Fryslân');
        expect(provincieNaam('Groningen')).toBe('Provincie Groningen');
    });

    it('zonder instelling: alle gebieden', () => {
        expect(provincieNaam(null)).toBe('alle gebieden');
        expect(provincieNaam(undefined)).toBe('alle gebieden');
    });
});
