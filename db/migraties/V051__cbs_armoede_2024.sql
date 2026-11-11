-- ============================================================
-- Migratie v51: CBS armoede vanaf 2024 (#507)
--
-- Vanaf peiljaar 2024 vervalt 'Huishoudens met laag inkomen' in CBS
-- Kerncijfers wijken en buurten en publiceert CBS in plaats daarvan
-- 'Personen in armoede' (%) en 'Personen tot 25% boven armoedegrens' (%).
--
-- 1. Beide indicatoren toevoegen met polariteit 'lager_is_beter' (trigger
--    trg_indicator_polariteit synchroniseert score_type = '+/-' en
--    interpretatie_logica = '-/+').
-- 2. Koppelen in Volledig Kompas onder Kwaliteit van leven > Rondkomen >
--    Armoede voor bestaande databases.
--
-- Idempotent en veilig op een lege database vóór load_sample.py (#137).
-- ============================================================

DO $$
DECLARE
    v_color_schema_id integer;
    v_config_id integer;
    v_titel_id integer;
    v_thema_id integer;
    v_onderdeel_id integer;
BEGIN
    SELECT id INTO v_color_schema_id
      FROM color_schemas
     WHERE id = 1
     LIMIT 1;
    IF v_color_schema_id IS NULL THEN
        SELECT id INTO v_color_schema_id
          FROM color_schemas
         ORDER BY id
         LIMIT 1;
    END IF;

    -- Op een verse installatie draaien migraties vóór load_sample.py (stuurdata_seed.sql);
    -- dan vult load_sample.py --stap definities daarna color_schemas, indicatoren en Kompas.
    IF v_color_schema_id IS NULL THEN
        RETURN;
    END IF;

    INSERT INTO indicatoren (
        uuid,
        naam,
        code,
        omschrijving,
        eenheid,
        polariteit,
        score_type,
        interpretatie_logica,
        color_schema_id,
        bron,
        status,
        ontologische_beschrijving,
        beschrijving_ai,
        is_actief
    )
    VALUES
    (
        '61b9c64b-9fc9-528c-ab91-fd39597c4080'::uuid,
        'Personen in armoede',
        'CBS_PERSONEN_IN_ARMOEDE',
        'Percentage personen in particuliere huishoudens met een huishoudensinkomen onder de nieuwe armoedegrens ten opzichte van het totaal aantal personen in particuliere huishoudens (CBS Kerncijfers wijken en buurten vanaf 2024, kolom PersonenInArmoede).',
        '%',
        'lager_is_beter',
        '+/-',
        '-/+',
        v_color_schema_id,
        'CBS Kerncijfers wijken en buurten',
        'O',
        'De indicator "Personen in armoede" meet het percentage inwoners in particuliere huishoudens met een besteedbaar inkomen onder de herziene landelijke armoedegrens (CBS/SCP/Nibud), gebaseerd op CBS Kerncijfers wijken en buurten vanaf peiljaar 2024. Gemeenten gebruiken dit cijfer als opvolger van huishoudens met laag inkomen (t/m 2023) om armoede per wijk en buurt te monitoren.',
        'De indicator "Personen in armoede" meet het percentage inwoners in particuliere huishoudens met een inkomen onder de armoedegrens per wijk en buurt (CBS Kerncijfers vanaf 2024).',
        TRUE
    ),
    (
        '66ff2a84-d859-5b72-b308-ef6fce09d820'::uuid,
        'Personen tot 25% boven armoedegrens',
        'CBS_PERSONEN_TOT_25_BOVEN_ARMOEDEGRENS',
        'Percentage personen in particuliere huishoudens met een huishoudensinkomen tussen de armoedegrens en 25% boven de armoedegrens ten opzichte van het totaal aantal personen in particuliere huishoudens (CBS Kerncijfers wijken en buurten vanaf 2024, kolom PersonenTot25BovenArmoedegrens).',
        '%',
        'lager_is_beter',
        '+/-',
        '-/+',
        v_color_schema_id,
        'CBS Kerncijfers wijken en buurten',
        'O',
        'De indicator "Personen tot 25% boven armoedegrens" meet het percentage inwoners in particuliere huishoudens die net boven de armoedegrens leven (inkomen tussen 100% en 125% van de herziene armoedegrens), gebaseerd op CBS Kerncijfers wijken en buurten vanaf peiljaar 2024. Deze groep maakt financiële kwetsbaarheid en het risico op terugval in armoede per buurt zichtbaar.',
        'De indicator "Personen tot 25% boven armoedegrens" meet het percentage inwoners met een inkomen tussen de armoedegrens en 25% daarboven per wijk en buurt (CBS Kerncijfers vanaf 2024).',
        TRUE
    )
    ON CONFLICT (uuid) DO UPDATE SET
        naam = EXCLUDED.naam,
        eenheid = COALESCE(indicatoren.eenheid, EXCLUDED.eenheid),
        polariteit = EXCLUDED.polariteit,
        omschrijving = COALESCE(NULLIF(indicatoren.omschrijving, ''), EXCLUDED.omschrijving),
        ontologische_beschrijving = COALESCE(NULLIF(indicatoren.ontologische_beschrijving, ''), EXCLUDED.ontologische_beschrijving),
        beschrijving_ai = COALESCE(NULLIF(indicatoren.beschrijving_ai, ''), EXCLUDED.beschrijving_ai),
        is_actief = TRUE;

    SELECT id INTO v_config_id
      FROM kompas_configuraties
     WHERE naam = 'Volledig Kompas'
     LIMIT 1;
    IF v_config_id IS NULL THEN
        RETURN;
    END IF;

    SELECT id INTO v_titel_id
      FROM kompas_titels
     WHERE config_id = v_config_id AND naam = 'Kwaliteit van leven'
     LIMIT 1;
    IF v_titel_id IS NULL THEN
        INSERT INTO kompas_titels (config_id, naam)
        VALUES (v_config_id, 'Kwaliteit van leven')
        RETURNING id INTO v_titel_id;
    END IF;

    SELECT id INTO v_thema_id
      FROM kompas_themas
     WHERE titel_id = v_titel_id AND naam = 'Rondkomen'
     LIMIT 1;
    IF v_thema_id IS NULL THEN
        INSERT INTO kompas_themas (titel_id, naam)
        VALUES (v_titel_id, 'Rondkomen')
        RETURNING id INTO v_thema_id;
    END IF;

    SELECT id INTO v_onderdeel_id
      FROM kompas_onderdelen
     WHERE thema_id = v_thema_id AND naam = 'Armoede'
     LIMIT 1;
    IF v_onderdeel_id IS NULL THEN
        INSERT INTO kompas_onderdelen (thema_id, naam)
        VALUES (v_thema_id, 'Armoede')
        RETURNING id INTO v_onderdeel_id;
    END IF;

    INSERT INTO kompas_indicator_mapping (config_id, indicator_uuid, onderdeel_id, is_actueel)
    SELECT v_config_id, i.uuid, v_onderdeel_id, TRUE
      FROM indicatoren i
     WHERE i.uuid IN (
         '61b9c64b-9fc9-528c-ab91-fd39597c4080'::uuid, -- Personen in armoede
         '66ff2a84-d859-5b72-b308-ef6fce09d820'::uuid  -- Personen tot 25% boven armoedegrens
     )
    ON CONFLICT DO NOTHING;
END $$;
