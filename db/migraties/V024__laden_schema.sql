-- Laad-API (#205, stap 2): schema laden voor registraties, leveringen, versies en fouten,
-- de stagingtabellen per profiel en de rol laden_schrijver. Idempotent.
--
-- Specificatie: docs/api/laden/openapi.yaml. De backend (omnitwin.laden) schrijft hier en in de
-- doeltabellen (gebied_data, gebieden, indicatoren, ...) met SET LOCAL ROLE laden_schrijver,
-- zodat de laadstraat niet meer kan dan laden.
--
-- Staging: een levering wordt in één transactie in de stagingtabel gezet, gecontroleerd,
-- gepubliceerd en weer uit de staging verwijderd. Andere sessies zien de stagingrijen nooit.
--
-- laden.waarnemingen: de gepubliceerde inhoud per dataset (profiel waarnemingen). gebied_data
-- is daarvan de samengevoegde weergave: bij twee datasets op dezelfde sleutel gaat de dataset
-- met voorrang voor (LADEN_VOORRANG); de andere waarde blijft hier zichtbaar.

CREATE SCHEMA IF NOT EXISTS laden;
COMMENT ON SCHEMA laden IS 'Laad-API (/api/laden/v1): registraties, leveringen, versies, staging (#205)';

-- ── Registraties ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS laden.datasets (
    id              text        PRIMARY KEY CHECK (id ~ '^[a-z0-9]+(-[a-z0-9]+)*$' AND length(id) BETWEEN 3 AND 63),
    bron_id         text,
    beschrijving    jsonb       NOT NULL,                 -- DCAT-AP-NL / GeoDCAT-AP (JSON-LD)
    laadprofiel     jsonb       NOT NULL,                 -- Laadprofiel uit de specificatie
    profiel         text        NOT NULL CHECK (profiel IN ('waarnemingen', 'definities', 'gebiedsindeling', 'kaartlaag')),
    actief          boolean     NOT NULL DEFAULT true,
    huidige_versie  integer,
    kaartlaag_id    integer,                              -- profiel kaartlaag: rij in externe_kaartlagen
    aangemaakt_op   timestamptz NOT NULL DEFAULT now(),
    gewijzigd_op    timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE laden.datasets IS 'Geregistreerde datasets (POST /api/laden/v1/datasets)';

-- ── Leveringen ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS laden.leveringen (
    id               uuid        PRIMARY KEY,
    dataset_id       text        NOT NULL REFERENCES laden.datasets(id) ON DELETE RESTRICT,
    status           text        NOT NULL DEFAULT 'ontvangen'
                                 CHECK (status IN ('ontvangen', 'bezig', 'gevalideerd', 'gepubliceerd', 'afgekeurd', 'mislukt')),
    modus            text        NOT NULL DEFAULT 'vervangen' CHECK (modus IN ('vervangen')),
    alleen_valideren boolean     NOT NULL DEFAULT false,
    idempotency_key  text        CHECK (length(idempotency_key) <= 255),
    sha256           text        NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
    bestandsnaam     text        NOT NULL,
    mediatype        text        NOT NULL,
    grootte          bigint      NOT NULL,
    dcat             jsonb,                               -- meegeleverde dcat.jsonld (multipart-deel of in de zip)
    client_id        text,
    ontvangen_op     timestamptz NOT NULL DEFAULT now(),
    gestart_op       timestamptz,
    klaar_op         timestamptz,
    aantallen        jsonb       NOT NULL DEFAULT '{}'::jsonb,
    versie           integer,
    fouten_aantal    integer     NOT NULL DEFAULT 0,
    bestand_verwijderd_op timestamptz                     -- bewaartermijn verstreken (laden.opslag)
);
COMMENT ON TABLE laden.leveringen IS 'Leveringen (POST /api/laden/v1/datasets/{id}/leveringen); het ruwe bestand staat op het volume leveringen';
-- Idempotency-Key is uniek per dataset; na 7 dagen maakt de laadstraat hem vrij (NULL)
CREATE UNIQUE INDEX IF NOT EXISTS leveringen_idempotency_key_uniek
    ON laden.leveringen (dataset_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS leveringen_dataset_ontvangen ON laden.leveringen (dataset_id, ontvangen_op DESC);
CREATE INDEX IF NOT EXISTS leveringen_status ON laden.leveringen (status) WHERE status IN ('ontvangen', 'bezig');

-- ── Versies ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS laden.versies (
    dataset_id      text        NOT NULL REFERENCES laden.datasets(id) ON DELETE RESTRICT,
    versie          integer     NOT NULL CHECK (versie > 0),
    levering_id     uuid        NOT NULL REFERENCES laden.leveringen(id),   -- de levering die deze versie maakte
    levering_ids    uuid[]      NOT NULL,                                   -- alle leveringen waaruit de versie bestaat
    gepubliceerd_op timestamptz NOT NULL DEFAULT now(),
    actief          boolean     NOT NULL DEFAULT false,
    aantal_regels   integer     NOT NULL DEFAULT 0,
    PRIMARY KEY (dataset_id, versie)
);
COMMENT ON TABLE laden.versies IS 'Gepubliceerde versies per dataset; precies één actief';
CREATE UNIQUE INDEX IF NOT EXISTS versies_een_actief ON laden.versies (dataset_id) WHERE actief;

-- ── Fouten per levering (Problem Details; de waarde uit de regel wordt niet bewaard) ─
CREATE TABLE IF NOT EXISTS laden.fouten (
    id          bigserial   PRIMARY KEY,
    levering_id uuid        NOT NULL REFERENCES laden.leveringen(id) ON DELETE CASCADE,
    resource    text,
    regel       integer,
    veld        text,
    code        text        NOT NULL,
    melding     text        NOT NULL
);
CREATE INDEX IF NOT EXISTS fouten_levering ON laden.fouten (levering_id, id);

-- ── Wat een dataset met profiel definities geleverd heeft (voor "ontbreekt in de set") ─
CREATE TABLE IF NOT EXISTS laden.dataset_objecten (
    dataset_id  text NOT NULL REFERENCES laden.datasets(id) ON DELETE CASCADE,
    soort       text NOT NULL CHECK (soort IN ('indicator', 'gebiedstype', 'relatie')),
    sleutel     text NOT NULL,
    PRIMARY KEY (dataset_id, soort, sleutel)
);

-- ── Gepubliceerde waarnemingen per dataset ───────────────────────────────────
CREATE TABLE IF NOT EXISTS laden.waarnemingen (
    dataset_id      text        NOT NULL REFERENCES laden.datasets(id) ON DELETE RESTRICT,
    levering_id     uuid        NOT NULL REFERENCES laden.leveringen(id),
    gebied_id       varchar(100) NOT NULL,
    gebiedstype_id  uuid        NOT NULL,
    indicator_uuid  uuid        NOT NULL,
    jaar            integer,
    datum           timestamp,
    scenario_id     varchar(50) NOT NULL DEFAULT 'current',
    waarde          numeric     NOT NULL,
    n               integer,
    n_status        text        NOT NULL CHECK (n_status IN ('gemeten', 'bron-onderdrukt')),
    kwaliteit       varchar(20),
    bron            varchar(255),
    opmerking       varchar(500),
    metadata        jsonb,
    gepubliceerd_op timestamptz NOT NULL DEFAULT now(),
    CHECK ((jaar IS NULL) <> (datum IS NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS waarnemingen_sleutel ON laden.waarnemingen
    (dataset_id, gebied_id, indicator_uuid, COALESCE(jaar, -1), COALESCE(datum, '-infinity'::timestamp), scenario_id);
CREATE INDEX IF NOT EXISTS waarnemingen_gebied_data_sleutel ON laden.waarnemingen (gebied_id, indicator_uuid, jaar, scenario_id);
CREATE INDEX IF NOT EXISTS waarnemingen_bereik ON laden.waarnemingen (dataset_id, indicator_uuid, gebiedstype_id);
CREATE INDEX IF NOT EXISTS waarnemingen_levering ON laden.waarnemingen (levering_id);

-- ── Staging per profiel (alleen binnen de transactie van één levering gevuld) ─
CREATE TABLE IF NOT EXISTS laden.staging_waarnemingen (
    levering_id     uuid        NOT NULL,
    regel           integer     NOT NULL,
    gebied_code     varchar(100) NOT NULL,
    gebiedstype     varchar(50),
    gebiedstype_id  uuid,                 -- na controle: het gebiedstype van het gebied
    indicator_uuid  uuid        NOT NULL,
    jaar            integer,
    datum           timestamp,
    scenario_id     varchar(50) NOT NULL,
    waarde          numeric     NOT NULL,
    n               integer,
    n_status        text        NOT NULL,  -- gemeten | bron-onderdrukt | onderdrukt
    kwaliteit       varchar(20),
    bron            varchar(255),
    opmerking       varchar(500),
    metadata        jsonb
);
CREATE INDEX IF NOT EXISTS staging_waarnemingen_levering ON laden.staging_waarnemingen (levering_id);

CREATE TABLE IF NOT EXISTS laden.staging_indicatoren (
    levering_id     uuid    NOT NULL,
    regel           integer NOT NULL,
    uuid            uuid    NOT NULL,
    naam            varchar(255) NOT NULL,
    code            varchar(50),
    omschrijving    text,
    eenheid         varchar(50),
    score_type      varchar(10),
    min_waarde      numeric,
    max_waarde      numeric,
    status          varchar(20),
    begingeldigheid timestamp,
    eindgeldigheid  timestamp,
    bron            varchar(255)
);
CREATE TABLE IF NOT EXISTS laden.staging_gebiedstypen (
    levering_id     uuid    NOT NULL,
    regel           integer NOT NULL,
    id              uuid    NOT NULL,
    naam            varchar(255) NOT NULL,
    code            varchar(50),
    niveau          varchar(50),
    actief          boolean,
    metadata        jsonb
);
CREATE TABLE IF NOT EXISTS laden.staging_relaties (
    levering_id     uuid    NOT NULL,
    regel           integer NOT NULL,
    indicator_uuid  uuid    NOT NULL,
    gebiedstype_id  uuid    NOT NULL
);
CREATE TABLE IF NOT EXISTS laden.staging_gebieden (
    levering_id     uuid    NOT NULL,
    regel           integer NOT NULL,
    id              varchar(100) NOT NULL,
    naam            varchar(255) NOT NULL,
    gemeente_code   varchar(4),
    actief          boolean NOT NULL DEFAULT true,
    metadata        jsonb,
    geom            public.geometry(MultiPolygon, 28992) NOT NULL
);

-- ── Rol laden_schrijver: alleen wat de laadstraat nodig heeft ────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'laden_schrijver') THEN
        CREATE ROLE laden_schrijver NOLOGIN;
    END IF;
END
$$;
ALTER ROLE laden_schrijver NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

-- De database-eigenaar (die db-init en de backend draait) mag naar deze rol schakelen
DO $$
BEGIN
    IF NOT pg_has_role(current_user, 'laden_schrijver', 'MEMBER') THEN
        EXECUTE format('GRANT laden_schrijver TO %I', current_user);
    END IF;
END
$$;

REVOKE ALL ON SCHEMA laden FROM PUBLIC;
GRANT USAGE ON SCHEMA laden TO laden_schrijver;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA laden TO laden_schrijver;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA laden TO laden_schrijver;

-- Doeltabellen: lezen voor de controles, schrijven voor de publicatie
GRANT USAGE ON SCHEMA public TO laden_schrijver;
GRANT SELECT ON public.gemeenten TO laden_schrijver;
GRANT SELECT, INSERT, UPDATE, DELETE ON
    public.gebied_data,
    public.gebieden,
    public.gebiedstypes,
    public.indicatoren,
    public.indicator_gebiedstype_relaties,
    public.externe_kaartlagen
TO laden_schrijver;
GRANT USAGE ON SEQUENCE public.gebied_data_id_seq, public.indicatoren_id_seq, public.externe_kaartlagen_id_seq
TO laden_schrijver;
