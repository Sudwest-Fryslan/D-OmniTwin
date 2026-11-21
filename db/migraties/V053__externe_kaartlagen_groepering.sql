-- V053: Externe kaartlagen groeperen, ordenen en koppelen aan Kompasthema en indicatoren (#527)
--
-- Breidt public.externe_kaartlagen uit zodat lagen gegroepeerd kunnen worden op
-- algemene groepsnaam of Kompasthema, geordend per groep en laag, en gekoppeld
-- aan één of meer indicator-UUID's (tevens gebruikt door #528 uitlichten).

ALTER TABLE public.externe_kaartlagen
    ADD COLUMN IF NOT EXISTS groep_naam varchar(120),
    ADD COLUMN IF NOT EXISTS groep_volgorde integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS kompas_thema_naam varchar(150),
    ADD COLUMN IF NOT EXISTS gekoppelde_indicatoren uuid[] NOT NULL DEFAULT '{}'::uuid[];

CREATE INDEX IF NOT EXISTS idx_externe_kaartlagen_groep_volgorde
    ON public.externe_kaartlagen (actief, groep_volgorde, volgorde, naam);

COMMENT ON COLUMN public.externe_kaartlagen.groep_naam IS
    'Optionele groepsnaam in het kaartlagenpaneel; leeg valt terug op kompas_thema_naam of Overige kaartlagen (#527).';
COMMENT ON COLUMN public.externe_kaartlagen.groep_volgorde IS
    'Sorteervolgorde van de kaartlagengroep (oplopend, standaard 0; #527).';
COMMENT ON COLUMN public.externe_kaartlagen.kompas_thema_naam IS
    'Koppeling naar naam van een Kompasthema (kompas_themas.naam; #527/#528).';
COMMENT ON COLUMN public.externe_kaartlagen.gekoppelde_indicatoren IS
    'Lijst met indicator-UUID''s (indicatoren.uuid) die met deze kaartlaag samenhangen (#527/#528).';
