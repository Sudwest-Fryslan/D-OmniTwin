-- D-OmniTwin: Indicator namen migratie
-- Uitvoeren via: psql -h localhost -U omnitwin_user -d omnitwin_db -f tmp_migrate_indicatoren.sql

BEGIN;

-- 1. Rename 'hoog' → 'Opleidingsniveau hoog'
UPDATE indicatoren
SET naam = 'Opleidingsniveau hoog',
    code = 'CBS_OPLEIDINGSNIVEAUHOOG',
    eenheid = '%',
    bron = 'CBS Kerncijfers wijken en buurten',
    score_type = '+/+',
    updated_at = CURRENT_TIMESTAMP
WHERE naam = 'hoog';

-- 2. Rename 'laag' → 'Opleidingsniveau laag'
UPDATE indicatoren
SET naam = 'Opleidingsniveau laag',
    code = 'CBS_OPLEIDINGSNIVEAULAAG',
    eenheid = '%',
    bron = 'CBS Kerncijfers wijken en buurten',
    score_type = '+/-',
    updated_at = CURRENT_TIMESTAMP
WHERE naam = 'laag';

-- 3. Rename 'middelhoog' → 'Opleidingsniveau middelbaar'
UPDATE indicatoren
SET naam = 'Opleidingsniveau middelbaar',
    code = 'CBS_OPLEIDINGSNIVEAUMIDDELBAAR',
    eenheid = '%',
    bron = 'CBS Kerncijfers wijken en buurten',
    score_type = '+/+',
    updated_at = CURRENT_TIMESTAMP
WHERE naam = 'middelhoog';

-- 4. Fix 'In bezit overige verhuurders' alias: was verkeerd gelinkt aan Woningcorporatie bezit
--    (geen DB-wijziging nodig — fix zit in seed_fryslan.py alias-tabel)

-- 5. Fix 'Overmatige drinker' alias: was verkeerd gelinkt aan 'Roken'
--    (geen DB-wijziging nodig — fix zit in seed_fryslan.py alias-tabel)

-- 6. Woningvoorraad toevoegen als nieuwe indicator
INSERT INTO indicatoren (uuid, naam, code, eenheid, omschrijving, bron, score_type, status)
VALUES (
    gen_random_uuid(),
    'Woningvoorraad',
    'CBS_WONINGVOORRAAD',
    'aantal',
    'Totaal aantal woningen in de buurt (CBS Kerncijfers)',
    'CBS Kerncijfers wijken en buurten',
    '+/+',
    'O'
)
ON CONFLICT (code) DO UPDATE SET
    naam = EXCLUDED.naam,
    eenheid = EXCLUDED.eenheid,
    bron = EXCLUDED.bron,
    updated_at = CURRENT_TIMESTAMP;

COMMIT;

-- Verificatie
SELECT naam, code, eenheid, bron, score_type
FROM indicatoren
WHERE naam IN (
    'Opleidingsniveau hoog',
    'Opleidingsniveau laag',
    'Opleidingsniveau middelbaar',
    'Woningvoorraad'
)
ORDER BY naam;

SELECT COUNT(*) as totaal_indicatoren FROM indicatoren;
