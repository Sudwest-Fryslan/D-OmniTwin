-- =============================================
-- DB indicatoren NIET in Kompas
-- =============================================
\echo '=== DB INDICATOREN NIET IN KOMPAS ==='
SELECT i.naam
FROM indicatoren i
WHERE NOT EXISTS (
    SELECT 1 FROM kompas_indicator_mapping m WHERE m.indicator_uuid = i.uuid
)
ORDER BY i.naam;

-- =============================================
-- Kompas CSV namen die NIET matchen in DB
-- (via de kompas_indicator_mapping: niet_gevonden tellen we via query)
-- =============================================
\echo ''
\echo '=== KOMPAS STATISTIEKEN ==='
SELECT
    COUNT(DISTINCT i.uuid) as indicatoren_gekoppeld,
    (SELECT COUNT(*) FROM indicatoren) - COUNT(DISTINCT i.uuid) as indicatoren_niet_gekoppeld
FROM indicatoren i
JOIN kompas_indicator_mapping m ON m.indicator_uuid = i.uuid;

-- =============================================
-- CBS: unieke indicator_namen in gebied_data die NIET in indicatoren zitten
-- (we kunnen dit niet direct queryen want de namen staan alleen in de CSV)
-- Maar we kunnen WEL zien welke indicator_uuids data hebben
-- =============================================
\echo ''
\echo '=== INDICATOREN MET DATA (gebied_data) ==='
SELECT i.naam, COUNT(DISTINCT gd.gebied_id) as buurten, COUNT(*) as metingen
FROM indicatoren i
JOIN gebied_data gd ON gd.indicator_uuid = i.uuid
GROUP BY i.naam
ORDER BY metingen DESC;

\echo ''
\echo '=== INDICATOREN ZONDER DATA ==='
SELECT i.naam
FROM indicatoren i
WHERE NOT EXISTS (
    SELECT 1 FROM gebied_data gd WHERE gd.indicator_uuid = i.uuid
)
ORDER BY i.naam;
