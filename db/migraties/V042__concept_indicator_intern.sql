-- ============================================================
-- Migratie v42: indicator met status C (concept) is intern (#341)
--
-- Besluit #341: indicatoren met de SWF-status Concept of Onderzoek zijn niet
-- openbaar. De use case swf-definities vertaalt Onderzoek naar C (D-OmniTwin kent
-- C = concept, O = operationeel, B = beëindigd). Hier: een indicator met status C
-- krijgt toegang 'intern' (ADR 0010), net als een indicator uit een interne
-- dataset; zijn waarden volgen.
--
-- Zelfde functie als in V032, met alleen `j.status = 'C'` erbij; V032 blijft
-- ongewijzigd (checksum). Idempotent: CREATE OR REPLACE en een herberekening.
-- ============================================================

CREATE OR REPLACE FUNCTION public.herbereken_toegang(p_indicatoren uuid[])
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    n integer;
BEGIN
    UPDATE public.indicatoren i SET toegang = x.toegang
    FROM (SELECT j.uuid, CASE
              WHEN j.status = 'C'
                OR EXISTS (SELECT 1 FROM laden.dataset_objecten o JOIN laden.datasets d ON d.id = o.dataset_id
                           WHERE o.soort = 'indicator' AND o.sleutel = j.uuid::text AND d.toegang = 'intern')
                OR (EXISTS (SELECT 1 FROM public.gebied_data gd
                            JOIN laden.leveringen l ON l.id = gd.levering_id
                            JOIN laden.datasets d ON d.id = l.dataset_id
                            WHERE gd.indicator_uuid = j.uuid AND d.toegang = 'intern')
                    AND NOT EXISTS (SELECT 1 FROM public.gebied_data gd
                                    LEFT JOIN laden.leveringen l ON l.id = gd.levering_id
                                    LEFT JOIN laden.datasets d ON d.id = l.dataset_id
                                    WHERE gd.indicator_uuid = j.uuid AND coalesce(d.toegang, 'openbaar') = 'openbaar'))
              THEN 'intern' ELSE 'openbaar' END AS toegang
          FROM public.indicatoren j WHERE j.uuid = ANY(p_indicatoren)) x
    WHERE i.uuid = x.uuid AND i.toegang <> x.toegang;

    UPDATE public.gebied_data gd SET toegang = x.toegang
    FROM (SELECT g.id, CASE WHEN i.toegang = 'intern' OR d.toegang = 'intern' THEN 'intern' ELSE 'openbaar' END AS toegang
          FROM public.gebied_data g
          JOIN public.indicatoren i ON i.uuid = g.indicator_uuid
          LEFT JOIN laden.leveringen l ON l.id = g.levering_id
          LEFT JOIN laden.datasets d ON d.id = l.dataset_id
          WHERE g.indicator_uuid = ANY(p_indicatoren)) x
    WHERE gd.id = x.id AND gd.toegang IS DISTINCT FROM x.toegang;
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;
END
$$;
COMMENT ON FUNCTION public.herbereken_toegang(uuid[]) IS
    'Toegang van indicatoren en hun waarden opnieuw afleiden uit de datasets en de status (C = intern) (#254, #341)';
REVOKE ALL ON FUNCTION public.herbereken_toegang(uuid[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.herbereken_toegang(uuid[]) TO laden_schrijver;

COMMENT ON COLUMN public.indicatoren.toegang IS
    'openbaar of intern (#254): intern als een interne dataset hem definieert of al zijn waarden levert, of als zijn status C (concept) is (#341)';

-- Bestaande indicatoren met status C (en wat eerder intern was door de status)
SELECT public.herbereken_toegang(ARRAY(SELECT uuid FROM public.indicatoren WHERE status = 'C' OR toegang = 'intern'));
