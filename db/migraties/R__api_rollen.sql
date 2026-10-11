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

-- Grens per query (#203). PostgREST past de instelling van web_anon per verzoek toe
-- ("impersonated role settings"); pg_featureserv logt direct in als featureserv.
ALTER ROLE web_anon      SET statement_timeout = '10s';
ALTER ROLE authenticator SET statement_timeout = '10s';
ALTER ROLE featureserv   SET statement_timeout = '30s';

-- ── Schema api: alleen views en functies voor PostgREST ─────────────────────
CREATE SCHEMA IF NOT EXISTS api;
REVOKE ALL ON SCHEMA api FROM PUBLIC;
GRANT USAGE ON SCHEMA api TO web_anon;

-- Opnieuw aanmaken (DROP + CREATE) zodat kolomwijzigingen ook bij een bestaande database
-- doorkomen. Alles in één transactie: PostgREST ziet nooit een half schema.

-- Toegang per laag en bron (#254, ADR 0010). De views hieronder zijn van de database-eigenaar en
-- lezen de tabellen zonder row level security; ze filteren daarom zelf: `openbaar` voor iedereen,
-- `intern` alleen als het verzoek de header X-Omnitwin-Toegang: intern heeft. Die header zet de
-- backend in het forwardAuth-antwoord (viewer-toegang@file, deploy/traefik/dynamic.yml) bij een
-- sessie of token met de rol lezer of beheerder; Traefik vervangt een meegestuurde header van de
-- client (authResponseHeaders). PostgREST is alleen via Traefik bereikbaar.
CREATE OR REPLACE FUNCTION public.verzoek_mag_intern()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT coalesce(nullif(current_setting('request.headers', true), '')::json->>'x-omnitwin-toegang', '') = 'intern'
$$;
COMMENT ON FUNCTION public.verzoek_mag_intern() IS
    'PostgREST: mag dit verzoek interne data zien? (header X-Omnitwin-Toegang van de forwardAuth, #254)';

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

-- Externe kaartlagen (frontend: kaartlagen-paneel); intern alleen met X-Omnitwin-Toegang: intern
DROP VIEW IF EXISTS api.externe_kaartlagen;
CREATE VIEW api.externe_kaartlagen AS
SELECT id, naam, beschrijving, laag_type, bron_type, url, typename, srsname, versie,
       filter_type, filter_waarde, koppel_veld, kleur_lijn, kleur_fill, opacity,
       actief, volgorde, created_at, updated_at, toegang
FROM public.externe_kaartlagen
WHERE toegang = 'openbaar' OR public.verzoek_mag_intern();

-- Indicatoren: beschrijvende metadata, zonder interne beheervelden
-- (admin_notes, ontologie_beoordeeld_door, gevalideerd_door).
-- Frontend: teller; admin: mutaties (Datakwaliteit); tests: use cases.
DROP VIEW IF EXISTS api.indicatoren;
CREATE VIEW api.indicatoren AS
SELECT id, uuid, naam, code, omschrijving, eenheid, interpretatie_logica, score_type,
       min_waarde, max_waarde, waarde_type, bron, status, categorie,
       begingeldigheid, eindgeldigheid, color_schema_id,
       ontologische_beschrijving, ontologie_status, beschrijving_ai,
       is_actief, vervangen_door_id, hoofd_indicator_id, created_at, updated_at, toegang
FROM public.indicatoren
WHERE toegang = 'openbaar' OR public.verzoek_mag_intern();

-- Actuele waarde per gebied en indicator (tests: use cases, #138). Zelfde regel als
-- public.vw_gebied_indicator_actueel (V030), maar over de waarden die dit verzoek mag zien (#254):
-- anoniem de recentste openbare waarde.
DROP VIEW IF EXISTS api.vw_gebied_indicator_actueel;
CREATE VIEW api.vw_gebied_indicator_actueel AS
SELECT DISTINCT ON (gd.gebied_id, gd.indicator_uuid)
       gd.gebied_id, gd.indicator_uuid, gd.waarde, gd.jaar, gd.datum, gd.bron
FROM public.gebied_data gd
WHERE COALESCE(gd.scenario_id, 'current') = 'current'
  AND (gd.toegang = 'openbaar' OR public.verzoek_mag_intern())
ORDER BY gd.gebied_id, gd.indicator_uuid, gd.jaar DESC NULLS LAST, gd.datum DESC NULLS LAST;

-- Waarden per gebied, indicator en jaar (use cases via /api/data/v1, laad-API #205).
-- Zonder n: waarden onder de n-drempel staan hier nooit (laad-API), n zelf is niet nodig.
-- andere_bronnen: waarden van andere datasets op dezelfde sleutel die niet voorgingen (V036, A6 van #222).
DROP VIEW IF EXISTS api.gebied_data;
CREATE VIEW api.gebied_data AS
SELECT gebied_id, indicator_uuid, jaar, datum, scenario_id, waarde, kwaliteit, bron, n_status, toegang,
       metadata->'andere_bronnen' AS andere_bronnen
FROM public.gebied_data
WHERE toegang = 'openbaar' OR public.verzoek_mag_intern();

-- Indicatorenlijst met aantallen (frontend: indicatorkeuze, /rpc/get_indicatoren_stats).
-- SECURITY DEFINER met vaste search_path: web_anon heeft geen rechten in public nodig.
-- Met toegang (#254); interne indicatoren alleen met X-Omnitwin-Toegang: intern. De aantallen
-- tellen alle waarden van de indicator (ook interne van een openbare indicator).
DROP FUNCTION IF EXISTS api.get_indicatoren_stats(uuid);
CREATE FUNCTION api.get_indicatoren_stats(p_gebiedstype_id uuid DEFAULT NULL)
RETURNS TABLE (
    uuid uuid,
    naam character varying,
    code character varying,
    omschrijving text,
    eenheid character varying,
    categorie character varying,
    aantal_gebieden_met_data bigint,
    aantal_metingen bigint,
    nieuwste_jaar integer,
    toegang text
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
    SELECT s.uuid, s.naam, s.code, s.omschrijving, s.eenheid, s.categorie, s.aantal_gebieden_met_data,
           s.aantal_metingen, s.nieuwste_jaar, i.toegang
    FROM public.get_indicatoren_stats(p_gebiedstype_id) WITH ORDINALITY AS s
    JOIN public.indicatoren i ON i.uuid = s.uuid
    WHERE i.toegang = 'openbaar' OR public.verzoek_mag_intern()
    ORDER BY s.ordinality
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
    api.vw_gebied_indicator_actueel,
    api.gebied_data
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
        -- Leest gebieden en deelgebieden met de rechten van de eigenaar (zie V027__organisatie.sql)
        ALTER FUNCTION postgisftw.buurten_in_deelgebied(integer, double precision)
            SECURITY DEFINER SET search_path = public, pg_temp;
        REVOKE ALL ON FUNCTION postgisftw.buurten_in_deelgebied(integer, double precision) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION postgisftw.buurten_in_deelgebied(integer, double precision) TO featureserv;
    END IF;
END
$$;

-- ── Schema app (#137, V047): standaard in het zoekpad ───────────────────────
-- pg_dump neemt instellingen van de database niet mee; na een restore zet db-init ze zo terug.
-- web_anon en featureserv hebben geen USAGE op app: voor hen verandert er niets.
DO $$
BEGIN
    IF to_regnamespace('app') IS NOT NULL THEN
        EXECUTE format('ALTER DATABASE %I SET search_path = "$user", public, app', current_database());
        REVOKE ALL ON SCHEMA app FROM PUBLIC;
    END IF;
END
$$;

-- ── Views in public die interne data lezen: security_invoker (#254) ─────────
-- Zo geldt de row level security op indicatoren, gebied_data en externe_kaartlagen (V032) ook als
-- de backend een anoniem verzoek als omnitwin_openbaar uitvoert via een view. Elke run opnieuw, omdat
-- een latere migratie een view opnieuw kan aanmaken (dan valt de optie weg). Alleen views die geen
-- andere rol (web_anon, featureserv) rechtstreeks leest; die lezen via schema api (eigenaar).
DO $$
DECLARE
    v record;
BEGIN
    IF to_regrole('omnitwin_openbaar') IS NULL THEN
        RETURN;
    END IF;
    FOR v IN
        WITH RECURSIVE afh(oid) AS (
            SELECT c.oid FROM pg_class c
            WHERE c.oid IN ('public.indicatoren'::regclass, 'public.gebied_data'::regclass,
                            'public.externe_kaartlagen'::regclass)
            UNION
            SELECT r.ev_class FROM pg_depend d
            JOIN pg_rewrite r ON r.oid = d.objid
            JOIN afh ON afh.oid = d.refobjid
            WHERE d.classid = 'pg_rewrite'::regclass AND r.ev_class <> d.refobjid
        )
        SELECT c.oid::regclass AS naam
        FROM afh JOIN pg_class c ON c.oid = afh.oid JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'v' AND n.nspname = 'public'
    LOOP
        EXECUTE format('ALTER VIEW %s SET (security_invoker = true)', v.naam);
    END LOOP;
END
$$;

COMMIT;

-- PostgREST het nieuwe schema laten inlezen (als hij al draait)
NOTIFY pgrst, 'reload schema';
