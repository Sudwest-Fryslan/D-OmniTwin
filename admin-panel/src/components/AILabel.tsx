// Label "AI" bij een AI-resultaat (#312): wat het is, dat het onjuist of onvolledig kan zijn, de bronnen,
// "Meer informatie" (verklaring van de usecase, PDF, #307) en "Melden" (services/melden.ts).
import React, { useEffect, useState } from 'react';
import { organisatieAPI } from '../services/api';
import { heeftMeldkanaal, meld, meldUrl } from '../services/melden';
import type { AIUsecaseCodeMelding, Melding } from '../services/melden';

const TEKST: Record<AIUsecaseCodeMelding, string> = {
    A: 'Dit antwoord is gemaakt met een taalmodel (AI-assistent).',
    B: 'Deze samenvatting is gemaakt met een taalmodel.',
    C: 'Deze zoekresultaten zijn mede gevonden op betekenis, met een AI-model.',
};

// Eén keer per sessie de meldplek van deze instantie ophalen
let meldplek: Promise<string | null> | null = null;
const haalMeldplek = () => {
    meldplek ??= organisatieAPI.get().then(r => r.data.meld_url ?? null).catch(() => null);
    return meldplek;
};

export interface AILabelProps {
    usecase: AIUsecaseCodeMelding;
    vraag?: string;
    resultaat?: string;
    bronnen?: string[];
    pagina?: string;
}

export const AILabel: React.FC<AILabelProps> = ({ usecase, vraag, resultaat, bronnen, pagina }) => {
    const [plek, setPlek] = useState<string | null>(null);
    useEffect(() => { let actief = true; haalMeldplek().then(p => { if (actief) setPlek(p); }); return () => { actief = false; }; }, []);
    const melding: Melding = { onderwerp: 'ai', usecase, vraag, resultaat, bronnen, pagina };

    return (
        <div role="note" aria-label={`AI-resultaat, usecase ${usecase}`} data-testid={`ai-label-${usecase}`}
            style={{
                fontSize: '0.85rem', lineHeight: 1.45, marginTop: '1rem', padding: '0.6rem 0.75rem',
                borderLeft: '3px solid var(--color-primary)', background: 'var(--color-surface-light)',
                color: 'var(--color-text-secondary)', borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
            }}>
            <p style={{ margin: 0, display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                <span aria-hidden="true" className="badge" style={{ border: '1px solid var(--color-primary)', color: 'var(--color-text-primary)', fontWeight: 700 }}>AI</span>
                <span>{TEKST[usecase]} Het kan onjuist of onvolledig zijn; controleer belangrijke gegevens via de bron.</span>
            </p>
            {bronnen && bronnen.length > 0 && <p style={{ margin: '0.3rem 0 0' }}>Bronnen: {bronnen.slice(0, 8).join(', ')}</p>}
            <p style={{ margin: '0.35rem 0 0', display: 'flex', gap: '1rem' }}>
                <a href={`/api/ai/usecases/${usecase}/verklaring`} target="_blank" rel="noopener noreferrer"
                    aria-label={`Meer informatie: verklaring van AI-usecase ${usecase} (PDF, opent in een nieuw venster)`}>
                    Meer informatie
                </a>
                <a href={meldUrl(melding, plek)} target="_blank" rel="noopener noreferrer"
                    aria-label={`Melden: dit AI-resultaat (usecase ${usecase}) klopt niet of iets werkt niet (opent in een nieuw venster)`}
                    onClick={e => { if (heeftMeldkanaal()) { e.preventDefault(); meld(melding); } }}>
                    Melden
                </a>
            </p>
        </div>
    );
};

export default AILabel;
