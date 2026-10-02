-- Laad-API (#205, stap 3): gebied_data en gebiedstypes klaar voor leveringen. Idempotent.
--
-- gebied_data
--   n               aantal waarnemingen waarop de waarde rust (profiel waarnemingen)
--   n_status        gemeten | bron-onderdrukt (de bron paste de n-drempel zelf toe);
--                   waarden onder de drempel (onderdrukt) komen hier nooit
--   levering_id     de levering die de waarde publiceerde (NULL: geladen buiten de laad-API)
--   De unieke sleutel zonder scenario (unq_gebied_indicator_jaar) vervalt: de sleutel is
--   gebied × indicator × jaar (of datum) × scenario (unique_measurement_jaar/_datum blijven).
--   De verwijzing naar indicatoren wordt RESTRICT: een indicator met waarden verdwijnt niet
--   stil (profiel definities zet hem op eindgeldigheid).
-- gebiedstypes
--   actief, metadata (herkomst van de indeling, bijv. de WFS van de SWF-monitor)

ALTER TABLE public.gebied_data ADD COLUMN IF NOT EXISTS n integer;
ALTER TABLE public.gebied_data ADD COLUMN IF NOT EXISTS n_status text;
ALTER TABLE public.gebied_data ADD COLUMN IF NOT EXISTS levering_id uuid;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'gebied_data_n_status_check'
                   AND conrelid = 'public.gebied_data'::regclass) THEN
        ALTER TABLE public.gebied_data ADD CONSTRAINT gebied_data_n_status_check
            CHECK (n_status IS NULL OR n_status IN ('gemeten', 'bron-onderdrukt'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'gebied_data_n_check'
                   AND conrelid = 'public.gebied_data'::regclass) THEN
        ALTER TABLE public.gebied_data ADD CONSTRAINT gebied_data_n_check CHECK (n IS NULL OR n >= 0);
    END IF;
END
$$;
COMMENT ON COLUMN public.gebied_data.n IS 'Aantal waarnemingen waarop de waarde rust (laad-API, profiel waarnemingen)';
COMMENT ON COLUMN public.gebied_data.n_status IS 'gemeten of bron-onderdrukt (de bron paste de n-drempel zelf toe); NULL = geladen buiten de laad-API';
COMMENT ON COLUMN public.gebied_data.levering_id IS 'Levering (laden.leveringen) die deze waarde publiceerde; NULL = geladen buiten de laad-API';
CREATE INDEX IF NOT EXISTS idx_gebied_data_levering ON public.gebied_data (levering_id) WHERE levering_id IS NOT NULL;

-- Sleutel zonder scenario weg (de sleutels met scenario blijven)
ALTER TABLE public.gebied_data DROP CONSTRAINT IF EXISTS unq_gebied_indicator_jaar;
DROP INDEX IF EXISTS public.unq_gebied_indicator_jaar;

-- Ontbrekende sleutels met scenario (oude installaties) aanvullen
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_measurement_jaar'
                   AND conrelid = 'public.gebied_data'::regclass) THEN
        ALTER TABLE public.gebied_data ADD CONSTRAINT unique_measurement_jaar
            UNIQUE (gebied_id, indicator_uuid, jaar, scenario_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_measurement_datum'
                   AND conrelid = 'public.gebied_data'::regclass) THEN
        ALTER TABLE public.gebied_data ADD CONSTRAINT unique_measurement_datum
            UNIQUE (gebied_id, indicator_uuid, datum, scenario_id);
    END IF;
END
$$;

-- gebied_data → indicatoren: CASCADE wordt RESTRICT
DO $$
DECLARE
    fk record;
BEGIN
    FOR fk IN
        SELECT c.conname FROM pg_constraint c
        WHERE c.conrelid = 'public.gebied_data'::regclass AND c.contype = 'f'
          AND c.confrelid = 'public.indicatoren'::regclass AND c.confdeltype <> 'r'
    LOOP
        EXECUTE format('ALTER TABLE public.gebied_data DROP CONSTRAINT %I', fk.conname);
    END LOOP;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c
                   WHERE c.conrelid = 'public.gebied_data'::regclass AND c.contype = 'f'
                     AND c.confrelid = 'public.indicatoren'::regclass) THEN
        ALTER TABLE public.gebied_data ADD CONSTRAINT gebied_data_indicator_uuid_fkey
            FOREIGN KEY (indicator_uuid) REFERENCES public.indicatoren(uuid) ON DELETE RESTRICT;
    END IF;
END
$$;

-- gebiedstypes
ALTER TABLE public.gebiedstypes ADD COLUMN IF NOT EXISTS actief boolean NOT NULL DEFAULT true;
ALTER TABLE public.gebiedstypes ADD COLUMN IF NOT EXISTS metadata jsonb;
COMMENT ON COLUMN public.gebiedstypes.actief IS 'Gebiedstype in gebruik (profiel definities, swf-monitor: gebiedstypen[].actief)';
COMMENT ON COLUMN public.gebiedstypes.metadata IS 'Herkomst en overige eigenschappen (bijv. wfs, typenames, sleutel, label, code_prefix)';
