-- Vrijgave van AI-usecases (#307) en het AI-logboek (#313). Idempotent.
--
-- AI-usecases (afgesproken met de AI Officer): A = Assistent, B = Samenvatting/rapport,
-- C = Zoeken (semantisch). Een usecase is open als er een verklaring (PDF) is met geldig_tot op of
-- na vandaag en hij niet is stilgezet. Zonder verklaring: dicht, ook na deze migratie op een
-- bestaande installatie. De poort zelf: src/omnitwin/ai_vrijgave.py.
--
--   ai_usecases        de drie usecases, met noodstop (stilgezet) en wie die het laatst omzette
--   ai_verklaringen    de geüploade verklaringen (PDF in de database: zit zo in elke pg_dump-back-up);
--                      de nieuwste per usecase is de actuele
--   ai_vrijgave_log    upload, noodstop, hervat, verlopen en bewaartermijn: alleen toevoegen
--   ai_instellingen    bewaartermijn van het AI-logboek (per instantie, standaard 365 dagen)
--   ai_logboek         elke AI-actie (ook geweigerde), zonder gebruikersgegevens; alleen toevoegen,
--                      hashketen (hash = sha256(inhoud + hash vorige regel))
--
-- Rollen:
--   omnitwin_ai_log            de backend schrijft het logboek als deze rol (SET LOCAL ROLE):
--                              alleen SELECT en INSERT
--   omnitwin_ai_log_opschoner  eigenaar van ai_logboek_opschonen() (SECURITY DEFINER): de enige die
--                              regels mag verwijderen, en alleen ouder dan de bewaartermijn
-- Een trigger weigert UPDATE, TRUNCATE en DELETE (behalve door de opschoner), ook voor de eigenaar
-- en een superuser. Wie de trigger uitzet of omzeilt, breekt de hashketen: de controle ziet dat.
-- Fail-closed: lukt schrijven in het logboek niet of klopt de keten niet, dan zet de applicatie
-- A, B en C automatisch stil (door = 'systeem'); functioneel beheer zet ze zelf weer open.

-- ── Rollen ───────────────────────────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'omnitwin_ai_log') THEN
        CREATE ROLE omnitwin_ai_log NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'omnitwin_ai_log_opschoner') THEN
        CREATE ROLE omnitwin_ai_log_opschoner NOLOGIN;
    END IF;
END
$$;
ALTER ROLE omnitwin_ai_log NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE omnitwin_ai_log_opschoner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

-- De database-eigenaar (db-init en de backend) mag naar de schrijfrol schakelen en de functie
-- aan de opschoner geven
DO $$
BEGIN
    IF NOT pg_has_role(current_user, 'omnitwin_ai_log', 'MEMBER') THEN
        EXECUTE format('GRANT omnitwin_ai_log TO %I', current_user);
    END IF;
    IF NOT pg_has_role(current_user, 'omnitwin_ai_log_opschoner', 'MEMBER') THEN
        EXECUTE format('GRANT omnitwin_ai_log_opschoner TO %I', current_user);
    END IF;
END
$$;

-- ── Vrijgave ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.ai_usecases (
    code          text PRIMARY KEY CHECK (code IN ('A', 'B', 'C')),
    naam          text NOT NULL,
    omschrijving  text NOT NULL,
    stilgezet     boolean NOT NULL DEFAULT false,   -- noodstop door functioneel beheer
    status_door   text,                             -- login die de noodstop het laatst omzette; 'systeem' = automatisch
    status_op     timestamptz,
    stilgezet_reden text                            -- toelichting bij de noodstop (automatisch: de reden)
);
COMMENT ON TABLE public.ai_usecases IS
    'AI-usecases (#307): open alleen met een geldige verklaring (ai_verklaringen) en zonder noodstop';

