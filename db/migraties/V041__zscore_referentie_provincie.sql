-- ============================================================
-- Migratie v41: referentiegroep per provincie (#324)
--
-- De Z-score-referentiefuncties krijgen een laatste, optionele parameter
-- p_provincie (provincienaam zoals in gemeenten.provincie). NULL = alle
-- provincies, zoals voorheen. Zo volgt de referentie 'provincie' in de rapporten
-- de instelling organisatie.benchmark_provincie in plaats van alle gebieden in
-- de database.
--
-- Zelfde definitie als db/schema/08_zscore_referentie.sql (via V021), met alleen
-- dat filter erbij; 08 blijft ongewijzigd (checksum van V021, zie db/README.md).
-- Idempotent: DROP FUNCTION IF EXISTS van de oude signatuur, CREATE OR REPLACE.
-- ============================================================

-- ── Referentieset ────────────────────────────────────────────────────────────
-- Per gebied en indicator één waarde (bij 'alle_jaren': één per jaar).
-- referentie_terugval = true: bij 'zelfde_jaar' hadden minder dan p_min_n gebieden
-- een waarde in het peiljaar; de set is dan 'recentst_per_gebied'.
DROP FUNCTION IF EXISTS public.zscore_referentie_waarden(uuid, varchar, text, varchar, uuid[], integer);
CREATE OR REPLACE FUNCTION public.zscore_referentie_waarden(
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'zelfde_jaar',
    p_scenario_id     varchar DEFAULT 'current',
    p_indicator_uuids uuid[]  DEFAULT NULL,
    p_min_n           integer DEFAULT 5,
    p_provincie       varchar DEFAULT NULL
)
RETURNS TABLE (gebied_id varchar, indicator_uuid uuid, waarde numeric, jaar integer, referentie_terugval boolean)
LANGUAGE plpgsql STABLE
AS $$
#variable_conflict use_column
DECLARE
    v_min_n integer := COALESCE(p_min_n, 0);
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
          AND (p_provincie IS NULL OR EXISTS (
                SELECT 1 FROM public.gemeenten gm
                WHERE gm.code = g.gemeente_code AND gm.provincie = p_provincie))
          AND NOT public.is_waterbuurt(g.naam, g.metadata)
          AND COALESCE(gd.scenario_id, 'current') = p_scenario_id
          AND gd.jaar IS NOT NULL
          AND (p_indicator_uuids IS NULL OR gd.indicator_uuid = ANY(p_indicator_uuids))
    ),
    gemarkeerd AS (
        SELECT k.*,
               ROW_NUMBER() OVER (PARTITION BY k.k_gebied, k.k_ind ORDER BY k.k_jaar DESC) AS rn_gebied,
               MAX(k.k_jaar) OVER (PARTITION BY k.k_ind) AS peiljaar
        FROM kandidaten k
    ),
    peil AS (
        -- Aantal waarden in het peiljaar, voor de minimum-n bij 'zelfde_jaar'
        SELECT m.k_ind AS p_ind, COUNT(*) FILTER (WHERE m.k_jaar = m.peiljaar) AS n_peil
        FROM gemarkeerd m
        GROUP BY m.k_ind
    )
    SELECT m.k_gebied, m.k_ind, m.k_waarde, m.k_jaar,
           (p_jaarlogica = 'zelfde_jaar' AND p.n_peil < v_min_n)
    FROM gemarkeerd m
    JOIN peil p ON p.p_ind = m.k_ind
    WHERE p_jaarlogica = 'alle_jaren'
       OR (p_jaarlogica = 'recentst_per_gebied' AND m.rn_gebied = 1)
       OR (p_jaarlogica = 'zelfde_jaar' AND p.n_peil >= v_min_n AND m.k_jaar = m.peiljaar)
       OR (p_jaarlogica = 'zelfde_jaar' AND p.n_peil <  v_min_n AND m.rn_gebied = 1);
END;
$$;

COMMENT ON FUNCTION public.zscore_referentie_waarden(uuid, varchar, text, varchar, uuid[], integer, varchar) IS
    'Referentieset voor Z-scores; waterbuurten en scenario-projecties uitgesloten, minimum-n met terugval (#66, #155). Zie docs/3-data-engineering/zscore_methodiek.md';


