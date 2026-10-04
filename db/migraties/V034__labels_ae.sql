-- Labels A-E per indicator en thema (#256). Idempotent.
--
-- 1. kompas_configuraties.classificatie krijgt de waarde label_ae (naast zscore en
--    percentiel_8, V031): elke indicator, elk onderdeel, thema en kwadrant krijgt een
--    label A (gunstigst) t/m E.
-- 2. Tabel indicator_labels: drempels per indicator als data. Zonder drempels rekent
--    D-OmniTwin voorlopig met kwintielen (20%-klassen) binnen de referentiegroep; met
--    drempels gelden die. Zo zijn de drempels van de Klimaatmonitor later in te laden
--    zonder code (#222, vraag A3). Methodiek: docs/3-data-engineering/labels_methodiek.md
--
-- Laden, bijvoorbeeld:
--   INSERT INTO indicator_labels (indicator_uuid, label, ondergrens, bovengrens, bron)
--   VALUES ('<uuid>', 'A', NULL, 5, 'Klimaatmonitor SWF'), ('<uuid>', 'B', 5, 10, '...'), ...
--   ON CONFLICT (indicator_uuid, label) DO UPDATE SET ondergrens = EXCLUDED.ondergrens, ...;
-- of \copy indicator_labels (indicator_uuid, label, ondergrens, bovengrens, bron) FROM 'drempels.csv' CSV HEADER

ALTER TABLE public.kompas_configuraties DROP CONSTRAINT IF EXISTS kompas_configuraties_classificatie_check;
ALTER TABLE public.kompas_configuraties ADD CONSTRAINT kompas_configuraties_classificatie_check
    CHECK (classificatie IN ('zscore', 'percentiel_8', 'label_ae'));

COMMENT ON COLUMN public.kompas_configuraties.classificatie IS
    'Kleuring van het Kompas: zscore (standaard), percentiel_8 (8 klassen van 12,5%, #255) of label_ae (labels A-E, #256)';

CREATE TABLE IF NOT EXISTS public.indicator_labels (
    indicator_uuid uuid NOT NULL REFERENCES public.indicatoren(uuid) ON DELETE CASCADE,
    label          char(1) NOT NULL CHECK (label IN ('A', 'B', 'C', 'D', 'E')),
    ondergrens     double precision,
    bovengrens     double precision,
    bron           text,
    opmerking      text,
    bijgewerkt     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (indicator_uuid, label),
    CONSTRAINT indicator_labels_grenzen_check
        CHECK (ondergrens IS NULL OR bovengrens IS NULL OR ondergrens < bovengrens)
);

COMMENT ON TABLE public.indicator_labels IS
    'Drempels voor de labels A-E per indicator (#256): label geldt als ondergrens <= waarde < bovengrens '
    '(leeg = open). Bij overlap wint het gunstigste label. Zonder rijen voor een indicator: voorlopig kwintielen.';
COMMENT ON COLUMN public.indicator_labels.label IS 'A = gunstigst, E = ongunstigst; de drempels bepalen zelf de richting';
COMMENT ON COLUMN public.indicator_labels.ondergrens IS 'Inclusief; NULL = geen ondergrens';
COMMENT ON COLUMN public.indicator_labels.bovengrens IS 'Exclusief; NULL = geen bovengrens';
COMMENT ON COLUMN public.indicator_labels.bron IS 'Herkomst van de drempels, bijv. vastgestelde drempels van de Klimaatmonitor';
