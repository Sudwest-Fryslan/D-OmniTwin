-- Functies voor pg_featureserv (OGC API Features "functions").
-- pg_featureserv publiceert automatisch alle set-returning functies in schema postgisftw
-- onder /api/geo/functions/postgisftw.<naam>/items?<param>=<waarde>.
-- Functies geven alleen de kolommen terug die de frontend nodig heeft (geen metadata e.d.).
-- Idempotent: veilig om opnieuw uit te voeren.

CREATE SCHEMA IF NOT EXISTS postgisftw;

-- CBS-buurten die een omgevingsvisie-deelgebied snijden (#68).
-- Vervangt het verwijderde endpoint /api/omgevingsvisie/deelgebieden/{id}/buurten.
-- Het deelgebied wordt eerst met een inward buffer (standaard -10 m) verkleind, zodat
-- buurten die alleen op de grens raken niet dubbel bij aangrenzende deelgebieden vallen.
-- De buffer wordt altijd inward toegepast: -abs(buffer_m), en 0 valt terug op -10 (zoals voorheen).
-- Beide geometrieen zijn RD New (EPSG:28992), dus de buffer is in meters;
-- pg_featureserv herprojecteert de uitvoer naar EPSG:4326.
CREATE OR REPLACE FUNCTION postgisftw.buurten_in_deelgebied(
    deelgebied_id integer,
    buffer_m double precision DEFAULT -10
)
RETURNS TABLE(id text, naam text, geom geometry)
LANGUAGE sql
STABLE
PARALLEL SAFE
-- pg_featureserv verbindt als rol featureserv, die alleen de geo-views mag lezen (#57).
-- De functie leest gebieden en deelgebieden daarom met de rechten van de eigenaar.
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT g.id::text, g.naam::text, g.geom
    FROM public.gebieden g
    JOIN public.gebiedstypes gt ON g.gebiedstype_id = gt.id
    WHERE gt.code = 'CBS_BUURT'
      AND g.gemeente_code = '1900'
      AND g.actief = true
      AND ST_Intersects(
            g.geom,
            ST_Buffer(
                (SELECT d.geom FROM public.omgevingsvisie_deelgebieden d
                 WHERE d.id = buurten_in_deelgebied.deelgebied_id),
                CASE WHEN buurten_in_deelgebied.buffer_m = 0 THEN -10
                     ELSE -abs(buurten_in_deelgebied.buffer_m) END
            )
      )
    ORDER BY g.naam
$$;

COMMENT ON FUNCTION postgisftw.buurten_in_deelgebied(integer, double precision) IS
    'CBS-buurten (SWF, gemeente 1900) die een omgevingsvisie-deelgebied snijden, met inward buffer in meters (standaard -10). Gepubliceerd via pg_featureserv.';
