-- ============================================================
-- Migratie v50: Groep 2 laaghangend fruit (#507)
--
-- 1. Indicator 'Arbeidsongeschiktheid (AO)' toevoegen (CBS Kerncijfers,
--    PersonenPerSoortUitkeringAO) met polariteit 'lager_is_beter' (trigger
--    trg_indicator_polariteit houdt score_type = '+/-' en
--    interpretatie_logica = '-/+' gelijk).
-- 2. 'Netto arbeidsparticipatie' (al in cbs-kerncijfers geladen) en
--    'Arbeidsongeschiktheid (AO)' opnemen in Volledig Kompas onder
--    Kwaliteit van leven > Rondkomen > Werk voor bestaande databases.
--
-- Idempotent en veilig op een lege database vóór load_sample.py (#137).
-- ============================================================

INSERT INTO indicatoren (
    uuid,
    naam,
    code,
    omschrijving,
    eenheid,
    polariteit,
    score_type,
    interpretatie_logica,
    bron,
    status,
    ontologische_beschrijving,
    beschrijving_ai,
    is_actief
)
VALUES (
    '8d4c7f51-e8e8-5576-af88-650cee66e899'::uuid,
    'Arbeidsongeschiktheid (AO)',
    'CBS_ARBEIDSONGESCHIKTHEID_AO',
    'Aantal personen dat op de laatste dag van december een arbeidsongeschiktheidsuitkering ontvangt op grond van WAO, WAZ, Wajong of WIA (CBS Kerncijfers wijken en buurten, kolom PersonenPerSoortUitkeringAO). Personen met een uitkering in een instelling zijn meegeteld conform CBS-definitie.',
    'aantal',
    'lager_is_beter',
    '+/-',
    '-/+',
    'CBS Kerncijfers wijken en buurten',
    'O',
    'De indicator "Arbeidsongeschiktheid (AO)" telt het aantal inwoners met een arbeidsongeschiktheidsuitkering (WAO, WAZ, Wajong of WIA) op de peildatum van 31 december per wijk en buurt, gebaseerd op CBS Kerncijfers wijken en buurten. Gemeenten en beleidsteams gebruiken dit cijfer samen met bijstandsuitkeringen en arbeidsparticipatie om uitval op de arbeidsmarkt en zorg-/inkomensondersteuning in buurten in beeld te brengen.',
    'De indicator "Arbeidsongeschiktheid (AO)" telt het aantal inwoners met een arbeidsongeschiktheidsuitkering (WAO, WAZ, Wajong of WIA) op de peildatum van 31 december per wijk en buurt, gebaseerd op CBS Kerncijfers wijken en buurten.',
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

DO $$
DECLARE
    v_config_id integer;
    v_titel_id integer;
    v_thema_id integer;
    v_onderdeel_id integer;
BEGIN
    SELECT id INTO v_config_id
      FROM kompas_configuraties
     WHERE naam = 'Volledig Kompas'
     LIMIT 1;

    -- Op een verse installatie draaien migraties vóór load_sample.py; dan maakt load_sample.py
    -- het profiel daarna aan vanuit db/stuurdata/kompas_hierarchie.csv.
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
     WHERE thema_id = v_thema_id AND naam = 'Werk'
     LIMIT 1;
    IF v_onderdeel_id IS NULL THEN
        INSERT INTO kompas_onderdelen (thema_id, naam)
        VALUES (v_thema_id, 'Werk')
        RETURNING id INTO v_onderdeel_id;
    END IF;

    INSERT INTO kompas_indicator_mapping (config_id, indicator_uuid, onderdeel_id, is_actueel)
    SELECT v_config_id, i.uuid, v_onderdeel_id, TRUE
      FROM indicatoren i
     WHERE i.uuid IN (
         'b07f74eb-5117-4705-802c-597ba830d016'::uuid, -- Netto arbeidsparticipatie
         '8d4c7f51-e8e8-5576-af88-650cee66e899'::uuid  -- Arbeidsongeschiktheid (AO)
     )
    ON CONFLICT DO NOTHING;
END $$;

