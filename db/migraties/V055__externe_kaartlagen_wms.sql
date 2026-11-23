-- Migratie V055: Externe WMS-lagen met serverstijl en overlay-laagtype (#529)
-- Breidt public.externe_kaartlagen uit met een optionele WMS-stijlnaam en
-- staat naast 'selectie' en 'data_koppel' ook 'overlay' toe als laag_type.

ALTER TABLE public.externe_kaartlagen
    ADD COLUMN IF NOT EXISTS wms_stijl character varying(120);

ALTER TABLE public.externe_kaartlagen
    DROP CONSTRAINT IF EXISTS externe_kaartlagen_laag_type_check;

ALTER TABLE public.externe_kaartlagen
    ADD CONSTRAINT externe_kaartlagen_laag_type_check
    CHECK ((laag_type)::text = ANY (ARRAY['selectie'::text, 'data_koppel'::text, 'overlay'::text]));

COMMENT ON COLUMN public.externe_kaartlagen.wms_stijl IS
    'Optionele WMS STYLES-parameter (leeg = standaard serverstijl van de WMS-bron; #529).';
