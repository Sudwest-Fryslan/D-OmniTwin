-- ============================================================
-- Z-scores: één bron voor de referentiestatistiek (#66)
--
-- Alle Z-scores (rapporten, benchmark, Kompas) gebruiken deze functies.
-- Methodiek: docs/3-data-engineering/zscore_methodiek.md
--
-- Parameters (met standaardwaarden):
--   p_gebiedstype_id   gebiedstype van de referentiegroep (verplicht)
--   p_gemeente_code    gemeente van de referentiegroep; NULL = alle gemeenten
--   p_jaarlogica       'recentst_per_gebied' (standaard): per gebied en indicator
--                        de meest recente waarde, ongeacht het jaar
--                      'recentst_jaar_indicator': per indicator alleen het meest
--                        recente jaar in de referentiegroep
--   p_scenario_id      'current' (standaard); NULL in gebied_data telt als 'current'
--   p_indicator_uuids  NULL = alle indicatoren
--
-- Waterbuurten (gebieden.metadata->>'water' = 'JA') zitten nooit in de
-- referentiegroep. Metingen zonder jaar (alleen datum) tellen niet mee.
--
-- Idempotent: alleen CREATE OR REPLACE. Bestaande database bijwerken:
--   psql -f migrations/schema_v20_zscore_referentie.sql
-- ============================================================

-- Referentieset: per gebied en indicator één waarde
CREATE OR REPLACE FUNCTION public.zscore_referentie_waarden(
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'recentst_per_gebied',
    p_scenario_id     varchar DEFAULT 'current',
    p_indicator_uuids uuid[]  DEFAULT NULL
)
RETURNS TABLE (gebied_id varchar, indicator_uuid uuid, waarde numeric, jaar integer)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    IF p_jaarlogica = 'recentst_per_gebied' THEN
        RETURN QUERY
        SELECT DISTINCT ON (gd.gebied_id, gd.indicator_uuid)
               gd.gebied_id, gd.indicator_uuid, gd.waarde, gd.jaar
        FROM public.gebied_data gd
        JOIN public.gebieden g ON g.id = gd.gebied_id
        WHERE g.gebiedstype_id = p_gebiedstype_id
          AND (p_gemeente_code IS NULL OR g.gemeente_code = p_gemeente_code)
          AND COALESCE(g.metadata->>'water', 'NEE') != 'JA'
          AND COALESCE(gd.scenario_id, 'current') = p_scenario_id
          AND gd.jaar IS NOT NULL
          AND (p_indicator_uuids IS NULL OR gd.indicator_uuid = ANY(p_indicator_uuids))
        ORDER BY gd.gebied_id, gd.indicator_uuid, gd.jaar DESC;

    ELSIF p_jaarlogica = 'recentst_jaar_indicator' THEN
        RETURN QUERY
        WITH kandidaten AS (
            SELECT gd.gebied_id, gd.indicator_uuid, gd.waarde, gd.jaar,
                   MAX(gd.jaar) OVER (PARTITION BY gd.indicator_uuid) AS peiljaar
            FROM public.gebied_data gd
            JOIN public.gebieden g ON g.id = gd.gebied_id
            WHERE g.gebiedstype_id = p_gebiedstype_id
              AND (p_gemeente_code IS NULL OR g.gemeente_code = p_gemeente_code)
              AND COALESCE(g.metadata->>'water', 'NEE') != 'JA'
              AND COALESCE(gd.scenario_id, 'current') = p_scenario_id
              AND gd.jaar IS NOT NULL
              AND (p_indicator_uuids IS NULL OR gd.indicator_uuid = ANY(p_indicator_uuids))
        )
        SELECT k.gebied_id, k.indicator_uuid, k.waarde, k.jaar
        FROM kandidaten k
        WHERE k.jaar = k.peiljaar;

    ELSE
        RAISE EXCEPTION 'Onbekende jaarlogica: % (verwacht recentst_per_gebied of recentst_jaar_indicator)', p_jaarlogica;
    END IF;
END;
$$;

COMMENT ON FUNCTION public.zscore_referentie_waarden(uuid, varchar, text, varchar, uuid[]) IS
    'Referentieset voor Z-scores: per gebied en indicator één waarde; waterbuurten uitgesloten (#66)';


-- Referentiestatistiek per indicator: gemiddelde, standaarddeviatie (steekproef) en n
CREATE OR REPLACE FUNCTION public.zscore_referentie_stats(
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'recentst_per_gebied',
    p_scenario_id     varchar DEFAULT 'current',
    p_indicator_uuids uuid[]  DEFAULT NULL
)
RETURNS TABLE (
    indicator_uuid    uuid,
    gemiddelde        numeric,
    standaarddeviatie numeric,
    n                 integer,
    min_waarde        numeric,
    max_waarde        numeric,
    min_jaar          integer,
    max_jaar          integer
)
LANGUAGE sql STABLE
AS $$
    SELECT rw.indicator_uuid,
           AVG(rw.waarde),
           STDDEV_SAMP(rw.waarde),
           COUNT(*)::integer,
           MIN(rw.waarde),
           MAX(rw.waarde),
           MIN(rw.jaar),
           MAX(rw.jaar)
    FROM public.zscore_referentie_waarden(
        p_gebiedstype_id, p_gemeente_code, p_jaarlogica, p_scenario_id, p_indicator_uuids
    ) rw
    GROUP BY rw.indicator_uuid;
$$;

COMMENT ON FUNCTION public.zscore_referentie_stats(uuid, varchar, text, varchar, uuid[]) IS
    'Gemiddelde, standaarddeviatie (STDDEV_SAMP) en n per indicator van de Z-score-referentiegroep (#66)';


-- De Z-scoreformule. NULL als er geen spreiding is (n < 2 of sd = 0 of NULL).
CREATE OR REPLACE FUNCTION public.zscore(
    p_waarde            numeric,
    p_gemiddelde        numeric,
    p_standaarddeviatie numeric,
    p_n                 integer
)
RETURNS numeric
LANGUAGE sql IMMUTABLE
AS $$
    SELECT CASE
        WHEN p_waarde IS NULL OR p_gemiddelde IS NULL THEN NULL
        WHEN p_n IS NULL OR p_n < 2 THEN NULL
        WHEN p_standaarddeviatie IS NULL OR p_standaarddeviatie <= 0 THEN NULL
        ELSE (p_waarde - p_gemiddelde) / p_standaarddeviatie
    END;
$$;

COMMENT ON FUNCTION public.zscore(numeric, numeric, numeric, integer) IS
    'Z = (waarde - gemiddelde) / standaarddeviatie; NULL bij n < 2 of sd = 0 (#66)';


-- Z-scores voor gebieden ten opzichte van een referentiegroep.
-- p_gebied_ids NULL = alle gebieden van de referentiegroep zelf.
-- Het doelgebied krijgt dezelfde jaarlogica als de referentie: bij
-- 'recentst_per_gebied' zijn meest recente waarde, bij 'recentst_jaar_indicator'
-- zijn waarde in het peiljaar van de referentie.
-- Indicatoren zonder referentiewaarden komen niet terug; z_score is NULL bij
-- n < 2 of sd = 0.
CREATE OR REPLACE FUNCTION public.zscore_gebieden(
    p_gebied_ids      varchar[],
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'recentst_per_gebied',
    p_scenario_id     varchar DEFAULT 'current',
    p_indicator_uuids uuid[]  DEFAULT NULL
)
RETURNS TABLE (
    gebied_id         varchar,
    indicator_uuid    uuid,
    waarde            numeric,
    jaar              integer,
    gemiddelde        numeric,
    standaarddeviatie numeric,
    n                 integer,
    min_waarde        numeric,
    max_waarde        numeric,
    z_score           numeric
)
LANGUAGE sql STABLE
AS $$
    WITH stats AS (
        SELECT * FROM public.zscore_referentie_stats(
            p_gebiedstype_id, p_gemeente_code, p_jaarlogica, p_scenario_id, p_indicator_uuids
        )
    ),
    doel AS (
        -- Gebieden uit de referentiegroep zelf
        SELECT rw.gebied_id, rw.indicator_uuid, rw.waarde, rw.jaar
        FROM public.zscore_referentie_waarden(
            p_gebiedstype_id, p_gemeente_code, p_jaarlogica, p_scenario_id, p_indicator_uuids
        ) rw
        WHERE p_gebied_ids IS NULL
        UNION ALL
        -- Opgegeven gebieden (mogen buiten de referentiegroep liggen)
        (
            SELECT DISTINCT ON (gd.gebied_id, gd.indicator_uuid)
                   gd.gebied_id, gd.indicator_uuid, gd.waarde, gd.jaar
            FROM public.gebied_data gd
            JOIN stats s ON s.indicator_uuid = gd.indicator_uuid
            WHERE p_gebied_ids IS NOT NULL
              AND gd.gebied_id = ANY(p_gebied_ids)
              AND COALESCE(gd.scenario_id, 'current') = p_scenario_id
              AND gd.jaar IS NOT NULL
              AND (p_jaarlogica <> 'recentst_jaar_indicator' OR gd.jaar = s.max_jaar)
            ORDER BY gd.gebied_id, gd.indicator_uuid, gd.jaar DESC
        )
    )
    SELECT d.gebied_id, d.indicator_uuid, d.waarde, d.jaar,
           s.gemiddelde, s.standaarddeviatie, s.n, s.min_waarde, s.max_waarde,
           public.zscore(d.waarde, s.gemiddelde, s.standaarddeviatie, s.n)
    FROM doel d
    JOIN stats s ON s.indicator_uuid = d.indicator_uuid;
$$;

COMMENT ON FUNCTION public.zscore_gebieden(varchar[], uuid, varchar, text, varchar, uuid[]) IS
    'Z-scores per gebied en indicator t.o.v. de referentiegroep van zscore_referentie_stats (#66)';