INSERT INTO public.ai_usecases (code, naam, omschrijving) VALUES
    ('A', 'Assistent', 'Chat: intentie, toelichting en de formulering van antwoorden op datavragen met een taalmodel.'),
    ('B', 'Samenvatting/rapport', 'Samenvattingen per domein, totaal en benchmark in rapporten, met een taalmodel.'),
    ('C', 'Zoeken (semantisch)', 'Zoeken op betekenis met het embeddingmodel: Kompas-zoeken, de betekenis in de chatrelevantie en kandidaten bij deduplicatie.')
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.ai_verklaringen (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usecase        text NOT NULL REFERENCES public.ai_usecases(code),
    versie         text NOT NULL CHECK (length(btrim(versie)) BETWEEN 1 AND 100),
    geldig_tot     date NOT NULL,
    bestandsnaam   text NOT NULL CHECK (length(bestandsnaam) BETWEEN 1 AND 255),
    pdf            bytea NOT NULL,
    grootte        integer NOT NULL CHECK (grootte > 0),
    sha256         text NOT NULL,
    geupload_door  text NOT NULL,
    geupload_op    timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE public.ai_verklaringen IS
    'Verklaringen (DPIA/IAMA/besluit, PDF) per AI-usecase (#307); de nieuwste per usecase is de actuele';
CREATE INDEX IF NOT EXISTS idx_ai_verklaringen_usecase ON public.ai_verklaringen (usecase, geupload_op DESC);

CREATE TABLE IF NOT EXISTS public.ai_vrijgave_log (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tijdstip       timestamptz NOT NULL DEFAULT now(),
    usecase        text,
    actie          text NOT NULL CHECK (actie IN ('verklaring_geupload', 'noodstop', 'hervat', 'verlopen', 'bewaartermijn')),
    door           text,             -- login; leeg = automatisch (verlopen)
    verklaring_id  uuid,
    versie         text,
    geldig_tot     date,
    toelichting    text
);
COMMENT ON TABLE public.ai_vrijgave_log IS 'Aan- en uitzetten van AI-usecases (#307); alleen toevoegen';
CREATE INDEX IF NOT EXISTS idx_ai_vrijgave_log_tijdstip ON public.ai_vrijgave_log (tijdstip DESC);

CREATE TABLE IF NOT EXISTS public.ai_instellingen (
    id                   boolean PRIMARY KEY DEFAULT true CHECK (id),
    bewaartermijn_dagen  integer NOT NULL DEFAULT 365 CHECK (bewaartermijn_dagen BETWEEN 30 AND 3650),
    gewijzigd_door       text,
    gewijzigd_op         timestamptz
);
COMMENT ON TABLE public.ai_instellingen IS 'Instellingen van het AI-logboek (#313): bewaartermijn per instantie';
INSERT INTO public.ai_instellingen (id) VALUES (true) ON CONFLICT (id) DO NOTHING;

-- ── AI-logboek ───────────────────────────────────────────────────────────────
CREATE SEQUENCE IF NOT EXISTS public.ai_logboek_id_seq;

CREATE TABLE IF NOT EXISTS public.ai_logboek (
    id           bigint PRIMARY KEY,            -- gezet door de trigger, onder het slot
    tijdstip     timestamptz NOT NULL,          -- idem
    usecase      text NOT NULL CHECK (usecase IN ('A', 'B', 'C', 'X', '-')),  -- X = buiten A/B/C, - = opschonen
    functie      text NOT NULL,
    status       text NOT NULL CHECK (status IN ('uitgevoerd', 'geweigerd', 'fout', 'opgeschoond')),
    taak         text,                          -- vraag of taak, afgekapt
    bronnen      text[] NOT NULL DEFAULT '{}',  -- indicator- of document-id's
    model        text,
    modelversie  text,
    app_versie   text,
    resultaat    text,                          -- afgekapt
    foutmelding  text,
    vorige_hash  text,
    hash         text NOT NULL
);
COMMENT ON TABLE public.ai_logboek IS
    'Elke AI-actie (#313), zonder gebruikersgegevens; alleen toevoegen, hashketen, opgeschoond na de bewaartermijn';
CREATE INDEX IF NOT EXISTS idx_ai_logboek_tijdstip ON public.ai_logboek (tijdstip);

-- Inhoud van een regel voor de hash; src/omnitwin/ai_logboek.py (regelhash) doet precies hetzelfde
CREATE OR REPLACE FUNCTION public.ai_logboek_regelhash(r public.ai_logboek) RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT encode(sha256(convert_to(concat_ws(E'\x1f',
        r.id::text,
        to_char(r.tijdstip AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
        coalesce(r.usecase, ''), coalesce(r.functie, ''), coalesce(r.status, ''), coalesce(r.taak, ''),
        coalesce(array_to_string(r.bronnen, ','), ''), coalesce(r.model, ''), coalesce(r.modelversie, ''),
        coalesce(r.app_versie, ''), coalesce(r.resultaat, ''), coalesce(r.foutmelding, ''),
        coalesce(r.vorige_hash, '')), 'UTF8')), 'hex')
$$;

-- Volgnummer, tijdstip en hash onder één slot: zo volgt elke regel op de vorige, ook bij gelijktijdig schrijven
CREATE OR REPLACE FUNCTION public.ai_logboek_keten() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('omnitwin.ai_logboek'));
    NEW.id := nextval('public.ai_logboek_id_seq');
    NEW.tijdstip := clock_timestamp();
    NEW.vorige_hash := (SELECT l.hash FROM public.ai_logboek l ORDER BY l.id DESC LIMIT 1);
    NEW.hash := public.ai_logboek_regelhash(NEW);
    RETURN NEW;
END
$$;

CREATE OR REPLACE FUNCTION public.ai_alleen_toevoegen() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'ai_logboek' AND TG_OP = 'DELETE' AND current_user = 'omnitwin_ai_log_opschoner' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION '% is alleen-toevoegen: % is niet toegestaan', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'insufficient_privilege';
END
$$;

DROP TRIGGER IF EXISTS ai_logboek_keten ON public.ai_logboek;
CREATE TRIGGER ai_logboek_keten BEFORE INSERT ON public.ai_logboek
    FOR EACH ROW EXECUTE FUNCTION public.ai_logboek_keten();
DROP TRIGGER IF EXISTS ai_logboek_bewaak ON public.ai_logboek;
CREATE TRIGGER ai_logboek_bewaak BEFORE UPDATE OR DELETE ON public.ai_logboek
    FOR EACH ROW EXECUTE FUNCTION public.ai_alleen_toevoegen();
DROP TRIGGER IF EXISTS ai_logboek_geen_truncate ON public.ai_logboek;
CREATE TRIGGER ai_logboek_geen_truncate BEFORE TRUNCATE ON public.ai_logboek
    FOR EACH STATEMENT EXECUTE FUNCTION public.ai_alleen_toevoegen();
DROP TRIGGER IF EXISTS ai_vrijgave_log_bewaak ON public.ai_vrijgave_log;
CREATE TRIGGER ai_vrijgave_log_bewaak BEFORE UPDATE OR DELETE ON public.ai_vrijgave_log
    FOR EACH ROW EXECUTE FUNCTION public.ai_alleen_toevoegen();
DROP TRIGGER IF EXISTS ai_vrijgave_log_geen_truncate ON public.ai_vrijgave_log;
CREATE TRIGGER ai_vrijgave_log_geen_truncate BEFORE TRUNCATE ON public.ai_vrijgave_log
    FOR EACH STATEMENT EXECUTE FUNCTION public.ai_alleen_toevoegen();

-- Opschonen na de bewaartermijn: alleen een aaneengesloten begin van de keten, en het opschonen
-- komt zelf als regel in het logboek
CREATE OR REPLACE FUNCTION public.ai_logboek_opschonen(p_app_versie text DEFAULT NULL) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
    dagen  integer;
    tot_id bigint;
    n      integer;
BEGIN
    SELECT bewaartermijn_dagen INTO dagen FROM public.ai_instellingen WHERE id;
    dagen := coalesce(dagen, 365);
    PERFORM pg_advisory_xact_lock(hashtext('omnitwin.ai_logboek'));
    SELECT max(id) INTO tot_id FROM public.ai_logboek
     WHERE tijdstip < now() - make_interval(days => dagen);
    IF tot_id IS NULL THEN
        RETURN 0;
    END IF;
    DELETE FROM public.ai_logboek WHERE id <= tot_id;
    GET DIAGNOSTICS n = ROW_COUNT;
    INSERT INTO public.ai_logboek (usecase, functie, status, taak, resultaat, app_versie)
    VALUES ('-', 'opschonen', 'opgeschoond', format('Opschonen na de bewaartermijn van %s dagen', dagen),
            format('%s regels verwijderd, tot en met id %s', n, tot_id), p_app_versie);
    RETURN n;
END
$$;

-- ── Rechten ──────────────────────────────────────────────────────────────────
REVOKE ALL ON public.ai_logboek FROM PUBLIC;
REVOKE ALL ON SEQUENCE public.ai_logboek_id_seq FROM PUBLIC;
REVOKE ALL ON public.ai_vrijgave_log FROM PUBLIC;
-- Ook de eigenaar (en wie lid is, zoals omnitwin_openbaar) niet wijzigen of verwijderen
DO $$
BEGIN
    EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON public.ai_logboek FROM %I', current_user);
    EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON public.ai_vrijgave_log FROM %I', current_user);
END
$$;

GRANT USAGE ON SCHEMA public TO omnitwin_ai_log, omnitwin_ai_log_opschoner;
GRANT SELECT, INSERT ON public.ai_logboek TO omnitwin_ai_log;
GRANT USAGE ON SEQUENCE public.ai_logboek_id_seq TO omnitwin_ai_log, omnitwin_ai_log_opschoner;
GRANT SELECT, INSERT, DELETE ON public.ai_logboek TO omnitwin_ai_log_opschoner;
GRANT SELECT ON public.ai_instellingen TO omnitwin_ai_log_opschoner;

ALTER FUNCTION public.ai_logboek_opschonen(text) OWNER TO omnitwin_ai_log_opschoner;
REVOKE ALL ON FUNCTION public.ai_logboek_opschonen(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.ai_logboek_opschonen(text) TO omnitwin_ai_log;
