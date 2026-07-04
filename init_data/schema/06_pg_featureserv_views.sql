-- Fix voor pg_featureserv: 
-- Omdat we zowel geom als geom_centroid hebben, kiest pg_featureserv soms willekeurig de centroid.
-- Deze view zorgt ervoor dat pg_featureserv altijd de MultiPolygon geometries serveert voor de kaart.

CREATE OR REPLACE VIEW public.vw_gebieden_features AS 
SELECT 
    id, 
    naam, 
    gebiedstype_id, 
    gemeente_code, 
    provincienaam, 
    geom 
FROM public.gebieden;
