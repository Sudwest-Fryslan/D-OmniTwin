-- ============================================================
-- Migratie v46: één polariteitscodering voor indicatoren (#120)
--
-- "Is hoger beter?" stond op drie manieren in het model, met verschillende
-- uitleg per plek: indicatoren.interpretatie_logica (pos_is_pos, -/+, N/A,
-- neutraal), indicatoren.score_type (+/+, +/-, -/+, -/-, -=-) en de view
-- v_score_types. Rapporten en chat lazen '-/+' als "lager is beter", de kaart,
-- het Kompas en de percentielklassen als "hoger is beter". Dat raakte o.a. de
-- SWF-indicatoren met omkeren (score_type '-/+', #342) en 'Afstand tot koele plek'.
--
-- Nu:
-- - indicatoren.polariteit: de ene codering, codelijst
--     hoger_is_beter | lager_is_beter | neutraal   (check-constraint).
-- - Bestaande waarden omgezet met één regel (gelijk aan omnitwin.polariteit):
--     interpretatie_logica neutraal/N/A           -> neutraal
--     score_type '+/+' (of '+=+')                 -> hoger_is_beter
--     score_type leeg en logica '-/+'             -> lager_is_beter
--     score_type leeg                             -> hoger_is_beter
--     elke andere score_type (+/-, -/+, -/-, -=-) -> lager_is_beter
-- - score_type en interpretatie_logica blijven bestaan als afgeleide kolommen,
--   voor bestaande laders en de API (api.indicatoren): een trigger houdt ze gelijk
--   aan polariteit (score_type '+/+' of '+/-'; logica pos_is_pos, -/+ of neutraal).
--   Wie een oude kolom schrijft (ETL, laad-API), zet daarmee de polariteit.
-- - v_score_types vervalt; de codelijst staat in v_polariteiten.
--
-- Geen schemanaam in deze migratie: tabellen en functies volgen het search_path.
-- Idempotent.
-- ============================================================

CREATE OR REPLACE FUNCTION polariteit_uit_score_type(p_score_type text, p_logica text)
RETURNS text
LANGUAGE sql IMMUTABLE
AS $$
    SELECT CASE
        WHEN lower(btrim(coalesce(p_logica, ''))) IN ('neutraal', 'n/a') THEN 'neutraal'
        WHEN nullif(btrim(coalesce(p_score_type, '')), '') IS NULL THEN
            CASE WHEN btrim(coalesce(p_logica, '')) = '-/+' THEN 'lager_is_beter' ELSE 'hoger_is_beter' END
        WHEN btrim(p_score_type) IN ('+/+', '+=+') THEN 'hoger_is_beter'
        ELSE 'lager_is_beter'
    END;
$$;
COMMENT ON FUNCTION polariteit_uit_score_type(text, text) IS
    'Oude codering (score_type, interpretatie_logica) naar polariteit (#120); gelijk aan omnitwin.polariteit.uit_oud';

ALTER TABLE indicatoren ADD COLUMN IF NOT EXISTS polariteit varchar(20);

UPDATE indicatoren
   SET polariteit = polariteit_uit_score_type(score_type, interpretatie_logica)
 WHERE polariteit IS NULL;

ALTER TABLE indicatoren ALTER COLUMN polariteit SET DEFAULT 'hoger_is_beter';
ALTER TABLE indicatoren ALTER COLUMN polariteit SET NOT NULL;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'indicatoren_polariteit_check') THEN
        ALTER TABLE indicatoren ADD CONSTRAINT indicatoren_polariteit_check
            CHECK (polariteit IN ('hoger_is_beter', 'lager_is_beter', 'neutraal'));
    END IF;
END $$;
COMMENT ON COLUMN indicatoren.polariteit IS
    'Is hoger beter? hoger_is_beter | lager_is_beter | neutraal (#120). score_type en interpretatie_logica volgen deze kolom.';
COMMENT ON COLUMN indicatoren.score_type IS
    'Afgeleid van polariteit (#120): +/+ (hoger is beter of neutraal) of +/- (lager is beter). Schrijven zet de polariteit.';
COMMENT ON COLUMN indicatoren.interpretatie_logica IS
    'Afgeleid van polariteit (#120): pos_is_pos, -/+ of neutraal. Schrijven zet de polariteit.';

-- De oude kolommen gelijk trekken met de polariteit
CREATE OR REPLACE FUNCTION indicator_polariteit_sync()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- De kolomdefault vult polariteit al; alleen expliciet meegegeven telt
        IF NEW.polariteit IS NULL OR NEW.polariteit = 'hoger_is_beter' THEN
            NEW.polariteit := polariteit_uit_score_type(NEW.score_type, NEW.interpretatie_logica);
        END IF;
    ELSIF NEW.polariteit IS DISTINCT FROM OLD.polariteit THEN
        NULL;  -- polariteit zelf gewijzigd: die gaat voor
    ELSIF NEW.score_type IS DISTINCT FROM OLD.score_type
          AND NEW.interpretatie_logica IS NOT DISTINCT FROM OLD.interpretatie_logica THEN
        -- Alleen score_type gewijzigd (bijv. omkeren uit de monitor, #342)
        NEW.polariteit := polariteit_uit_score_type(NEW.score_type, NULL);
    ELSIF NEW.score_type IS DISTINCT FROM OLD.score_type
          OR NEW.interpretatie_logica IS DISTINCT FROM OLD.interpretatie_logica THEN
        NEW.polariteit := polariteit_uit_score_type(NEW.score_type, NEW.interpretatie_logica);
    END IF;

    IF NEW.polariteit IS NULL THEN
        NEW.polariteit := 'hoger_is_beter';
    END IF;
    NEW.score_type := CASE NEW.polariteit WHEN 'lager_is_beter' THEN '+/-' ELSE '+/+' END;
    NEW.interpretatie_logica := CASE NEW.polariteit
        WHEN 'lager_is_beter' THEN '-/+'
        WHEN 'neutraal' THEN 'neutraal'
        ELSE 'pos_is_pos' END;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_indicator_polariteit ON indicatoren;
CREATE TRIGGER trg_indicator_polariteit
    BEFORE INSERT OR UPDATE ON indicatoren
    FOR EACH ROW EXECUTE FUNCTION indicator_polariteit_sync();

-- Bestaande rijen: oude kolommen gelijk trekken (de trigger doet het werk)
UPDATE indicatoren
   SET polariteit = polariteit
 WHERE score_type IS DISTINCT FROM CASE polariteit WHEN 'lager_is_beter' THEN '+/-' ELSE '+/+' END
    OR interpretatie_logica IS DISTINCT FROM CASE polariteit
           WHEN 'lager_is_beter' THEN '-/+' WHEN 'neutraal' THEN 'neutraal' ELSE 'pos_is_pos' END;

-- De codelijst (vervangt v_score_types)
DROP VIEW IF EXISTS v_score_types;
CREATE OR REPLACE VIEW v_polariteiten AS
    SELECT 'hoger_is_beter'::text AS code, 'Hoger is beter'::text AS naam,
           'Een hoge waarde is gunstig'::text AS beschrijving,
           'Inkomen, arbeidsparticipatie'::text AS voorbeelden
    UNION ALL
    SELECT 'lager_is_beter', 'Lager is beter',
           'Een lage waarde is gunstig',
           'Afstand tot koele plek, eenzaamheid, inbraken'
    UNION ALL
    SELECT 'neutraal', 'Neutraal',
           'Geen oordeel: de waarde beschrijft alleen',
           'Leeftijdsopbouw, huishoudsamenstelling';
COMMENT ON VIEW v_polariteiten IS 'Codelijst polariteit van indicatoren (#120)';
