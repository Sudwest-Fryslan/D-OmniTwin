-- De eigen organisatie van deze instantie als data (#231, ADR 0007); idempotent.
--
-- Eén D-OmniTwin-instantie hoort bij één organisatie. Wat de code over die
-- organisatie moet weten (naam, gemeentecode(s) van het eigen gebied,
-- standaard-referentie, contactpunt, logo's) staat in deze tabel, niet in de code.
-- De inhoud komt uit db/stuurdata/organisatie.sql (docker-entrypoint.sh laadt dat
-- bij elke db-init, alleen als de tabel nog leeg is).
--
-- Daarnaast: postgisftw.buurten_in_deelgebied filtert niet meer op een vaste
-- gemeentecode, maar op de gemeentecodes van de eigen organisatie. Deze definitie
-- vervangt die uit db/schema/07_postgisftw_functions.sql.

CREATE TABLE IF NOT EXISTS public.organisatie (
    id                     boolean     PRIMARY KEY DEFAULT true CHECK (id),  -- hooguit één rij
    code                   text        NOT NULL,
    naam                   text        NOT NULL,
    korte_naam             text,
    oin                    text        CHECK (oin IS NULL OR oin ~ '^[0-9]{20}$'),
    gemeente_codes         text[]      NOT NULL DEFAULT '{}',
    benchmark_provincie    text,
    contact_email          text,
    logos                  jsonb       NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(logos) = 'array'),
    thema                  text        NOT NULL DEFAULT 'd-omnitwin' CHECK (thema ~ '^[a-z0-9-]+$'),
    bijgewerkt_op          timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.organisatie IS
    'De eigen organisatie van deze instantie (#231, ADR 0007): hooguit één rij. Vulling: db/stuurdata/organisatie.sql. Lezen: GET /api/organisatie.';
COMMENT ON COLUMN public.organisatie.code IS 'Korte, stabiele code van de organisatie (bijv. swf); geen seriële ID.';
COMMENT ON COLUMN public.organisatie.korte_naam IS 'Korte naam voor labels (bijv. SWF).';
COMMENT ON COLUMN public.organisatie.oin IS 'Organisatie-identificatienummer (20 cijfers), optioneel.';
COMMENT ON COLUMN public.organisatie.gemeente_codes IS 'CBS-gemeentecodes (4 cijfers) van het eigen gebied; de eerste is de standaard-referentie in rapporten.';
COMMENT ON COLUMN public.organisatie.benchmark_provincie IS 'Standaard-benchmarkgebied: naam van de provincie zoals in gemeenten.provincie (bijv. Fryslân).';
COMMENT ON COLUMN public.organisatie.contact_email IS 'Functioneel contactadres van de organisatie voor deze instantie.';
COMMENT ON COLUMN public.organisatie.thema IS 'Huisstijl (NLDS-thema): static/css/themes/<thema>.css als dat bestaat; alleen [a-z0-9-].';
COMMENT ON COLUMN public.organisatie.logos IS 'Logo''s in de footer, op volgorde: [{"pad": "/static/images/...", "naam": "...", "rol": "eigen"|"partner"}].';

-- CBS-buurten die een omgevingsvisie-deelgebied snijden (#68), alleen buurten van
-- de eigen organisatie (organisatie.gemeente_codes). Zonder organisatie of zonder
-- gemeentecodes: geen gemeentefilter.
CREATE SCHEMA IF NOT EXISTS postgisftw;

CREATE OR REPLACE FUNCTION postgisftw.buurten_in_deelgebied(
    deelgebied_id integer,
    buffer_m double precision DEFAULT -10
)
RETURNS TABLE(id text, naam text, geom geometry)
LANGUAGE sql
STABLE
PARALLEL SAFE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    WITH eigen AS (
        SELECT COALESCE((SELECT o.gemeente_codes FROM public.organisatie o), '{}') AS codes
    )
    SELECT g.id::text, g.naam::text, g.geom
    FROM public.gebieden g
    JOIN public.gebiedstypes gt ON g.gebiedstype_id = gt.id
    CROSS JOIN eigen
    WHERE gt.code = 'CBS_BUURT'
      AND (cardinality(eigen.codes) = 0 OR g.gemeente_code = ANY (eigen.codes))
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
    'CBS-buurten van de eigen organisatie (organisatie.gemeente_codes) die een omgevingsvisie-deelgebied snijden, met inward buffer in meters (standaard -10). Gepubliceerd via pg_featureserv.';
