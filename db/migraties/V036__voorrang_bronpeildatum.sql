-- Voorrang bij overlap: nieuwste bronpeildatum wint (aanname A6, #222). Idempotent.
--
-- Leveren twee datasets een waarde voor dezelfde sleutel (gebied × indicator × jaar of
-- peildatum × scenario), dan komt in gebied_data:
--   1. de waarde met de nieuwste bronpeildatum;
--   2. bij een gelijke bronpeildatum: die uit de laatst aangeleverde levering (ontvangen_op);
--   3. daarna (alleen als ook dat gelijk is): laatst gepubliceerd, dan dataset-id.
-- De andere waarden blijven in laden.waarnemingen en staan in gebied_data.metadata onder
-- andere_bronnen (dataset, waarde, bron, bronpeildatum, n_status, levering_id), nieuwste eerst.
-- Een waarde uit een niet-openbare dataset (dct:accessRights niet PUBLIC) staat alleen in
-- andere_bronnen als de winnende dataset zelf ook niet openbaar is.
--
-- laden.waarnemingen.bronpeildatum: de stand van de bron van de levering. De laadstraat
-- (omnitwin.laden.p_waarnemingen.bronpeildatum) neemt dct:modified uit de meegeleverde
-- dcat.jsonld, anders dct:issued, anders de datum van ontvangst (UTC). De peildatum in de
-- sleutel (kolom datum) telt hier niet: binnen één sleutel is die per definitie gelijk.
--
-- Vervangt LADEN_VOORRANG (een vaste voorkeursdataset). Bestaande rijen krijgen de datum van
-- ontvangst van hun levering; sleutels met waarden uit meer dan één dataset worden opnieuw
-- beslist.

ALTER TABLE laden.waarnemingen ADD COLUMN IF NOT EXISTS bronpeildatum date;
UPDATE laden.waarnemingen w
SET bronpeildatum = (l.ontvangen_op AT TIME ZONE 'UTC')::date
FROM laden.leveringen l
WHERE l.id = w.levering_id AND w.bronpeildatum IS NULL;
ALTER TABLE laden.waarnemingen ALTER COLUMN bronpeildatum SET NOT NULL;
COMMENT ON COLUMN laden.waarnemingen.bronpeildatum IS
    'Stand van de bron (dct:modified, dct:issued of datum van ontvangst); voorrang bij overlap (A6, #222)';

-- gebied_data opnieuw opbouwen voor de sleutels in de tijdelijke tabel _sleutels
-- (gebied_id, indicator_uuid, jaar, datum, scenario_id), die de aanroeper vult.
CREATE OR REPLACE FUNCTION laden.herbouw_gebied_data() RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM public.gebied_data g USING _sleutels k
    WHERE g.gebied_id = k.gebied_id AND g.indicator_uuid = k.indicator_uuid
      AND g.jaar IS NOT DISTINCT FROM k.jaar AND g.datum IS NOT DISTINCT FROM k.datum
      AND coalesce(g.scenario_id, 'current') = k.scenario_id;

    INSERT INTO public.gebied_data (gebied_id, indicator_uuid, waarde, jaar, datum, scenario_id, bron,
                                    kwaliteit, metadata, n, n_status, levering_id)
    WITH kandidaat AS (
        SELECT w.dataset_id, w.levering_id, w.gebied_id, w.indicator_uuid, w.jaar, w.datum, w.scenario_id,
               w.waarde, w.n, w.n_status, w.kwaliteit, w.metadata, w.bronpeildatum,
               coalesce(w.bron, left(d.beschrijving->>'dct:title', 255)) AS bron,
               rtrim(coalesce(d.beschrijving->>'dct:accessRights', ''), '/') LIKE '%/PUBLIC' AS openbaar,
               row_number() OVER (PARTITION BY w.gebied_id, w.indicator_uuid, w.jaar, w.datum, w.scenario_id
                                  ORDER BY w.bronpeildatum DESC, l.ontvangen_op DESC, w.gepubliceerd_op DESC,
                                           w.dataset_id) AS rang
        FROM laden.waarnemingen w
        JOIN _sleutels k ON w.gebied_id = k.gebied_id AND w.indicator_uuid = k.indicator_uuid
             AND w.jaar IS NOT DISTINCT FROM k.jaar AND w.datum IS NOT DISTINCT FROM k.datum
             AND w.scenario_id = k.scenario_id
        JOIN laden.datasets d ON d.id = w.dataset_id
        JOIN laden.leveringen l ON l.id = w.levering_id
    ),
    andere AS (
        SELECT gebied_id, indicator_uuid, coalesce(jaar, -1) AS j, coalesce(datum, '-infinity'::timestamp) AS dt,
               scenario_id,
               jsonb_agg(o ORDER BY rang) AS alle,
               jsonb_agg(o ORDER BY rang) FILTER (WHERE openbaar) AS openbare
        FROM (SELECT *, jsonb_build_object('dataset', dataset_id, 'waarde', waarde, 'bron', bron,
                                           'bronpeildatum', bronpeildatum, 'n_status', n_status,
                                           'levering_id', levering_id) AS o
              FROM kandidaat WHERE rang > 1) x
        GROUP BY 1, 2, 3, 4, 5
    )
    SELECT a.gebied_id, a.indicator_uuid, a.waarde, a.jaar, a.datum, a.scenario_id, a.bron, a.kwaliteit,
           jsonb_build_object('dataset', a.dataset_id, 'bronpeildatum', a.bronpeildatum)
               || coalesce(a.metadata, '{}'::jsonb)
               || CASE WHEN (CASE WHEN a.openbaar THEN o.openbare ELSE o.alle END) IS NULL THEN '{}'::jsonb
                       ELSE jsonb_build_object('andere_bronnen', CASE WHEN a.openbaar THEN o.openbare ELSE o.alle END)
                  END,
           a.n, a.n_status, a.levering_id
    FROM kandidaat a
    LEFT JOIN andere o ON o.gebied_id = a.gebied_id AND o.indicator_uuid = a.indicator_uuid
         AND o.j = coalesce(a.jaar, -1) AND o.dt = coalesce(a.datum, '-infinity'::timestamp)
         AND o.scenario_id = a.scenario_id
    WHERE a.rang = 1
    ON CONFLICT DO NOTHING;
END
$$;
COMMENT ON FUNCTION laden.herbouw_gebied_data() IS
    'gebied_data opnieuw voor de sleutels in _sleutels: nieuwste bronpeildatum wint, dan laatst aangeleverd; rest in metadata.andere_bronnen (A6, #222)';
REVOKE ALL ON FUNCTION laden.herbouw_gebied_data() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION laden.herbouw_gebied_data() TO laden_schrijver;

-- Bestaande overlap opnieuw beslissen volgens de nieuwe regel
CREATE TEMP TABLE _sleutels ON COMMIT DROP AS
SELECT gebied_id, indicator_uuid, jaar, datum, scenario_id
FROM laden.waarnemingen
GROUP BY gebied_id, indicator_uuid, jaar, datum, scenario_id
HAVING count(DISTINCT dataset_id) > 1;
SELECT laden.herbouw_gebied_data();
DROP TABLE _sleutels;
