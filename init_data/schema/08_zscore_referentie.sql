-- ============================================================
-- Z-scores: één bron voor de referentiestatistiek (#66)
--
-- Alle Z-scores (rapporten, benchmark, Kompas) gebruiken deze functies.
-- Methodiek en afwijkingen t.o.v. de oude code: docs/3-data-engineering/zscore_methodiek.md
--
-- Parameters (met standaardwaarden):
--   p_gebiedstype_id   gebiedstype van de referentiegroep (verplicht)
--   p_gemeente_code    gemeente van de referentiegroep; NULL = alle gemeenten
--   p_jaarlogica       'zelfde_jaar' (standaard, zoals het executive-rapport en
--                        Kompas top-buurten werkten): de referentie bestaat uit de
--                        waarden in hetzelfde jaar als de meest recente waarde van
--                        het doelgebied. Zonder doelgebied: het meest recente jaar
--                        van de indicator in de referentiegroep.
--                      'recentst_per_gebied': per gebied de meest recente waarde,
--                        ongeacht het jaar (zoals multi-gebied, thema-analyse,
--                        deelgebied en benchmark werkten)
--                      'alle_jaren': hulpwaarde, alle jaren (één rij per gebied en jaar)
--   p_scenario_id      'current' (standaard); NULL in gebied_data telt als 'current'
--   p_indicator_uuids  NULL = alle indicatoren
--
-- Waterbuurten (gebieden.metadata->>'water' = 'JA') zitten nooit in de
-- referentiegroep. Metingen zonder jaar (alleen datum) tellen niet mee.
--
-- ⚠️ WAARSCHUWING (zie de methodiek voor details):
--   - Vóór #66 zaten waterbuurten wél in de referentie van executive,
--     multi-gebied, thema-analyse, benchmark en Kompas; uitkomsten verschuiven
--     waar waterbuurten waarden hebben.
--   - Vóór #66 telden scenario-projecties (scenario_id <> 'current') mee.
--   - Wijken die als CBS-buurt zijn opgeslagen (ETL/import_geografie_2024.py)
--     vallen in de referentiegroep; hier wordt niet op naam gefilterd.
--   - gebieden.actief speelt geen rol; vw_gebied_kaart_basis gebruikt een
--     ruimere definitie van water (ook op naam).
--
-- Idempotent: alleen CREATE OR REPLACE. Bestaande database bijwerken:
--   psql -f migrations/schema_v21_zscore_referentie.sql
-- ============================================================

-- Referentieset: per gebied en indicator één waarde (bij 'alle_jaren': één per jaar)
CREATE OR REPLACE FUNCTION public.zscore_referentie_waarden(
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'zelfde_jaar',
    p_scenario_id     varchar DEFAULT 'current',
    p_indicator_uuids uuid[]  DEFAULT NULL
)
RETURNS TABLE (gebied_id varchar, indicator_uuid uuid, waarde numeric, jaar integer)
LANGUAGE plpgsql STABLE
AS $$
#variable_conflict use_column
BEGIN
    IF p_jaarlogica NOT IN ('zelfde_jaar', 'recentst_per_gebied', 'alle_jaren') THEN
        RAISE EXCEPTION 'Onbekende jaarlogica: % (verwacht zelfde_jaar of recentst_per_gebied)', p_jaarlogica;
    END IF;

    RETURN QUERY
    WITH kandidaten AS (
        -- De referentiegroep: gebiedstype (+ gemeente), zonder waterbuurten
        SELECT gd.gebied_id AS k_gebied, gd.indicator_uuid AS k_ind, gd.waarde AS k_waarde, gd.jaar AS k_jaar
        FROM public.gebied_data gd
        JOIN public.gebieden g ON g.id = gd.gebied_id
        WHERE g.gebiedstype_id = p_gebiedstype_id
          AND (p_gemeente_code IS NULL OR g.gemeente_code = p_gemeente_code)
          AND COALESCE(g.metadata->>'water', 'NEE') != 'JA'
          AND COALESCE(gd.scenario_id, 'current') = p_scenario_id
          AND gd.jaar IS NOT NULL
          AND (p_indicator_uuids IS NULL OR gd.indicator_uuid = ANY(p_indicator_uuids))
    ),
    gemarkeerd AS (
        SELECT k.*,
               ROW_NUMBER() OVER (PARTITION BY k.k_gebied, k.k_ind ORDER BY k.k_jaar DESC) AS rn_gebied,
               MAX(k.k_jaar) OVER (PARTITION BY k.k_ind) AS peiljaar
        FROM kandidaten k
    )
    SELECT m.k_gebied, m.k_ind, m.k_waarde, m.k_jaar
    FROM gemarkeerd m
    WHERE p_jaarlogica = 'alle_jaren'
       OR (p_jaarlogica = 'recentst_per_gebied' AND m.rn_gebied = 1)
       OR (p_jaarlogica = 'zelfde_jaar' AND m.k_jaar = m.peiljaar);
END;
$$;

COMMENT ON FUNCTION public.zscore_referentie_waarden(uuid, varchar, text, varchar, uuid[]) IS
    'Referentieset voor Z-scores; waterbuurten en scenario-projecties uitgesloten (#66). Zie docs/3-data-engineering/zscore_methodiek.md';


-- Referentiestatistiek per indicator: gemiddelde, standaarddeviatie (steekproef) en n.
-- Zonder doelgebied; bij 'zelfde_jaar' dus het meest recente jaar van de indicator.
CREATE OR REPLACE FUNCTION public.zscore_referentie_stats(
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'zelfde_jaar',
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
-- ⚠️ Vóór #66 gaf het executive-rapport hier 0 en sloten de andere rapporten de indicator uit.
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
-- p_gebied_ids NULL = de gebieden van de referentieset zelf (zoals Kompas top-buurten).
-- Het doelgebied gebruikt zijn meest recente waarde (scenario p_scenario_id).
-- Bij 'zelfde_jaar' is de referentie het jaar van die waarde, per indicator.
-- Indicatoren zonder referentiewaarden komen niet terug; z_score is NULL bij n < 2 of sd = 0.
-- ⚠️ Het doelgebied zelf wordt niet op waterbuurt gefilterd; dat doen de rapporten.
CREATE OR REPLACE FUNCTION public.zscore_gebieden(
    p_gebied_ids      varchar[],
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'zelfde_jaar',
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
    WITH ref AS (
        -- 'zelfde_jaar': alle jaren, statistiek per (indicator, jaar);
        -- 'recentst_per_gebied': één waarde per gebied, statistiek per indicator
        SELECT rw.gebied_id AS r_gebied, rw.indicator_uuid AS r_ind, rw.waarde AS r_waarde,
               CASE WHEN p_jaarlogica = 'zelfde_jaar' THEN rw.jaar END AS r_sleuteljaar
        FROM public.zscore_referentie_waarden(
            p_gebiedstype_id, p_gemeente_code,
            CASE WHEN p_jaarlogica = 'zelfde_jaar' THEN 'alle_jaren' ELSE p_jaarlogica END,
            p_scenario_id, p_indicator_uuids
        ) rw
    ),
    stats AS (
        SELECT r_ind, r_sleuteljaar,
               AVG(r_waarde) AS s_gem, STDDEV_SAMP(r_waarde) AS s_sd, COUNT(*)::integer AS s_n,
               MIN(r_waarde) AS s_min, MAX(r_waarde) AS s_max
        FROM ref
        GROUP BY r_ind, r_sleuteljaar
    ),
    doel AS (
        -- Gebieden uit de referentieset zelf
        SELECT rw.gebied_id AS d_gebied, rw.indicator_uuid AS d_ind, rw.waarde AS d_waarde, rw.jaar AS d_jaar
        FROM public.zscore_referentie_waarden(
            p_gebiedstype_id, p_gemeente_code, p_jaarlogica, p_scenario_id, p_indicator_uuids
        ) rw
        WHERE p_gebied_ids IS NULL
        UNION ALL
        -- Opgegeven gebieden (mogen buiten de referentiegroep liggen): meest recente waarde
        (
            SELECT DISTINCT ON (gd.gebied_id, gd.indicator_uuid)
                   gd.gebied_id, gd.indicator_uuid, gd.waarde, gd.jaar
            FROM public.gebied_data gd
            WHERE p_gebied_ids IS NOT NULL
              AND gd.gebied_id = ANY(p_gebied_ids)
              AND COALESCE(gd.scenario_id, 'current') = p_scenario_id
              AND gd.jaar IS NOT NULL
              AND (p_indicator_uuids IS NULL OR gd.indicator_uuid = ANY(p_indicator_uuids))
            ORDER BY gd.gebied_id, gd.indicator_uuid, gd.jaar DESC
        )
    )
    SELECT d.d_gebied, d.d_ind, d.d_waarde, d.d_jaar,
           s.s_gem, s.s_sd, s.s_n, s.s_min, s.s_max,
           public.zscore(d.d_waarde, s.s_gem, s.s_sd, s.s_n)
    FROM doel d
    JOIN stats s ON s.r_ind = d.d_ind
                AND s.r_sleuteljaar IS NOT DISTINCT FROM
                    (CASE WHEN p_jaarlogica = 'zelfde_jaar' THEN d.d_jaar END);
$$;

COMMENT ON FUNCTION public.zscore_gebieden(varchar[], uuid, varchar, text, varchar, uuid[]) IS
    'Z-scores per gebied en indicator t.o.v. de referentiegroep; standaard zelfde jaar als het doelgebied (#66)';
