-- Actuele waarde per gebied en indicator: alleen gerealiseerde waarden (#159). Idempotent.
--
-- De view sorteerde op jaar DESC zonder NULLS LAST en zonder scenariofilter:
--   - een rij zonder jaar (alleen datum) kwam vóór elk jaar en gold als "actueel";
--   - een projectie (scenario_id '2030', '2050', ...) kon de recentste waarde zijn.
-- Nu: alleen scenario 'current' (NULL telt als 'current', zoals in de Z-score-referentie,
-- db/schema/08_zscore_referentie.sql), recentste jaar eerst met NULLS LAST, bij gelijk jaar
-- de recentste datum. Zelfde kolommen, dus CREATE OR REPLACE; api.vw_gebied_indicator_actueel
-- (R__api_rollen.sql) leest deze view en hoeft niet mee.
CREATE OR REPLACE VIEW public.vw_gebied_indicator_actueel AS
SELECT DISTINCT ON (gd.gebied_id, gd.indicator_uuid)
    gd.gebied_id,
    gd.indicator_uuid,
    gd.waarde,
    gd.jaar,
    gd.datum,
    gd.bron
FROM public.gebied_data gd
WHERE COALESCE(gd.scenario_id, 'current') = 'current'
ORDER BY gd.gebied_id, gd.indicator_uuid, gd.jaar DESC NULLS LAST, gd.datum DESC NULLS LAST;

COMMENT ON VIEW public.vw_gebied_indicator_actueel IS
    'Recentste gerealiseerde waarde (scenario current) per gebied en indicator; jaar NULLS LAST (#159)';
