-- v20: eigen databaserollen voor PostgREST en pg_featureserv, en schema api (#57, #137)
--
-- Standaardopzet PostgREST (https://docs.postgrest.org/en/stable/explanations/db_authz.html):
--   authenticator  LOGIN, NOINHERIT: alleen verbinden; PostgREST schakelt per verzoek naar web_anon
--   web_anon       NOLOGIN: USAGE + SELECT op schema api, EXECUTE op de api-functies. Geen schrijfrechten.
--   featureserv    LOGIN: alleen-lezen voor pg_featureserv, beperkt tot de geo-views en postgisftw-functies
--
-- PostgREST publiceert alleen schema api (PGRST_DB_SCHEMAS=api). Daarin staan alleen views
-- en functies, met dezelfde namen als de tabellen die de frontend al gebruikte, zodat de
-- URL's (/api/data/<naam>) niet veranderen. Applicatiedata (users, sessions, api_keys,
-- llm_config, system_prompts, app_logs, log_config) komt hier nooit in.
--
-- De views zijn eigendom van de database-eigenaar en lezen de tabellen met diens rechten;
-- web_anon heeft geen enkel recht op schema public.
--
-- Wachtwoorden zet docker-entrypoint.sh (db-init) na deze migratie: authenticator en
-- featureserv gebruiken DATABASE_PASSWORD. Idempotent: db-init draait dit bij elke start.

SET client_min_messages = warning;  -- geen NOTICE's van DROP ... IF EXISTS
BEGIN;

-- ── Rollen ───────────────────────────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'web_anon') THEN
        CREATE ROLE web_anon NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticator') THEN
        CREATE ROLE authenticator LOGIN NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'featureserv') THEN
        CREATE ROLE featureserv LOGIN;
    END IF;
END
$$;

ALTER ROLE web_anon      NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE authenticator LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE featureserv   LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT web_anon TO authenticator;

-- ── Schema api: alleen views en functies voor PostgREST ─────────────────────
CREATE SCHEMA IF NOT EXISTS api;
REVOKE ALL ON SCHEMA api FROM PUBLIC;
GRANT USAGE ON SCHEMA api TO web_anon;

-- Opnieuw aanmaken (DROP + CREATE) zodat kolomwijzigingen ook bij een bestaande database
-- doorkomen. Alles in één transactie: PostgREST ziet nooit een half schema.

-- Gemeenten (frontend: gemeentekeuze; admin: gemeentelijst)
DROP VIEW IF EXISTS api.gemeenten;
CREATE VIEW api.gemeenten AS
SELECT code, naam, provincie, is_eiland
FROM public.gemeenten;

-- Gebiedstypes (frontend: gebiedstypekeuze)
DROP VIEW IF EXISTS api.gebiedstypes;
CREATE VIEW api.gebiedstypes AS
SELECT id, naam, code, beschrijving, bron, niveau
FROM public.gebiedstypes;

-- Gebieden zonder geometrie en metadata (frontend: tellers; admin: gebied zoeken).
-- Geometrie gaat via pg_featureserv (/api/geo).
DROP VIEW IF EXISTS api.gebieden;
CREATE VIEW api.gebieden AS
SELECT id, naam, gebiedstype_id, gemeente_code, provincienaam, actief, created_at, updated_at
FROM public.gebieden;

-- Externe kaartlagen (frontend: kaartlagen-paneel)
DROP VIEW IF EXISTS api.externe_kaartlagen;
CREATE VIEW api.externe_kaartlagen AS
SELECT id, naam, beschrijving, laag_type, bron_type, url, typename, srsname, versie,
       filter_type, filter_waarde, koppel_veld, kleur_lijn, kleur_fill, opacity,
       actief, volgorde, created_at, updated_at
FROM public.externe_kaartlagen;