-- Referentiestatistiek per indicator: gemiddelde, standaarddeviatie (steekproef) en n.
-- Zonder doelgebied; bij 'zelfde_jaar' dus het meest recente jaar van de indicator
-- (of de terugval, zie referentie_terugval).
DROP FUNCTION IF EXISTS public.zscore_referentie_stats(uuid, varchar, text, varchar, uuid[], integer);
CREATE OR REPLACE FUNCTION public.zscore_referentie_stats(
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'zelfde_jaar',
    p_scenario_id     varchar DEFAULT 'current',
    p_indicator_uuids uuid[]  DEFAULT NULL,
    p_min_n           integer DEFAULT 5,
    p_provincie       varchar DEFAULT NULL
)
RETURNS TABLE (
    indicator_uuid      uuid,
    gemiddelde          numeric,
    standaarddeviatie   numeric,
    n                   integer,
    min_waarde          numeric,
    max_waarde          numeric,
    min_jaar            integer,
    max_jaar            integer,
    referentie_terugval boolean
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
           MAX(rw.jaar),
           BOOL_OR(rw.referentie_terugval)
    FROM public.zscore_referentie_waarden(
        p_gebiedstype_id, p_gemeente_code, p_jaarlogica, p_scenario_id, p_indicator_uuids, p_min_n,
        p_provincie
    ) rw
    GROUP BY rw.indicator_uuid;
$$;

COMMENT ON FUNCTION public.zscore_referentie_stats(uuid, varchar, text, varchar, uuid[], integer, varchar) IS
    'Gemiddelde, standaarddeviatie (STDDEV_SAMP) en n per indicator van de Z-score-referentiegroep (#66, #155)';


-- Z-scores voor gebieden ten opzichte van een referentiegroep.
-- p_gebied_ids NULL = de gebieden van de referentieset zelf (zoals Kompas top-buurten).
-- Het doelgebied gebruikt zijn meest recente waarde (scenario p_scenario_id).
-- Bij 'zelfde_jaar' is de referentie het jaar van die waarde, per indicator. Hebben
-- minder dan p_min_n gebieden een waarde in dat jaar, dan is de referentie de meest
-- recente waarde per gebied en is referentie_terugval = true (#155).
-- Een waterbuurt als doelgebied krijgt geen Z-score (z_score NULL, is_waterbuurt true).
-- Indicatoren zonder referentiewaarden komen niet terug; z_score is NULL bij n < 2 of sd = 0.
DROP FUNCTION IF EXISTS public.zscore_gebieden(varchar[], uuid, varchar, text, varchar, uuid[], integer);
CREATE OR REPLACE FUNCTION public.zscore_gebieden(
    p_gebied_ids      varchar[],
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'zelfde_jaar',
    p_scenario_id     varchar DEFAULT 'current',
    p_indicator_uuids uuid[]  DEFAULT NULL,
    p_min_n           integer DEFAULT 5,
    p_provincie       varchar DEFAULT NULL
)
RETURNS TABLE (
    gebied_id           varchar,
    indicator_uuid      uuid,
    waarde              numeric,
    jaar                integer,
    gemiddelde          numeric,
    standaarddeviatie   numeric,
    n                   integer,
    min_waarde          numeric,
    max_waarde          numeric,
    z_score             numeric,
    referentie_terugval boolean,
    is_waterbuurt       boolean
)
LANGUAGE sql STABLE
AS $$
    WITH ref AS (
        -- Alle jaren; daaruit statistiek per (indicator, jaar) en per indicator (recentst)
        SELECT rw.gebied_id AS r_gebied, rw.indicator_uuid AS r_ind, rw.waarde AS r_waarde, rw.jaar AS r_jaar
        FROM public.zscore_referentie_waarden(
            p_gebiedstype_id, p_gemeente_code, 'alle_jaren', p_scenario_id, p_indicator_uuids, 5,
            p_provincie
        ) rw
    ),
    recent AS (
        SELECT DISTINCT ON (r.r_gebied, r.r_ind) r.r_gebied, r.r_ind, r.r_waarde
        FROM ref r
        ORDER BY r.r_gebied, r.r_ind, r.r_jaar DESC
    ),
    stats_jaar AS (
        SELECT r_ind, r_jaar,
               AVG(r_waarde) AS s_gem, STDDEV_SAMP(r_waarde) AS s_sd, COUNT(*)::integer AS s_n,
               MIN(r_waarde) AS s_min, MAX(r_waarde) AS s_max
        FROM ref
        GROUP BY r_ind, r_jaar
    ),
    stats_recent AS (
        SELECT r_ind,
               AVG(r_waarde) AS s_gem, STDDEV_SAMP(r_waarde) AS s_sd, COUNT(*)::integer AS s_n,
               MIN(r_waarde) AS s_min, MAX(r_waarde) AS s_max
        FROM recent
        GROUP BY r_ind
    ),
    doel AS (
        -- Gebieden uit de referentieset zelf; de terugval volgt uit de set
        SELECT rw.gebied_id AS d_gebied, rw.indicator_uuid AS d_ind, rw.waarde AS d_waarde,
               rw.jaar AS d_jaar, rw.referentie_terugval AS d_terugval
        FROM public.zscore_referentie_waarden(
            p_gebiedstype_id, p_gemeente_code, p_jaarlogica, p_scenario_id, p_indicator_uuids, p_min_n,
            p_provincie
        ) rw
        WHERE p_gebied_ids IS NULL
        UNION ALL
        -- Opgegeven gebieden (mogen buiten de referentiegroep liggen): meest recente waarde
        (
            SELECT DISTINCT ON (gd.gebied_id, gd.indicator_uuid)
                   gd.gebied_id, gd.indicator_uuid, gd.waarde, gd.jaar, NULL::boolean
            FROM public.gebied_data gd
            WHERE p_gebied_ids IS NOT NULL
              AND gd.gebied_id = ANY(p_gebied_ids)
              AND COALESCE(gd.scenario_id, 'current') = p_scenario_id
              AND gd.jaar IS NOT NULL
              AND (p_indicator_uuids IS NULL OR gd.indicator_uuid = ANY(p_indicator_uuids))
            ORDER BY gd.gebied_id, gd.indicator_uuid, gd.jaar DESC
        )
    ),
    gekozen AS (
        -- Welke referentie: het jaar van het doelgebied, of de terugval op recentst
        SELECT d.*,
               sj.s_gem AS j_gem, sj.s_sd AS j_sd, sj.s_n AS j_n, sj.s_min AS j_min, sj.s_max AS j_max,
               sr.s_gem AS r_gem, sr.s_sd AS r_sd, sr.s_n AS r_n, sr.s_min AS r_min, sr.s_max AS r_max,
               CASE WHEN p_jaarlogica <> 'zelfde_jaar' THEN false
                    ELSE COALESCE(d.d_terugval, COALESCE(sj.s_n, 0) < COALESCE(p_min_n, 0))
               END AS terugval
        FROM doel d
        LEFT JOIN stats_jaar sj ON p_jaarlogica = 'zelfde_jaar'
                               AND sj.r_ind = d.d_ind AND sj.r_jaar = d.d_jaar
        LEFT JOIN stats_recent sr ON sr.r_ind = d.d_ind
    ),
    resultaat AS (
        SELECT k.d_gebied, k.d_ind, k.d_waarde, k.d_jaar, k.terugval,
               CASE WHEN p_jaarlogica = 'zelfde_jaar' AND NOT k.terugval THEN k.j_gem ELSE k.r_gem END AS gem,
               CASE WHEN p_jaarlogica = 'zelfde_jaar' AND NOT k.terugval THEN k.j_sd  ELSE k.r_sd  END AS sd,
               CASE WHEN p_jaarlogica = 'zelfde_jaar' AND NOT k.terugval THEN k.j_n   ELSE k.r_n   END AS n,
               CASE WHEN p_jaarlogica = 'zelfde_jaar' AND NOT k.terugval THEN k.j_min ELSE k.r_min END AS mn,
               CASE WHEN p_jaarlogica = 'zelfde_jaar' AND NOT k.terugval THEN k.j_max ELSE k.r_max END AS mx
        FROM gekozen k
    )
    SELECT r.d_gebied, r.d_ind, r.d_waarde, r.d_jaar,
           r.gem, r.sd, r.n, r.mn, r.mx,
           CASE WHEN public.is_waterbuurt(g.naam, g.metadata) THEN NULL
                ELSE public.zscore(r.d_waarde, r.gem, r.sd, r.n)
           END,
           r.terugval,
           COALESCE(public.is_waterbuurt(g.naam, g.metadata), false)
    FROM resultaat r
    LEFT JOIN public.gebieden g ON g.id = r.d_gebied
    WHERE r.n IS NOT NULL;
$$;

COMMENT ON FUNCTION public.zscore_gebieden(varchar[], uuid, varchar, text, varchar, uuid[], integer, varchar) IS
    'Z-scores per gebied en indicator t.o.v. de referentiegroep; standaard zelfde jaar als het doelgebied, terugval bij n < p_min_n; geen Z-score voor waterbuurten (#66, #155)';
