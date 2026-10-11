-- Schema app: applicatie- en runtime-data apart van stuurinformatie en brondata (#137, stap 1). Idempotent.
--
-- Naar app gaan de tabellen die alleen de backend leest en schrijft, die geheim zijn en die nooit
-- gedeeld of gepubliceerd worden: gebruikers, sessies, sleutels, logs, LLM- en logconfiguratie,
-- gebruikersvoorkeuren, gebruikersmeldingen (V045, met e-mailadres), deduplicatie-uitzonderingen en de AI-vrijgave en het AI-logboek (V039).
-- ALTER TABLE ... SET SCHEMA verplaatst de tabel met data, indexen, constraints, triggers, rechten
-- en eigen sequences; verwijzingen (foreign keys, views, defaults) gaan op oid en blijven werken.
--
-- Wat in public blijft: stuurinformatie (indicatoren, Kompas, kleurschema's, prompts, scenario's),
-- brondata (gebieden, gebied_data, ...) en de beheertabellen van db-init (schema_migraties,
-- installatie_status). Die splitsing (schema's stuur en bron) is een vervolgstap.
--
-- search_path: de database krijgt "$user", public, app als standaard, zodat queries zonder schema
-- (FROM users) blijven werken. R__api_rollen.sql zet dit bij elke start opnieuw, want pg_dump neemt
-- database-instellingen niet mee (restore.sh). PostgREST (alleen api) en pg_featureserv (alleen
-- de geo-views) krijgen geen rechten in app.

CREATE SCHEMA IF NOT EXISTS app;
COMMENT ON SCHEMA app IS
    'Applicatie- en runtime-data (#137): alleen de backend; nooit via PostgREST of pg_featureserv, niet delen';
REVOKE ALL ON SCHEMA app FROM PUBLIC;

DO $$
DECLARE
    t text;
    r record;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'users', 'sessions', 'api_keys', 'oidc_sessies',
        'app_logs', 'log_config', 'llm_config',
        'gebruiker_voorkeuren', 'gebruiker_favorieten',
        'deduplicatie_uitzonderingen', 'gebruiker_meldingen',
        'ai_usecases', 'ai_verklaringen', 'ai_vrijgave_log', 'ai_instellingen', 'ai_logboek'
    ] LOOP
        IF to_regclass('public.' || t) IS NOT NULL AND to_regclass('app.' || t) IS NULL THEN
            EXECUTE format('ALTER TABLE public.%I SET SCHEMA app', t);
        END IF;
    END LOOP;

    -- Rollen met rechten op een tabel in app (zoals omnitwin_ai_log) hebben het schema nodig
    FOR r IN
        SELECT DISTINCT g.grantee
        FROM information_schema.role_table_grants g
        WHERE g.table_schema = 'app' AND g.grantee <> 'PUBLIC' AND g.grantee <> current_user
    LOOP
        EXECUTE format('GRANT USAGE ON SCHEMA app TO %I', r.grantee);
    END LOOP;

    EXECUTE format('ALTER DATABASE %I SET search_path = "$user", public, app', current_database());
END
$$;

-- Deze migratie zelf (en de rest van deze sessie) ook al met app in het pad
SET search_path = "$user", public, app;

-- ── AI-logboek (V039): functies die de tabellen bij naam noemen ─────────────
-- De trigger- en opschoonfunctie verwezen naar public.ai_logboek; nu naar app. Zelfde logica, zelfde hash.
CREATE OR REPLACE FUNCTION public.ai_logboek_keten() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('omnitwin.ai_logboek'));
    NEW.id := nextval('app.ai_logboek_id_seq');
    NEW.tijdstip := clock_timestamp();
    NEW.vorige_hash := (SELECT l.hash FROM app.ai_logboek l ORDER BY l.id DESC LIMIT 1);
    NEW.hash := public.ai_logboek_regelhash(NEW);
    RETURN NEW;
END
$$;

CREATE OR REPLACE FUNCTION public.ai_logboek_opschonen(p_app_versie text DEFAULT NULL) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, app, pg_temp AS $$
DECLARE
    dagen  integer;
    tot_id bigint;
    n      integer;
BEGIN
    SELECT bewaartermijn_dagen INTO dagen FROM app.ai_instellingen WHERE id;
    dagen := coalesce(dagen, 365);
    PERFORM pg_advisory_xact_lock(hashtext('omnitwin.ai_logboek'));
    SELECT max(id) INTO tot_id FROM app.ai_logboek
     WHERE tijdstip < now() - make_interval(days => dagen);
    IF tot_id IS NULL THEN
        RETURN 0;
    END IF;
    DELETE FROM app.ai_logboek WHERE id <= tot_id;
    GET DIAGNOSTICS n = ROW_COUNT;
    INSERT INTO app.ai_logboek (usecase, functie, status, taak, resultaat, app_versie)
    VALUES ('-', 'opschonen', 'opgeschoond', format('Opschonen na de bewaartermijn van %s dagen', dagen),
            format('%s regels verwijderd, tot en met id %s', n, tot_id), p_app_versie);
    RETURN n;
END
$$;

-- De schrijf- en opschoonrol hebben het schema nodig, ook als de lus hierboven ze niet zag
GRANT USAGE ON SCHEMA app TO omnitwin_ai_log, omnitwin_ai_log_opschoner;
