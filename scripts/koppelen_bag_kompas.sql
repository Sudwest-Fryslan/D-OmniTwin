-- Koppelen BAG indicatoren aan Kompas structuur
-- Config ID: 1 (Volledig Kompas)

-- 1. BOUWPERIODE (Onderdeel ID 27)
-- Indicatoren: Voor 1915, 1915-1945, 1945-1984, Vanaf 1985
-- Score type: '+/+' (Neutraal/Informatief, maar technisch 'meer is meer' voor de taartpunt grootte)
-- Weging: 25 (Gelijk verdeeld, puur voor verdeling)

INSERT INTO kompas_indicator_mapping (onderdeel_id, indicator_uuid, weging, is_actueel, config_id)
SELECT 27, uuid, 25, true, 1
FROM indicatoren WHERE code IN ('bag_bouwjaar_voor_1915', 'bag_bouwjaar_1915_1945', 'bag_bouwjaar_1945_1984', 'bag_bouwjaar_vanaf_1985')
ON CONFLICT (onderdeel_id, indicator_uuid) DO UPDATE SET is_actueel = true, config_id = 1;

UPDATE indicatoren SET score_type = '+/+' WHERE code IN ('bag_bouwjaar_voor_1915', 'bag_bouwjaar_1915_1945', 'bag_bouwjaar_1945_1984', 'bag_bouwjaar_vanaf_1985');


-- 2. GEBRUIK OMGEVING (Onderdeel ID 26)
-- Indicatoren: 11 gebruiksfuncties
-- Score type: '+/+' (Meer voorzieningen = vaak beter/levendiger, of gewoon neutraal aantal)
-- Weging: 10 (ongeveer gelijk, totaal > 100 mag, wordt genormaliseerd)

INSERT INTO kompas_indicator_mapping (onderdeel_id, indicator_uuid, weging, is_actueel, config_id)
SELECT 26, uuid, 10, true, 1
FROM indicatoren WHERE code IN (
    'bag_functie_woon', 'bag_functie_bijeenkomst', 'bag_functie_cel', 'bag_functie_gezondheid',
    'bag_functie_industrie', 'bag_functie_kantoor', 'bag_functie_logies', 'bag_functie_onderwijs',
    'bag_functie_sport', 'bag_functie_winkel', 'bag_functie_overige'
)
ON CONFLICT (onderdeel_id, indicator_uuid) DO UPDATE SET is_actueel = true, config_id = 1;

UPDATE indicatoren SET score_type = '+/+' WHERE code IN (
    'bag_functie_woon', 'bag_functie_bijeenkomst', 'bag_functie_cel', 'bag_functie_gezondheid',
    'bag_functie_industrie', 'bag_functie_kantoor', 'bag_functie_logies', 'bag_functie_onderwijs',
    'bag_functie_sport', 'bag_functie_winkel', 'bag_functie_overige'
);
