CREATE TABLE IF NOT EXISTS chat_scenarios (
    id SERIAL PRIMARY KEY,
    rol_code VARCHAR(50) UNIQUE NOT NULL,
    rol_naam VARCHAR(100) NOT NULL,
    beschrijving TEXT,
    narrative TEXT NOT NULL,
    acties JSONB DEFAULT '[]'::jsonb,
    trigger_keywords JSONB DEFAULT '[]'::jsonb,
    is_actief BOOLEAN DEFAULT true,
    volgorde INTEGER DEFAULT 0
);

INSERT INTO chat_scenarios (rol_code, rol_naam, beschrijving, narrative, acties, trigger_keywords, volgorde)
VALUES
(
    'beleidsadviseur',
    'Beleidsadviseur',
    'Beleid & RO voor gemeenten',
    'Je hebt gekozen voor het perspectief van Beleidsadviseur. Voor deze demonstratie kijken we naar de IJsselmeerkust (Súdwest-Fryslân). Ik heb de relevante data voor je klaargezet. Wat wil je als eerste doen?',
    '[
        {"type": "SELECTEER_GEBIEDSTYPE", "label": "🗺️ Toon: Buurten", "gebiedstype_id": "buurt"},
        {"type": "SELECTEER_GEMEENTE", "label": "📍 Gemeente: Súdwest-Fryslân", "gemeente_code": "1900"},
        {"type": "OPEN_KOMPAS", "label": "🧭 Open het D-Omni Kompas"}
    ]',
    '["beleidsadviseur", "ijsselmeerkust", "makkum", "workum"]',
    10
),
(
    'wijkcontactfunctionaris',
    'Dorp/Wijk contactfunctionaris',
    'Lokale initiatieven en wijkzaken',
    'Je hebt gekozen voor het perspectief van Dorp/Wijk contactfunctionaris. (Dit scenario wordt binnenkort verder ingevuld, je kunt de applicatie ondertussen vrij gebruiken).',
    '[]',
    '["wijkcontactfunctionaris", "dorpsbelang", "wijkagent"]',
    20
)
ON CONFLICT (rol_code) DO UPDATE
SET rol_naam = EXCLUDED.rol_naam,
    beschrijving = EXCLUDED.beschrijving,
    narrative = EXCLUDED.narrative,
    acties = EXCLUDED.acties,
    trigger_keywords = EXCLUDED.trigger_keywords,
    volgorde = EXCLUDED.volgorde;