-- Indicatoren: beschrijvende metadata, zonder interne beheervelden
-- (admin_notes, ontologie_beoordeeld_door, gevalideerd_door).
-- Frontend: teller; admin: mutaties (Datakwaliteit); tests: use cases.
DROP VIEW IF EXISTS api.indicatoren;
CREATE VIEW api.indicatoren AS
SELECT id, uuid, naam, code, omschrijving, eenheid, interpretatie_logica, score_type,
       min_waarde, max_waarde, waarde_type, bron, status, categorie,
       begingeldigheid, eindgeldigheid, color_schema_id,
       ontologische_beschrijving, ontologie_status, beschrijving_ai,
       is_actief, vervangen_door_id, hoofd_indicator_id, created_at, updated_at
FROM public.indicatoren;

-- Actuele waarde per gebied en indicator (tests: use cases, #138)
DROP VIEW IF EXISTS api.vw_gebied_indicator_actueel;
CREATE VIEW api.vw_gebied_indicator_actueel AS
SELECT gebied_id, indicator_uuid, waarde, jaar, datum, bron
FROM public.vw_gebied_indicator_actueel;

-- Indicatorenlijst met aantallen (frontend: indicatorkeuze, /rpc/get_indicatoren_stats).
-- SECURITY DEFINER met vaste search_path: web_anon heeft geen rechten in public nodig.
CREATE OR REPLACE FUNCTION api.get_indicatoren_stats(p_gebiedstype_id uuid DEFAULT NULL)
RETURNS TABLE (
    uuid uuid,
    naam character varying,
    code character varying,
    omschrijving text,
    eenheid character varying,
    categorie character varying,
    aantal_gebieden_met_data bigint,
    aantal_metingen bigint,
    nieuwste_jaar integer
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT * FROM public.get_indicatoren_stats(p_gebiedstype_id)
$$;

-- Rechten in api: alleen lezen en de gewhiteliste functies
REVOKE ALL ON ALL TABLES IN SCHEMA api FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA api FROM PUBLIC;
GRANT SELECT ON
    api.gemeenten,
    api.gebiedstypes,
    api.gebieden,
    api.externe_kaartlagen,
    api.indicatoren,
    api.vw_gebied_indicator_actueel
TO web_anon;
GRANT EXECUTE ON FUNCTION api.get_indicatoren_stats(uuid) TO web_anon;

-- Nieuwe functies in api zijn niet automatisch voor iedereen uitvoerbaar
ALTER DEFAULT PRIVILEGES IN SCHEMA api REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- ── pg_featureserv: alleen de geo-views en postgisftw-functies ──────────────
-- pg_featureserv publiceert alles waarop de rol SELECT heeft; daarom alleen deze twee.
-- Collectienamen blijven public.<naam>, zodat de URL's onder /api/geo gelijk blijven.
GRANT USAGE ON SCHEMA public TO featureserv;
DO $$
BEGIN
    IF to_regclass('public.vw_gebieden_features') IS NOT NULL THEN
        GRANT SELECT ON public.vw_gebieden_features TO featureserv;          -- kaart: buurten
    END IF;
    IF to_regclass('public.omgevingsvisie_deelgebieden') IS NOT NULL THEN
        GRANT SELECT ON public.omgevingsvisie_deelgebieden TO featureserv;   -- kaart + admin: deelgebieden
    END IF;
    IF to_regnamespace('postgisftw') IS NOT NULL THEN
        GRANT USAGE ON SCHEMA postgisftw TO featureserv;
    END IF;
    IF to_regprocedure('postgisftw.buurten_in_deelgebied(integer, double precision)') IS NOT NULL THEN
        -- Leest gebieden en deelgebieden met de rechten van de eigenaar (zie 07_postgisftw_functions.sql)
        ALTER FUNCTION postgisftw.buurten_in_deelgebied(integer, double precision)
            SECURITY DEFINER SET search_path = public, pg_temp;
        REVOKE ALL ON FUNCTION postgisftw.buurten_in_deelgebied(integer, double precision) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION postgisftw.buurten_in_deelgebied(integer, double precision) TO featureserv;
    END IF;
END
$$;

COMMIT;

-- PostgREST het nieuwe schema laten inlezen (als hij al draait)
NOTIFY pgrst, 'reload schema';
