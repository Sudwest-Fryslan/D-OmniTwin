-- Migratie V056: Opt-in objectinformatie (GetFeatureInfo) per externe WMS-laag (#530)
ALTER TABLE public.externe_kaartlagen
    ADD COLUMN IF NOT EXISTS info_actief boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN public.externe_kaartlagen.info_actief IS
    'Of klikken in inspectiemodus WMS GetFeatureInfo mag opvragen voor deze laag (#530; standaard uit).';
