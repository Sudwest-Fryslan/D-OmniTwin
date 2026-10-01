-- ============================================================
-- Z-scores: één bron voor de referentiestatistiek (#66, #155)
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
--   p_min_n            5 (standaard, #155): minimum aantal gebieden in de referentie
--                        bij 'zelfde_jaar'. Hebben minder gebieden een waarde in dat
--                        jaar, dan valt de referentie terug op 'recentst_per_gebied'
--                        en is referentie_terugval = true. 0 of NULL = nooit terugvallen.
--
-- Waterbuurten (is_waterbuurt(naam, metadata)) zitten nooit in de referentiegroep
-- en krijgen als doelgebied geen Z-score. Metingen zonder jaar tellen niet mee.
--
-- ⚠️ WAARSCHUWING (zie de methodiek voor details):
--   - Vóór #66 zaten waterbuurten wél in de referentie van executive,
--     multi-gebied, thema-analyse, benchmark en Kompas; uitkomsten verschuiven
--     waar waterbuurten waarden hebben.
--   - Vóór #66 telden scenario-projecties (scenario_id <> 'current') mee.
--   - Wijken die als CBS-buurt zijn opgeslagen (ETL/import_geografie_2024.py)
--     vallen in de referentiegroep; hangt af van de ETL (#69).
--   - gebieden.actief speelt geen rol; hangt af van de ETL (#69).
--
-- Idempotent: CREATE OR REPLACE, DROP FUNCTION IF EXISTS waar de signatuur
-- wijzigde, en een UPDATE die alleen ontbrekende watervlaggen zet.
-- Bestaande database bijwerken:
--   psql -f migrations/schema_v21_zscore_referentie.sql
-- ============================================================


-- ── Waterbuurt: één definitie (#155) ─────────────────────────────────────────
-- Een gebied is een waterbuurt als de data dat zegt (metadata->>'water' = 'JA',
-- zoals de CBS-wijk- en buurtkaart levert), of, als vangnet voor bronnen zonder
-- die vlag, als de naam op water wijst. De naamlijst is die van de oude
-- kaartview vw_gebied_kaart_basis. markeer_waterbuurten() zet de vlag bij het
-- laden in de data, zodat de naam alleen nog vangnet is.
CREATE OR REPLACE FUNCTION public.is_waterbuurt(p_naam text, p_metadata jsonb)
RETURNS boolean
LANGUAGE sql IMMUTABLE
AS $$
    SELECT COALESCE(p_metadata->>'water', 'NEE') = 'JA'
        OR COALESCE(p_naam, '') ILIKE ANY (ARRAY['%buitenwater%', '%Wadden Sea%', '%IJsselmeer%']);
$$;

COMMENT ON FUNCTION public.is_waterbuurt(text, jsonb) IS
    'Eén definitie van waterbuurt: metadata->>''water'' = ''JA'', met de naam (buitenwater, Wadden Sea, IJsselmeer) als vangnet (#155)';


-- Zet metadata.water = 'JA' (met water_bron = 'naam') voor gebieden die alleen
-- op naam als waterbuurt herkend worden. Geeft het aantal bijgewerkte gebieden.
-- Aanroepen na het laden van gebieden (load_sample.py, seed_fryslan.py, ETL).
CREATE OR REPLACE FUNCTION public.markeer_waterbuurten()
RETURNS integer
LANGUAGE sql VOLATILE
AS $$
    WITH bijgewerkt AS (
        UPDATE public.gebieden g
           SET metadata = COALESCE(g.metadata, '{}'::jsonb)
                          || jsonb_build_object('water', 'JA', 'water_bron', 'naam')
         WHERE public.is_waterbuurt(g.naam, g.metadata)
           AND COALESCE(g.metadata->>'water', 'NEE') <> 'JA'
        RETURNING 1
    )
    SELECT COUNT(*)::integer FROM bijgewerkt;
$$;

COMMENT ON FUNCTION public.markeer_waterbuurten() IS
    'Zet de watervlag in gebieden.metadata voor gebieden die alleen op naam waterbuurt zijn (#155)';

-- Bestaande data: vlag zetten (idempotent)
SELECT public.markeer_waterbuurten();

-- De kaartview gebruikt dezelfde definitie (kolommen ongewijzigd)
CREATE OR REPLACE VIEW public.vw_gebied_kaart_basis AS
 SELECT g.id,
    g.naam,
    g.gebiedstype_id,
    gt.naam AS gebiedstype_naam,
    g.actief,
    (public.st_asgeojson(public.st_transform(g.geom, 4326)))::json AS geometry
   FROM (public.gebieden g
     JOIN public.gebiedstypes gt ON ((g.gebiedstype_id = gt.id)))
  WHERE g.actief = true
    AND NOT public.is_waterbuurt(g.naam, g.metadata);


-- ── Referentieset ────────────────────────────────────────────────────────────
-- Per gebied en indicator één waarde (bij 'alle_jaren': één per jaar).
-- referentie_terugval = true: bij 'zelfde_jaar' hadden minder dan p_min_n gebieden
-- een waarde in het peiljaar; de set is dan 'recentst_per_gebied'.
DROP FUNCTION IF EXISTS public.zscore_referentie_waarden(uuid, varchar, text, varchar, uuid[]);
CREATE OR REPLACE FUNCTION public.zscore_referentie_waarden(
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'zelfde_jaar',
    p_scenario_id     varchar DEFAULT 'current',
    p_indicator_uuids uuid[]  DEFAULT NULL,
    p_min_n           integer DEFAULT 5
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

COMMENT ON FUNCTION public.zscore_referentie_waarden(uuid, varchar, text, varchar, uuid[], integer) IS
    'Referentieset voor Z-scores; waterbuurten en scenario-projecties uitgesloten, minimum-n met terugval (#66, #155). Zie docs/3-data-engineering/zscore_methodiek.md';


-- Referentiestatistiek per indicator: gemiddelde, standaarddeviatie (steekproef) en n.
-- Zonder doelgebied; bij 'zelfde_jaar' dus het meest recente jaar van de indicator
-- (of de terugval, zie referentie_terugval).
DROP FUNCTION IF EXISTS public.zscore_referentie_stats(uuid, varchar, text, varchar, uuid[]);
CREATE OR REPLACE FUNCTION public.zscore_referentie_stats(
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'zelfde_jaar',
    p_scenario_id     varchar DEFAULT 'current',
    p_indicator_uuids uuid[]  DEFAULT NULL,
    p_min_n           integer DEFAULT 5
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
        p_gebiedstype_id, p_gemeente_code, p_jaarlogica, p_scenario_id, p_indicator_uuids, p_min_n
    ) rw
    GROUP BY rw.indicator_uuid;
$$;

COMMENT ON FUNCTION public.zscore_referentie_stats(uuid, varchar, text, varchar, uuid[], integer) IS
    'Gemiddelde, standaarddeviatie (STDDEV_SAMP) en n per indicator van de Z-score-referentiegroep (#66, #155)';


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
-- Bij 'zelfde_jaar' is de referentie het jaar van die waarde, per indicator. Hebben
-- minder dan p_min_n gebieden een waarde in dat jaar, dan is de referentie de meest
-- recente waarde per gebied en is referentie_terugval = true (#155).
-- Een waterbuurt als doelgebied krijgt geen Z-score (z_score NULL, is_waterbuurt true).
-- Indicatoren zonder referentiewaarden komen niet terug; z_score is NULL bij n < 2 of sd = 0.
DROP FUNCTION IF EXISTS public.zscore_gebieden(varchar[], uuid, varchar, text, varchar, uuid[]);
CREATE OR REPLACE FUNCTION public.zscore_gebieden(
    p_gebied_ids      varchar[],
    p_gebiedstype_id  uuid,
    p_gemeente_code   varchar DEFAULT NULL,
    p_jaarlogica      text    DEFAULT 'zelfde_jaar',
    p_scenario_id     varchar DEFAULT 'current',
    p_indicator_uuids uuid[]  DEFAULT NULL,
    p_min_n           integer DEFAULT 5
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
            p_gebiedstype_id, p_gemeente_code, 'alle_jaren', p_scenario_id, p_indicator_uuids
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
            p_gebiedstype_id, p_gemeente_code, p_jaarlogica, p_scenario_id, p_indicator_uuids, p_min_n
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

COMMENT ON FUNCTION public.zscore_gebieden(varchar[], uuid, varchar, text, varchar, uuid[], integer) IS
    'Z-scores per gebied en indicator t.o.v. de referentiegroep; standaard zelfde jaar als het doelgebied, terugval bij n < p_min_n; geen Z-score voor waterbuurten (#66, #155)';
