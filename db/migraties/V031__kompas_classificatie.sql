-- Classificatie per kompasprofiel (#255). Idempotent.
--
-- kompas_configuraties.classificatie bepaalt hoe het Kompas indicatoren en hun
-- onderdelen, thema's en kwadranten kleurt:
--   zscore        de huidige weergave (standaard)
--   percentiel_8  percentielklasse 1-8 (12,5%) binnen de referentiegroep, met
--                 gewogen klasse-aggregatie; zie
--                 docs/3-data-engineering/percentielklasse_methodiek.md
-- Instellen is data: UPDATE kompas_configuraties SET classificatie = 'percentiel_8' WHERE ...
ALTER TABLE public.kompas_configuraties
    ADD COLUMN IF NOT EXISTS classificatie text NOT NULL DEFAULT 'zscore';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'kompas_configuraties_classificatie_check'
                   AND conrelid = 'public.kompas_configuraties'::regclass) THEN
        ALTER TABLE public.kompas_configuraties ADD CONSTRAINT kompas_configuraties_classificatie_check
            CHECK (classificatie IN ('zscore', 'percentiel_8'));
    END IF;
END
$$;

COMMENT ON COLUMN public.kompas_configuraties.classificatie IS
    'Kleuring van het Kompas: zscore (standaard) of percentiel_8 (8 klassen van 12,5%, #255)';
