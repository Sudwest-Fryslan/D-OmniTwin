-- Contrastrijke, instelbare selectie- en highlightstijl op de kaart (#500, ADR 0007, ADR 0011).
-- Standaard: Magenta (#e6007e), 4 px, dubbele halo-rand, geen vlakvulling bij hover/selectie.
-- Idempotent: veilig opnieuw uit te voeren.

ALTER TABLE public.organisatie ADD COLUMN IF NOT EXISTS selectie_kleur varchar(7);
ALTER TABLE public.organisatie ADD COLUMN IF NOT EXISTS selectie_lijndikte integer;
ALTER TABLE public.organisatie ADD COLUMN IF NOT EXISTS selectie_lijntype varchar(20);
ALTER TABLE public.organisatie ADD COLUMN IF NOT EXISTS selectie_vulling boolean;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'organisatie_selectie_kleur_check') THEN
        ALTER TABLE public.organisatie ADD CONSTRAINT organisatie_selectie_kleur_check
            CHECK (selectie_kleur IS NULL OR selectie_kleur ~ '^#[0-9A-Fa-f]{6}$');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'organisatie_selectie_lijndikte_check') THEN
        ALTER TABLE public.organisatie ADD CONSTRAINT organisatie_selectie_lijndikte_check
            CHECK (selectie_lijndikte IS NULL OR (selectie_lijndikte BETWEEN 2 AND 8));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'organisatie_selectie_lijntype_check') THEN
        ALTER TABLE public.organisatie ADD CONSTRAINT organisatie_selectie_lijntype_check
            CHECK (selectie_lijntype IS NULL OR selectie_lijntype IN ('doorgetrokken', 'gestreept', 'halo'));
    END IF;
END $$;

COMMENT ON COLUMN public.organisatie.selectie_kleur IS
    'Hexkleur (#RRGGBB) voor geselecteerde en gehighlighte kaartgebieden; leeg = #e6007e (#500)';
COMMENT ON COLUMN public.organisatie.selectie_lijndikte IS
    'Lijndikte in pixels (2-8) voor selectieranden op de kaart; leeg = 4 (#500)';
COMMENT ON COLUMN public.organisatie.selectie_lijntype IS
    'Lijntype voor selectieranden: doorgetrokken, gestreept of halo; leeg = halo (#500)';
COMMENT ON COLUMN public.organisatie.selectie_vulling IS
    'Of geselecteerde en gehighlighte gebieden een doorzichtige vlakvulling krijgen; leeg = false (#500)';
