-- Koppel nieuwe indicatoren aan Kompas structuur
-- Doel: Inzicht in technische kwaliteit woningvoorraad
-- Locatie: Kwaliteit fysieke leefomgeving (1) -> Wonen (3) -> Technische kwaliteit (9)

-- 1. Definieer variabelen voor leesbaarheid (in commentaar)
-- Titel ID = 1
-- Thema ID = 3
-- Onderdeel ID = 9

-- 2. Voeg toe aan kompas_indicator_mapping
-- Noot: weging is indicatief, totaal per onderdeel moet idealiter 100 zijn of wordt genormaliseerd

-- 2a. Aantal Energielabels Definitief (Meer = Beter inzicht)
INSERT INTO kompas_indicator_mapping (onderdeel_id, indicator_uuid, weging, is_actueel, config_id)
SELECT 9, uuid, 10, true, 1
FROM indicatoren WHERE code = 'aantal_energielabels_definitief'
ON CONFLICT (onderdeel_id, indicator_uuid) DO UPDATE SET is_actueel = true, config_id = 1;

UPDATE indicatoren SET score_type = '+/+' WHERE code = 'aantal_energielabels_definitief';

-- 2b. Energielabel Coverage (Hoger % = Beter inzicht)
INSERT INTO kompas_indicator_mapping (onderdeel_id, indicator_uuid, weging, is_actueel, config_id)
SELECT 9, uuid, 10, true, 1
FROM indicatoren WHERE code = 'pct_energielabel_coverage'
ON CONFLICT (onderdeel_id, indicator_uuid) DO UPDATE SET is_actueel = true, config_id = 1;

UPDATE indicatoren SET score_type = '+/+' WHERE code = 'pct_energielabel_coverage';

-- 2c. Gemiddeld Bouwjaar (Nieuwer = Beter qua techniek)
INSERT INTO kompas_indicator_mapping (onderdeel_id, indicator_uuid, weging, is_actueel, config_id)
SELECT 9, uuid, 20, true, 1
FROM indicatoren WHERE code = 'gemiddeld_bouwjaar'
ON CONFLICT (onderdeel_id, indicator_uuid) DO UPDATE SET is_actueel = true, config_id = 1;

UPDATE indicatoren SET score_type = '+/+' WHERE code = 'gemiddeld_bouwjaar';

-- 2d. Percentage vooroorylogs (Hoger % = Slechter/Aandachtspunt)
INSERT INTO kompas_indicator_mapping (onderdeel_id, indicator_uuid, weging, is_actueel, config_id)
SELECT 9, uuid, 20, true, 1
FROM indicatoren WHERE code = 'pct_voor_1945'
ON CONFLICT (onderdeel_id, indicator_uuid) DO UPDATE SET is_actueel = true, config_id = 1;

UPDATE indicatoren SET score_type = '-/-' WHERE code = 'pct_voor_1945';

-- 3. Update Scoring Regels (Optioneel, voor kleurtoekenning)
-- Voor coverage: 0% = Slecht (Rood), 100% = Goed (Groen). Dit gaat via 'thresholds' JSON kolom.
-- We proberen eerst een default insert in kompas_indicator_scoring_regels als die nog niet bestaat.

INSERT INTO kompas_indicator_scoring_regels (indicator_uuid, config_id, score_type, thresholds, eenheid, created_at, updated_at)
SELECT 
    uuid, 
    1, 
    'threshold_based', 
    '[{"min": 0, "max": 20, "label": "Zeer laag", "color": "#FF0000"}, {"min": 20, "max": 50, "label": "Laag", "color": "#FFA500"}, {"min": 50, "max": 80, "label": "Redelijk", "color": "#FFFF00"}, {"min": 80, "max": 95, "label": "Goed", "color": "#90EE90"}, {"min": 95, "max": 100, "label": "Uitstekend", "color": "#008000"}]'::jsonb,
    '%',
    NOW(),
    NOW()
FROM indicatoren WHERE code = 'pct_energielabel_coverage'
ON CONFLICT (indicator_uuid, config_id) DO UPDATE 
SET thresholds = EXCLUDED.thresholds, score_type = 'threshold_based';

-- Voor Aantal Definitief: 0 = Slecht, 500+ = Goed (Afhankelijk van buurtgrootte, lastig absoluut te maken)
-- We laten deze even zonder expliciete regels (default linear scaling indien supported)

