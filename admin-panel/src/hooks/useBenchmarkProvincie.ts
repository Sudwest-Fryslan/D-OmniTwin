import { useEffect, useState } from 'react';
import { organisatieAPI } from '../services/api';

/**
 * Naam van de referentie 'provincie' (#324) voor knoppen en uitleg: de instelling
 * benchmark_provincie van de organisatie, of "alle gebieden" zonder instelling.
 * Het label met het aantal gebieden komt na het laden uit de data (referentie_label).
 */
export function provincieNaam(provincie: string | null | undefined): string {
    return provincie ? `Provincie ${provincie}` : 'alle gebieden';
}

/** benchmark_provincie uit GET /api/organisatie; null zolang onbekend of niet ingesteld. */
export function useBenchmarkProvincie(): string | null {
    const [provincie, setProvincie] = useState<string | null>(null);
    useEffect(() => {
        let actief = true;
        organisatieAPI.get()
            .then(res => { if (actief) setProvincie(res.data?.benchmark_provincie ?? null); })
            .catch(() => { if (actief) setProvincie(null); });
        return () => { actief = false; };
    }, []);
    return provincie;
}
