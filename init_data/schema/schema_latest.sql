--
-- PostgreSQL database dump
--

\restrict 3gy4bFeI4foWARkSZje9qygwfD5dXKLhbefeqXjBiK82y7d3LZ316oAy286Aj2c

-- Dumped from database version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: update_gebied_centroid(); Type: FUNCTION; Schema: public; Owner: omnitwin_user
--

CREATE FUNCTION public.update_gebied_centroid() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.geom IS NOT NULL THEN
        NEW.geom_centroid = ST_Centroid(NEW.geom);
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_gebied_centroid() OWNER TO omnitwin_user;

--
-- Name: update_llm_config_modtime(); Type: FUNCTION; Schema: public; Owner: omnitwin_user
--

CREATE FUNCTION public.update_llm_config_modtime() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.bijgewerkt_op = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_llm_config_modtime() OWNER TO omnitwin_user;

--
-- Name: update_system_prompts_mod_time(); Type: FUNCTION; Schema: public; Owner: omnitwin_user
--

CREATE FUNCTION public.update_system_prompts_mod_time() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.laatst_gewijzigd = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_system_prompts_mod_time() OWNER TO omnitwin_user;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: omnitwin_user
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO omnitwin_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: app_logs; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.app_logs (
    id bigint NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    level character varying(10) NOT NULL,
    category character varying(50) NOT NULL,
    message text NOT NULL,
    user_id character varying(255),
    session_id character varying(255),
    ip_address character varying(45),
    endpoint character varying(255),
    response_time_ms integer,
    extra jsonb
);


ALTER TABLE public.app_logs OWNER TO omnitwin_user;

--
-- Name: app_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.app_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.app_logs_id_seq OWNER TO omnitwin_user;

--
-- Name: app_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.app_logs_id_seq OWNED BY public.app_logs.id;


--
-- Name: chat_scenarios; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.chat_scenarios (
    id integer NOT NULL,
    rol_code character varying(50) NOT NULL,
    rol_naam character varying(100) NOT NULL,
    beschrijving text,
    narrative text NOT NULL,
    acties jsonb DEFAULT '[]'::jsonb,
    trigger_keywords jsonb DEFAULT '[]'::jsonb,
    is_actief boolean DEFAULT true,
    volgorde integer DEFAULT 0
);


ALTER TABLE public.chat_scenarios OWNER TO omnitwin_user;

--
-- Name: chat_scenarios_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.chat_scenarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_scenarios_id_seq OWNER TO omnitwin_user;

--
-- Name: chat_scenarios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.chat_scenarios_id_seq OWNED BY public.chat_scenarios.id;


--
-- Name: color_schemas; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.color_schemas (
    id integer NOT NULL,
    naam character varying(100) NOT NULL,
    beschrijving text,
    colors jsonb NOT NULL,
    is_actief boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    palette_type character varying(20) DEFAULT 'sequential'::character varying,
    classificatie character varying(30) DEFAULT 'quantile'::character varying,
    klassen integer DEFAULT 5,
    nodata_kleur character varying(7) DEFAULT '#d1d5db'::character varying,
    CONSTRAINT color_schemas_classificatie_check CHECK (((classificatie)::text = ANY ((ARRAY['quantile'::character varying, 'jenks'::character varying, 'equal_interval'::character varying, 'diverging_midpoint'::character varying])::text[]))),
    CONSTRAINT color_schemas_klassen_check CHECK (((klassen >= 3) AND (klassen <= 7))),
    CONSTRAINT color_schemas_palette_type_check CHECK (((palette_type)::text = ANY ((ARRAY['sequential'::character varying, 'diverging'::character varying, 'qualitative'::character varying])::text[])))
);


ALTER TABLE public.color_schemas OWNER TO omnitwin_user;

--
-- Name: color_schemas_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.color_schemas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.color_schemas_id_seq OWNER TO omnitwin_user;

--
-- Name: color_schemas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.color_schemas_id_seq OWNED BY public.color_schemas.id;


--
-- Name: externe_kaartlagen; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.externe_kaartlagen (
    id integer NOT NULL,
    naam character varying(100) NOT NULL,
    beschrijving text,
    laag_type character varying(20) DEFAULT 'selectie'::character varying NOT NULL,
    bron_type character varying(20) DEFAULT 'WFS'::character varying NOT NULL,
    url text NOT NULL,
    typename character varying(100),
    srsname character varying(20) DEFAULT 'EPSG:28992'::character varying,
    versie character varying(10) DEFAULT '2.0.0'::character varying,
    filter_type character varying(20) DEFAULT 'provincie'::character varying,
    filter_waarde text,
    koppel_veld character varying(100),
    kleur_lijn character varying(7) DEFAULT '#8B5CF6'::character varying,
    kleur_fill character varying(7) DEFAULT '#8B5CF6'::character varying,
    opacity real DEFAULT 0.15,
    actief boolean DEFAULT true,
    volgorde integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT externe_kaartlagen_bron_type_check CHECK (((bron_type)::text = ANY ((ARRAY['WFS'::character varying, 'WMS'::character varying, 'GeoJSON'::character varying, 'lokaal'::character varying])::text[]))),
    CONSTRAINT externe_kaartlagen_filter_type_check CHECK (((filter_type)::text = ANY ((ARRAY['bbox'::character varying, 'provincie'::character varying, 'alles'::character varying])::text[]))),
    CONSTRAINT externe_kaartlagen_laag_type_check CHECK (((laag_type)::text = ANY ((ARRAY['selectie'::character varying, 'data_koppel'::character varying])::text[]))),
    CONSTRAINT externe_kaartlagen_opacity_check CHECK (((opacity >= (0)::double precision) AND (opacity <= (1)::double precision)))
);


ALTER TABLE public.externe_kaartlagen OWNER TO omnitwin_user;

--
-- Name: externe_kaartlagen_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.externe_kaartlagen_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.externe_kaartlagen_id_seq OWNER TO omnitwin_user;

--
-- Name: externe_kaartlagen_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.externe_kaartlagen_id_seq OWNED BY public.externe_kaartlagen.id;


--
-- Name: gebied_data; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.gebied_data (
    id bigint NOT NULL,
    gebied_id character varying(100) NOT NULL,
    indicator_uuid uuid NOT NULL,
    waarde numeric NOT NULL,
    jaar integer,
    datum timestamp without time zone,
    scenario_id character varying(50) DEFAULT 'current'::character varying,
    bron character varying(255),
    kwaliteit character varying(20),
    metadata jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_jaar_of_datum CHECK ((((jaar IS NOT NULL) AND (datum IS NULL)) OR ((jaar IS NULL) AND (datum IS NOT NULL))))
);


ALTER TABLE public.gebied_data OWNER TO omnitwin_user;

--
-- Name: TABLE gebied_data; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.gebied_data IS 'Feitelijke metingen/waarden per gebied en indicator';


--
-- Name: COLUMN gebied_data.scenario_id; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.gebied_data.scenario_id IS 'Scenario identifier voor toekomstprojecties (current, 2030, 2050, etc.)';


--
-- Name: gebied_data_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.gebied_data_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gebied_data_id_seq OWNER TO omnitwin_user;

--
-- Name: gebied_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.gebied_data_id_seq OWNED BY public.gebied_data.id;


--
-- Name: gebieden; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.gebieden (
    id character varying(100) NOT NULL,
    gebiedstype_id uuid NOT NULL,
    naam character varying(255) NOT NULL,
    geom public.geometry(MultiPolygon,28992),
    geom_centroid public.geometry(Point,28992),
    metadata jsonb,
    actief boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    gemeente_code character varying(4),
    provincienaam character varying(50)
);


ALTER TABLE public.gebieden OWNER TO omnitwin_user;

--
-- Name: TABLE gebieden; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.gebieden IS 'Specifieke gebieden met hun geometrie en metadata';


--
-- Name: COLUMN gebieden.geom; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.gebieden.geom IS 'Geometrie in RD New (EPSG:28992) coördinatensysteem';


--
-- Name: COLUMN gebieden.geom_centroid; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.gebieden.geom_centroid IS 'Automatisch berekend zwaartepunt voor kaartweergave';


--
-- Name: COLUMN gebieden.gemeente_code; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.gebieden.gemeente_code IS 'CBS gemeente code waar dit gebied toe behoort';


--
-- Name: COLUMN gebieden.provincienaam; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.gebieden.provincienaam IS 'Naam van de provincie (bijv. Fryslân)';


--
-- Name: gebiedstypes; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.gebiedstypes (
    id uuid NOT NULL,
    naam character varying(255) NOT NULL,
    code character varying(50),
    beschrijving text,
    bron character varying(255),
    niveau character varying(50),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.gebiedstypes OWNER TO omnitwin_user;

--
-- Name: TABLE gebiedstypes; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.gebiedstypes IS 'Verschillende soorten gebiedsindelingen (CBS buurten, wijken, welstandsgebieden, etc.)';


--
-- Name: gemeenten; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.gemeenten (
    code character varying(4) NOT NULL,
    naam character varying(100) NOT NULL,
    provincie character varying(50) NOT NULL,
    is_eiland boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.gemeenten OWNER TO omnitwin_user;

--
-- Name: TABLE gemeenten; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.gemeenten IS 'Nederlandse gemeenten met CBS codes, initieel gevuld met Friese gemeenten';


--
-- Name: COLUMN gemeenten.code; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.gemeenten.code IS '4-cijferige CBS gemeente code (bijv. 1900 voor Súdwest-Fryslân)';


--
-- Name: COLUMN gemeenten.is_eiland; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.gemeenten.is_eiland IS 'TRUE voor eilandgemeenten (Ameland, Schiermonnikoog, Terschelling, Vlieland)';


--
-- Name: indicator_embeddings; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.indicator_embeddings (
    id integer NOT NULL,
    indicator_uuid uuid NOT NULL,
    embedding public.vector(384),
    model_naam character varying(100) DEFAULT 'all-MiniLM-L6-v2'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.indicator_embeddings OWNER TO omnitwin_user;

--
-- Name: TABLE indicator_embeddings; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.indicator_embeddings IS 'Vectoren voor semantisch zoeken in het Kompas';


--
-- Name: indicator_embeddings_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.indicator_embeddings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.indicator_embeddings_id_seq OWNER TO omnitwin_user;

--
-- Name: indicator_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.indicator_embeddings_id_seq OWNED BY public.indicator_embeddings.id;


--
-- Name: indicator_gebiedstype_relaties; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.indicator_gebiedstype_relaties (
    indicator_uuid uuid NOT NULL,
    gebiedstype_id uuid NOT NULL,
    verplicht boolean DEFAULT false,
    display_volgorde integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.indicator_gebiedstype_relaties OWNER TO omnitwin_user;

--
-- Name: TABLE indicator_gebiedstype_relaties; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.indicator_gebiedstype_relaties IS 'Koppeltabel tussen indicatoren en gebiedstypes';


--
-- Name: indicatoren; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.indicatoren (
    id integer NOT NULL,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    naam character varying(255) NOT NULL,
    code character varying(50),
    omschrijving text,
    eenheid character varying(50),
    interpretatie_logica character varying(20) DEFAULT 'pos_is_pos'::character varying,
    min_waarde numeric,
    max_waarde numeric,
    bron character varying(255),
    status character varying(20) DEFAULT 'O'::character varying,
    begingeldigheid timestamp without time zone,
    eindgeldigheid timestamp without time zone,
    categorie character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    score_type character varying(10) DEFAULT '+/+'::character varying,
    color_schema_id integer DEFAULT 1,
    admin_notes text,
    bron_systeem_api character varying(255),
    bron_tabel_referentie character varying(255),
    laatste_update_bron timestamp without time zone,
    laatste_check_datum timestamp without time zone,
    waarde_type character varying(50) DEFAULT 'decimal'::character varying,
    ontologische_beschrijving text,
    ontologie_status character varying(50) DEFAULT 'draft'::character varying,
    ontologie_beoordeeld_door character varying(100),
    ontologie_beoordeeld_op timestamp without time zone,
    beschrijving_ai text,
    gevalideerd_door uuid,
    gevalideerd_op timestamp with time zone,
    embedding_versie text
);


ALTER TABLE public.indicatoren OWNER TO omnitwin_user;

--
-- Name: TABLE indicatoren; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.indicatoren IS 'KPI''s en meetwaarden met uitgebreide metadata voor gebiedsmonitor';


--
-- Name: COLUMN indicatoren.status; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.status IS 'C=Concept, O=Operationeel, B=Beëindigd';


--
-- Name: COLUMN indicatoren.bron_systeem_api; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.bron_systeem_api IS 'Type bron systeem of API (bijv. CBS OData, BAG API, RIVM)';


--
-- Name: COLUMN indicatoren.bron_tabel_referentie; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.bron_tabel_referentie IS 'Specifieke tabelnaam, dataset code of URL endpoint bij de bron';


--
-- Name: COLUMN indicatoren.laatste_update_bron; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.laatste_update_bron IS 'Datum/tijd wanneer de data voor het laatst is bijgewerkt bij de bron zelf';


--
-- Name: COLUMN indicatoren.laatste_check_datum; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.laatste_check_datum IS 'Wanneer ons systeem voor het laatst heeft gecontroleerd op updates bij de bron';


--
-- Name: COLUMN indicatoren.waarde_type; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.waarde_type IS 'Het datatype van de waarde (decimal, integer, percentage, text)';


--
-- Name: COLUMN indicatoren.ontologische_beschrijving; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.ontologische_beschrijving IS 'Formele beschrijving voor AI en semantisch zoeken';


--
-- Name: COLUMN indicatoren.ontologie_status; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.ontologie_status IS 'Status van de ontologie (draft, beoordeeld_ai, goedgekeurd_mens)';


--
-- Name: COLUMN indicatoren.beschrijving_ai; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.beschrijving_ai IS 'Originele AI-gegenereerde beschrijving (read-only referentie)';


--
-- Name: COLUMN indicatoren.gevalideerd_door; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.gevalideerd_door IS 'User ID van de beheerder die de ontologie heeft goedgekeurd';


--
-- Name: COLUMN indicatoren.gevalideerd_op; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.gevalideerd_op IS 'Tijdstip van laatste goedkeuring';


--
-- Name: COLUMN indicatoren.embedding_versie; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.indicatoren.embedding_versie IS 'Hash/versie van de embedding (verandert bij herberekening)';


--
-- Name: indicatoren_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.indicatoren_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.indicatoren_id_seq OWNER TO omnitwin_user;

--
-- Name: indicatoren_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.indicatoren_id_seq OWNED BY public.indicatoren.id;


--
-- Name: kompas_configuraties; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.kompas_configuraties (
    id integer NOT NULL,
    naam character varying(150) NOT NULL,
    beschrijving text,
    is_standaard boolean DEFAULT false,
    is_actief boolean DEFAULT true,
    icoon character varying(50) DEFAULT '🌍'::character varying,
    versie integer DEFAULT 1,
    created_by character varying(100),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.kompas_configuraties OWNER TO omnitwin_user;

--
-- Name: TABLE kompas_configuraties; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.kompas_configuraties IS 'Master configuraties voor meerdere kompas varianten';


--
-- Name: COLUMN kompas_configuraties.is_standaard; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.kompas_configuraties.is_standaard IS 'Standaard kompas voor nieuwe gebruikers (slechts 1 kan TRUE zijn)';


--
-- Name: COLUMN kompas_configuraties.is_actief; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.kompas_configuraties.is_actief IS 'Kan worden gebruikt om kompassen tijdelijk uit te schakelen';


--
-- Name: kompas_configuraties_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.kompas_configuraties_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kompas_configuraties_id_seq OWNER TO omnitwin_user;

--
-- Name: kompas_configuraties_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.kompas_configuraties_id_seq OWNED BY public.kompas_configuraties.id;


--
-- Name: kompas_extra_onderdelen; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.kompas_extra_onderdelen (
    id integer NOT NULL,
    naam character varying(100) NOT NULL,
    beschrijving text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.kompas_extra_onderdelen OWNER TO omnitwin_user;

--
-- Name: TABLE kompas_extra_onderdelen; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.kompas_extra_onderdelen IS 'Niveau 4 van Kompas hiërarchie - Optionele tags (Hitte, Wateroverlast, etc.)';


--
-- Name: kompas_extra_onderdelen_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.kompas_extra_onderdelen_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kompas_extra_onderdelen_id_seq OWNER TO omnitwin_user;

--
-- Name: kompas_extra_onderdelen_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.kompas_extra_onderdelen_id_seq OWNED BY public.kompas_extra_onderdelen.id;


--
-- Name: kompas_indicator_extra_tags; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.kompas_indicator_extra_tags (
    indicator_uuid uuid NOT NULL,
    extra_onderdeel_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.kompas_indicator_extra_tags OWNER TO omnitwin_user;

--
-- Name: TABLE kompas_indicator_extra_tags; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.kompas_indicator_extra_tags IS 'Many-to-many koppeling voor extra tags per indicator';


--
-- Name: kompas_indicator_mapping; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.kompas_indicator_mapping (
    id integer NOT NULL,
    indicator_uuid uuid NOT NULL,
    onderdeel_id integer NOT NULL,
    weging double precision DEFAULT 1.0,
    is_actueel boolean DEFAULT false,
    indicator_swf character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    config_id integer NOT NULL
);


ALTER TABLE public.kompas_indicator_mapping OWNER TO omnitwin_user;

--
-- Name: TABLE kompas_indicator_mapping; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.kompas_indicator_mapping IS 'Koppeling tussen indicatoren en de Kompas hiërarchie';


--
-- Name: COLUMN kompas_indicator_mapping.weging; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.kompas_indicator_mapping.weging IS 'Gewicht voor percentiel-aggregatie berekening (default = 1.0)';


--
-- Name: kompas_indicator_mapping_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.kompas_indicator_mapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kompas_indicator_mapping_id_seq OWNER TO omnitwin_user;

--
-- Name: kompas_indicator_mapping_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.kompas_indicator_mapping_id_seq OWNED BY public.kompas_indicator_mapping.id;


--
-- Name: kompas_indicator_scoring_regels; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.kompas_indicator_scoring_regels (
    id integer NOT NULL,
    indicator_uuid uuid NOT NULL,
    config_id integer NOT NULL,
    score_type character varying(50) NOT NULL,
    thresholds jsonb,
    inverse boolean DEFAULT false,
    eenheid character varying(50),
    doel_waarde double precision,
    beschrijving text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT kompas_indicator_scoring_regels_score_type_check CHECK (((score_type)::text = ANY ((ARRAY['positive_ascending'::character varying, 'positive_descending'::character varying, 'threshold_based'::character varying, 'custom'::character varying])::text[])))
);


ALTER TABLE public.kompas_indicator_scoring_regels OWNER TO omnitwin_user;

--
-- Name: TABLE kompas_indicator_scoring_regels; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.kompas_indicator_scoring_regels IS 'Kleur- en interpretatie regels per indicator per kompas';


--
-- Name: COLUMN kompas_indicator_scoring_regels.score_type; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.kompas_indicator_scoring_regels.score_type IS 'Type scoring: positive_ascending, positive_descending, threshold_based, custom';


--
-- Name: COLUMN kompas_indicator_scoring_regels.thresholds; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.kompas_indicator_scoring_regels.thresholds IS 'JSONB drempelwaarden voor threshold_based type';


--
-- Name: COLUMN kompas_indicator_scoring_regels.inverse; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON COLUMN public.kompas_indicator_scoring_regels.inverse IS 'Inverteer gradient kleuren (voor descending types)';


--
-- Name: kompas_indicator_scoring_regels_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.kompas_indicator_scoring_regels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kompas_indicator_scoring_regels_id_seq OWNER TO omnitwin_user;

--
-- Name: kompas_indicator_scoring_regels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.kompas_indicator_scoring_regels_id_seq OWNED BY public.kompas_indicator_scoring_regels.id;


--
-- Name: kompas_onderdelen; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.kompas_onderdelen (
    id integer NOT NULL,
    thema_id integer NOT NULL,
    naam character varying(150) NOT NULL,
    volgorde integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.kompas_onderdelen OWNER TO omnitwin_user;

--
-- Name: TABLE kompas_onderdelen; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.kompas_onderdelen IS 'Niveau 3 van Kompas hiërarchie - Onderdelen per thema';


--
-- Name: kompas_onderdelen_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.kompas_onderdelen_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kompas_onderdelen_id_seq OWNER TO omnitwin_user;

--
-- Name: kompas_onderdelen_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.kompas_onderdelen_id_seq OWNED BY public.kompas_onderdelen.id;


--
-- Name: kompas_themas; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.kompas_themas (
    id integer NOT NULL,
    titel_id integer NOT NULL,
    naam character varying(150) NOT NULL,
    volgorde integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.kompas_themas OWNER TO omnitwin_user;

--
-- Name: TABLE kompas_themas; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.kompas_themas IS 'Niveau 2 van Kompas hiërarchie - Thema''s per titel';


--
-- Name: kompas_themas_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.kompas_themas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kompas_themas_id_seq OWNER TO omnitwin_user;

--
-- Name: kompas_themas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.kompas_themas_id_seq OWNED BY public.kompas_themas.id;


--
-- Name: kompas_titels; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.kompas_titels (
    id integer NOT NULL,
    naam character varying(150) NOT NULL,
    kleur character varying(7) DEFAULT '#3B82F6'::character varying,
    volgorde integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    config_id integer NOT NULL
);


ALTER TABLE public.kompas_titels OWNER TO omnitwin_user;

--
-- Name: TABLE kompas_titels; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON TABLE public.kompas_titels IS 'Niveau 1 van Kompas hiërarchie - Hoofd categorieën';


--
-- Name: kompas_titels_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.kompas_titels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kompas_titels_id_seq OWNER TO omnitwin_user;

--
-- Name: kompas_titels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.kompas_titels_id_seq OWNED BY public.kompas_titels.id;


--
-- Name: llm_config; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.llm_config (
    id integer NOT NULL,
    api_url character varying(255) DEFAULT 'http://localhost:11434'::character varying NOT NULL,
    model_name character varying(100) DEFAULT 'qwen3:30b'::character varying NOT NULL,
    aangemaakt_op timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    bijgewerkt_op timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.llm_config OWNER TO omnitwin_user;

--
-- Name: llm_config_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.llm_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.llm_config_id_seq OWNER TO omnitwin_user;

--
-- Name: llm_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.llm_config_id_seq OWNED BY public.llm_config.id;


--
-- Name: log_config; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.log_config (
    category character varying(50) NOT NULL,
    level character varying(10) DEFAULT 'INFO'::character varying NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    updated_by character varying(255)
);


ALTER TABLE public.log_config OWNER TO omnitwin_user;

--
-- Name: omgevingsvisie_deelgebieden; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.omgevingsvisie_deelgebieden (
    id integer NOT NULL,
    naam text NOT NULL,
    deelgebied text NOT NULL,
    geom public.geometry(Polygon,28992),
    geom_wgs84 public.geometry(Polygon,4326)
);


ALTER TABLE public.omgevingsvisie_deelgebieden OWNER TO omnitwin_user;

--
-- Name: omgevingsvisie_deelgebieden_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.omgevingsvisie_deelgebieden_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.omgevingsvisie_deelgebieden_id_seq OWNER TO omnitwin_user;

--
-- Name: omgevingsvisie_deelgebieden_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.omgevingsvisie_deelgebieden_id_seq OWNED BY public.omgevingsvisie_deelgebieden.id;


--
-- Name: ov_halte_clusters; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.ov_halte_clusters (
    cluster_id uuid DEFAULT gen_random_uuid() NOT NULL,
    naam text,
    ov_type text,
    n_platforms integer DEFAULT 1,
    gebied_id text,
    gemeente_code text,
    provincie text,
    geom public.geometry(Point,28992),
    peildatum date DEFAULT CURRENT_DATE,
    CONSTRAINT ov_halte_clusters_provincie_check CHECK ((provincie = ANY (ARRAY['FR'::text, 'GR'::text, 'DR'::text])))
);


ALTER TABLE public.ov_halte_clusters OWNER TO omnitwin_user;

--
-- Name: ov_haltes; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.ov_haltes (
    osm_id bigint NOT NULL,
    naam text,
    ov_type text,
    osm_pt_type text,
    network text,
    ref text,
    gemeente_code text,
    gebied_id text,
    provincie text,
    geom public.geometry(Point,28992),
    peildatum date DEFAULT CURRENT_DATE,
    tags jsonb,
    CONSTRAINT ov_haltes_provincie_check CHECK ((provincie = ANY (ARRAY['FR'::text, 'GR'::text, 'DR'::text])))
);


ALTER TABLE public.ov_haltes OWNER TO omnitwin_user;

--
-- Name: ov_haltes_per_buurt; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.ov_haltes_per_buurt (
    gebied_id text NOT NULL,
    jaar integer NOT NULL,
    totaal_haltes integer DEFAULT 0,
    haltes_bus integer DEFAULT 0,
    haltes_tram integer DEFAULT 0,
    haltes_trein integer DEFAULT 0,
    haltes_veerboot integer DEFAULT 0,
    haltes_metro integer DEFAULT 0
);


ALTER TABLE public.ov_haltes_per_buurt OWNER TO omnitwin_user;

--
-- Name: sessions; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.sessions (
    token character varying(255) NOT NULL,
    user_id uuid,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.sessions OWNER TO omnitwin_user;

--
-- Name: system_prompts; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.system_prompts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    naam character varying(100) NOT NULL,
    beschrijving text,
    prompt_text text NOT NULL,
    is_actief boolean DEFAULT true,
    aangemaakt_op timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    laatst_gewijzigd timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.system_prompts OWNER TO omnitwin_user;

--
-- Name: users; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    username character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    is_active boolean DEFAULT true,
    is_admin boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.users OWNER TO omnitwin_user;

--
-- Name: v_kompas_config_stats; Type: VIEW; Schema: public; Owner: omnitwin_user
--

CREATE VIEW public.v_kompas_config_stats AS
 SELECT kc.id,
    kc.naam,
    kc.beschrijving,
    kc.is_standaard,
    kc.is_actief,
    kc.icoon,
    count(DISTINCT kth.id) AS aantal_themas,
    count(DISTINCT ko.id) AS aantal_onderdelen,
    count(DISTINCT kim.indicator_uuid) AS aantal_indicatoren,
    count(sr.id) AS aantal_scoring_regels
   FROM (((((public.kompas_configuraties kc
     LEFT JOIN public.kompas_titels kt ON ((kc.id = kt.config_id)))
     LEFT JOIN public.kompas_themas kth ON ((kt.id = kth.titel_id)))
     LEFT JOIN public.kompas_onderdelen ko ON ((kth.id = ko.thema_id)))
     LEFT JOIN public.kompas_indicator_mapping kim ON (((ko.id = kim.onderdeel_id) AND (kim.config_id = kc.id))))
     LEFT JOIN public.kompas_indicator_scoring_regels sr ON (((kim.indicator_uuid = sr.indicator_uuid) AND (sr.config_id = kc.id))))
  WHERE (kc.is_actief = true)
  GROUP BY kc.id, kc.naam, kc.beschrijving, kc.is_standaard, kc.is_actief, kc.icoon
  ORDER BY kc.is_standaard DESC, kc.naam;


ALTER VIEW public.v_kompas_config_stats OWNER TO omnitwin_user;

--
-- Name: VIEW v_kompas_config_stats; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON VIEW public.v_kompas_config_stats IS 'Statistieken per kompas configuratie (voor API endpoint /api/kompas/configuraties)';


--
-- Name: v_kompas_hierarchie; Type: VIEW; Schema: public; Owner: omnitwin_user
--

CREATE VIEW public.v_kompas_hierarchie AS
 SELECT kc.id AS config_id,
    kc.naam AS config_naam,
    kc.icoon AS config_icoon,
    kt.id AS titel_id,
    kt.naam AS titel_naam,
    kt.kleur AS titel_kleur,
    kth.id AS thema_id,
    kth.naam AS thema_naam,
    ko.id AS onderdeel_id,
    ko.naam AS onderdeel_naam,
    kim.indicator_uuid,
    i.naam AS indicator_naam,
    kim.is_actueel,
    kim.weging,
    sr.score_type,
    sr.inverse,
    sr.eenheid,
    sr.doel_waarde
   FROM ((((((public.kompas_configuraties kc
     JOIN public.kompas_titels kt ON ((kc.id = kt.config_id)))
     LEFT JOIN public.kompas_themas kth ON ((kt.id = kth.titel_id)))
     LEFT JOIN public.kompas_onderdelen ko ON ((kth.id = ko.thema_id)))
     LEFT JOIN public.kompas_indicator_mapping kim ON (((ko.id = kim.onderdeel_id) AND (kim.config_id = kc.id))))
     LEFT JOIN public.indicatoren i ON ((kim.indicator_uuid = i.uuid)))
     LEFT JOIN public.kompas_indicator_scoring_regels sr ON (((kim.indicator_uuid = sr.indicator_uuid) AND (sr.config_id = kc.id))))
  WHERE (kc.is_actief = true)
  ORDER BY kc.id, kt.volgorde, kth.volgorde, ko.volgorde, i.naam;


ALTER VIEW public.v_kompas_hierarchie OWNER TO omnitwin_user;

--
-- Name: VIEW v_kompas_hierarchie; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON VIEW public.v_kompas_hierarchie IS 'Complete hiërarchie voor alle actieve kompas configuraties met scoring regels';


--
-- Name: v_ontologie_validatiestatus; Type: VIEW; Schema: public; Owner: omnitwin_user
--

CREATE VIEW public.v_ontologie_validatiestatus AS
 SELECT ontologie_status,
    count(*) AS aantal
   FROM public.indicatoren
  GROUP BY ontologie_status
  ORDER BY
        CASE ontologie_status
            WHEN 'draft'::text THEN 1
            WHEN 'beoordeeld_ai'::text THEN 2
            WHEN 'goedgekeurd_mens'::text THEN 3
            ELSE 4
        END;


ALTER VIEW public.v_ontologie_validatiestatus OWNER TO omnitwin_user;

--
-- Name: VIEW v_ontologie_validatiestatus; Type: COMMENT; Schema: public; Owner: omnitwin_user
--

COMMENT ON VIEW public.v_ontologie_validatiestatus IS 'Aggregatie van ontologie validatie-status voor Dashboard widget';


--
-- Name: v_score_types; Type: VIEW; Schema: public; Owner: omnitwin_user
--

CREATE VIEW public.v_score_types AS
 SELECT '+/+'::text AS code,
    'Positive Ascending'::text AS naam,
    'Hoge waarde = Goed (Groen)'::text AS beschrijving,
    'Inkomen, Levensverwachting'::text AS voorbeelden
UNION ALL
 SELECT '+/-'::text AS code,
    'Positive Descending'::text AS naam,
    'Hoge waarde = Slecht (Rood)'::text AS beschrijving,
    'Werkloosheid, Schulden'::text AS voorbeelden
UNION ALL
 SELECT '-/+'::text AS code,
    'Negative Ascending'::text AS naam,
    'Lage waarde = Goed (Groen)'::text AS beschrijving,
    'Criminaliteit, Overlast'::text AS voorbeelden
UNION ALL
 SELECT '-/-'::text AS code,
    'Negative Descending'::text AS naam,
    'Lage waarde = Slecht (Rood)'::text AS beschrijving,
    'Vaccinatiegraad, Participatie'::text AS voorbeelden;


ALTER VIEW public.v_score_types OWNER TO omnitwin_user;

--
-- Name: v_visualisatie_config; Type: VIEW; Schema: public; Owner: omnitwin_user
--

CREATE VIEW public.v_visualisatie_config AS
 SELECT id,
    naam,
    beschrijving,
    colors,
    palette_type,
    classificatie,
    klassen,
    nodata_kleur,
    is_actief
   FROM public.color_schemas cs
  WHERE (is_actief = true);


ALTER VIEW public.v_visualisatie_config OWNER TO omnitwin_user;

--
-- Name: visualisatie_profielen; Type: TABLE; Schema: public; Owner: omnitwin_user
--

CREATE TABLE public.visualisatie_profielen (
    id integer NOT NULL,
    naam character varying(100) NOT NULL,
    beschrijving text,
    indicator_pattern character varying(200),
    color_schema_id integer,
    classificatie_override character varying(30),
    klassen_override integer,
    midpoint_waarde numeric,
    is_actief boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT visualisatie_profielen_classificatie_override_check CHECK (((classificatie_override)::text = ANY ((ARRAY['quantile'::character varying, 'jenks'::character varying, 'equal_interval'::character varying, 'diverging_midpoint'::character varying])::text[]))),
    CONSTRAINT visualisatie_profielen_klassen_override_check CHECK (((klassen_override >= 3) AND (klassen_override <= 7)))
);


ALTER TABLE public.visualisatie_profielen OWNER TO omnitwin_user;

--
-- Name: visualisatie_profielen_id_seq; Type: SEQUENCE; Schema: public; Owner: omnitwin_user
--

CREATE SEQUENCE public.visualisatie_profielen_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.visualisatie_profielen_id_seq OWNER TO omnitwin_user;

--
-- Name: visualisatie_profielen_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: omnitwin_user
--

ALTER SEQUENCE public.visualisatie_profielen_id_seq OWNED BY public.visualisatie_profielen.id;


--
-- Name: vw_gebied_indicator_actueel; Type: VIEW; Schema: public; Owner: omnitwin_user
--

CREATE VIEW public.vw_gebied_indicator_actueel AS
 SELECT DISTINCT ON (gebied_id, indicator_uuid) gebied_id,
    indicator_uuid,
    waarde,
    jaar,
    datum,
    bron
   FROM public.gebied_data gd
  ORDER BY gebied_id, indicator_uuid, jaar DESC;


ALTER VIEW public.vw_gebied_indicator_actueel OWNER TO omnitwin_user;

--
-- Name: vw_gebied_kaart_basis; Type: VIEW; Schema: public; Owner: omnitwin_user
--

CREATE VIEW public.vw_gebied_kaart_basis AS
 SELECT g.id,
    g.naam,
    g.gebiedstype_id,
    gt.naam AS gebiedstype_naam,
    g.actief,
    (public.st_asgeojson(public.st_transform(g.geom, 4326)))::json AS geometry
   FROM (public.gebieden g
     JOIN public.gebiedstypes gt ON ((g.gebiedstype_id = gt.id)))
  WHERE ((g.actief = true) AND (((g.metadata ->> 'water'::text) IS NULL) OR ((g.metadata ->> 'water'::text) <> 'JA'::text)) AND ((g.naam)::text !~~* '%buitenwater%'::text) AND ((g.naam)::text !~~* '%Wadden Sea%'::text) AND ((g.naam)::text !~~* '%IJsselmeer%'::text));


ALTER VIEW public.vw_gebied_kaart_basis OWNER TO omnitwin_user;

--
-- Name: app_logs id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.app_logs ALTER COLUMN id SET DEFAULT nextval('public.app_logs_id_seq'::regclass);


--
-- Name: chat_scenarios id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.chat_scenarios ALTER COLUMN id SET DEFAULT nextval('public.chat_scenarios_id_seq'::regclass);


--
-- Name: color_schemas id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.color_schemas ALTER COLUMN id SET DEFAULT nextval('public.color_schemas_id_seq'::regclass);


--
-- Name: externe_kaartlagen id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.externe_kaartlagen ALTER COLUMN id SET DEFAULT nextval('public.externe_kaartlagen_id_seq'::regclass);


--
-- Name: gebied_data id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebied_data ALTER COLUMN id SET DEFAULT nextval('public.gebied_data_id_seq'::regclass);


--
-- Name: indicator_embeddings id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicator_embeddings ALTER COLUMN id SET DEFAULT nextval('public.indicator_embeddings_id_seq'::regclass);


--
-- Name: indicatoren id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicatoren ALTER COLUMN id SET DEFAULT nextval('public.indicatoren_id_seq'::regclass);


--
-- Name: kompas_configuraties id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_configuraties ALTER COLUMN id SET DEFAULT nextval('public.kompas_configuraties_id_seq'::regclass);


--
-- Name: kompas_extra_onderdelen id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_extra_onderdelen ALTER COLUMN id SET DEFAULT nextval('public.kompas_extra_onderdelen_id_seq'::regclass);


--
-- Name: kompas_indicator_mapping id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_mapping ALTER COLUMN id SET DEFAULT nextval('public.kompas_indicator_mapping_id_seq'::regclass);


--
-- Name: kompas_indicator_scoring_regels id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_scoring_regels ALTER COLUMN id SET DEFAULT nextval('public.kompas_indicator_scoring_regels_id_seq'::regclass);


--
-- Name: kompas_onderdelen id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_onderdelen ALTER COLUMN id SET DEFAULT nextval('public.kompas_onderdelen_id_seq'::regclass);


--
-- Name: kompas_themas id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_themas ALTER COLUMN id SET DEFAULT nextval('public.kompas_themas_id_seq'::regclass);


--
-- Name: kompas_titels id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_titels ALTER COLUMN id SET DEFAULT nextval('public.kompas_titels_id_seq'::regclass);


--
-- Name: llm_config id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.llm_config ALTER COLUMN id SET DEFAULT nextval('public.llm_config_id_seq'::regclass);


--
-- Name: omgevingsvisie_deelgebieden id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.omgevingsvisie_deelgebieden ALTER COLUMN id SET DEFAULT nextval('public.omgevingsvisie_deelgebieden_id_seq'::regclass);


--
-- Name: visualisatie_profielen id; Type: DEFAULT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.visualisatie_profielen ALTER COLUMN id SET DEFAULT nextval('public.visualisatie_profielen_id_seq'::regclass);


--
-- Name: app_logs app_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.app_logs
    ADD CONSTRAINT app_logs_pkey PRIMARY KEY (id);


--
-- Name: chat_scenarios chat_scenarios_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.chat_scenarios
    ADD CONSTRAINT chat_scenarios_pkey PRIMARY KEY (id);


--
-- Name: chat_scenarios chat_scenarios_rol_code_key; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.chat_scenarios
    ADD CONSTRAINT chat_scenarios_rol_code_key UNIQUE (rol_code);


--
-- Name: color_schemas color_schemas_naam_key; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.color_schemas
    ADD CONSTRAINT color_schemas_naam_key UNIQUE (naam);


--
-- Name: color_schemas color_schemas_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.color_schemas
    ADD CONSTRAINT color_schemas_pkey PRIMARY KEY (id);


--
-- Name: externe_kaartlagen externe_kaartlagen_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.externe_kaartlagen
    ADD CONSTRAINT externe_kaartlagen_pkey PRIMARY KEY (id);


--
-- Name: gebied_data gebied_data_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebied_data
    ADD CONSTRAINT gebied_data_pkey PRIMARY KEY (id);


--
-- Name: gebieden gebieden_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebieden
    ADD CONSTRAINT gebieden_pkey PRIMARY KEY (id);


--
-- Name: gebiedstypes gebiedstypes_code_key; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebiedstypes
    ADD CONSTRAINT gebiedstypes_code_key UNIQUE (code);


--
-- Name: gebiedstypes gebiedstypes_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebiedstypes
    ADD CONSTRAINT gebiedstypes_pkey PRIMARY KEY (id);


--
-- Name: gemeenten gemeenten_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gemeenten
    ADD CONSTRAINT gemeenten_pkey PRIMARY KEY (code);


--
-- Name: indicator_embeddings indicator_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicator_embeddings
    ADD CONSTRAINT indicator_embeddings_pkey PRIMARY KEY (id);


--
-- Name: indicator_gebiedstype_relaties indicator_gebiedstype_relaties_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicator_gebiedstype_relaties
    ADD CONSTRAINT indicator_gebiedstype_relaties_pkey PRIMARY KEY (indicator_uuid, gebiedstype_id);


--
-- Name: indicatoren indicatoren_code_key; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicatoren
    ADD CONSTRAINT indicatoren_code_key UNIQUE (code);


--
-- Name: indicatoren indicatoren_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicatoren
    ADD CONSTRAINT indicatoren_pkey PRIMARY KEY (id);


--
-- Name: indicatoren indicatoren_uuid_key; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicatoren
    ADD CONSTRAINT indicatoren_uuid_key UNIQUE (uuid);


--
-- Name: kompas_configuraties kompas_configuraties_naam_key; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_configuraties
    ADD CONSTRAINT kompas_configuraties_naam_key UNIQUE (naam);


--
-- Name: kompas_configuraties kompas_configuraties_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_configuraties
    ADD CONSTRAINT kompas_configuraties_pkey PRIMARY KEY (id);


--
-- Name: kompas_extra_onderdelen kompas_extra_onderdelen_naam_key; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_extra_onderdelen
    ADD CONSTRAINT kompas_extra_onderdelen_naam_key UNIQUE (naam);


--
-- Name: kompas_extra_onderdelen kompas_extra_onderdelen_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_extra_onderdelen
    ADD CONSTRAINT kompas_extra_onderdelen_pkey PRIMARY KEY (id);


--
-- Name: kompas_indicator_extra_tags kompas_indicator_extra_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_extra_tags
    ADD CONSTRAINT kompas_indicator_extra_tags_pkey PRIMARY KEY (indicator_uuid, extra_onderdeel_id);


--
-- Name: kompas_indicator_mapping kompas_indicator_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_mapping
    ADD CONSTRAINT kompas_indicator_mapping_pkey PRIMARY KEY (id);


--
-- Name: kompas_indicator_scoring_regels kompas_indicator_scoring_regels_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_scoring_regels
    ADD CONSTRAINT kompas_indicator_scoring_regels_pkey PRIMARY KEY (id);


--
-- Name: kompas_onderdelen kompas_onderdelen_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_onderdelen
    ADD CONSTRAINT kompas_onderdelen_pkey PRIMARY KEY (id);


--
-- Name: kompas_themas kompas_themas_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_themas
    ADD CONSTRAINT kompas_themas_pkey PRIMARY KEY (id);


--
-- Name: kompas_titels kompas_titels_naam_key; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_titels
    ADD CONSTRAINT kompas_titels_naam_key UNIQUE (naam);


--
-- Name: kompas_titels kompas_titels_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_titels
    ADD CONSTRAINT kompas_titels_pkey PRIMARY KEY (id);


--
-- Name: llm_config llm_config_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.llm_config
    ADD CONSTRAINT llm_config_pkey PRIMARY KEY (id);


--
-- Name: log_config log_config_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.log_config
    ADD CONSTRAINT log_config_pkey PRIMARY KEY (category);


--
-- Name: omgevingsvisie_deelgebieden omgevingsvisie_deelgebieden_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.omgevingsvisie_deelgebieden
    ADD CONSTRAINT omgevingsvisie_deelgebieden_pkey PRIMARY KEY (id);


--
-- Name: ov_halte_clusters ov_halte_clusters_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.ov_halte_clusters
    ADD CONSTRAINT ov_halte_clusters_pkey PRIMARY KEY (cluster_id);


--
-- Name: ov_haltes_per_buurt ov_haltes_per_buurt_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.ov_haltes_per_buurt
    ADD CONSTRAINT ov_haltes_per_buurt_pkey PRIMARY KEY (gebied_id, jaar);


--
-- Name: ov_haltes ov_haltes_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.ov_haltes
    ADD CONSTRAINT ov_haltes_pkey PRIMARY KEY (osm_id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (token);


--
-- Name: system_prompts system_prompts_naam_key; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.system_prompts
    ADD CONSTRAINT system_prompts_naam_key UNIQUE (naam);


--
-- Name: system_prompts system_prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.system_prompts
    ADD CONSTRAINT system_prompts_pkey PRIMARY KEY (id);


--
-- Name: indicator_embeddings unique_embedding_per_indicator; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicator_embeddings
    ADD CONSTRAINT unique_embedding_per_indicator UNIQUE (indicator_uuid);


--
-- Name: kompas_indicator_mapping unique_indicator_onderdeel; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_mapping
    ADD CONSTRAINT unique_indicator_onderdeel UNIQUE (indicator_uuid, onderdeel_id);


--
-- Name: kompas_indicator_mapping unique_indicator_onderdeel_config; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_mapping
    ADD CONSTRAINT unique_indicator_onderdeel_config UNIQUE (config_id, indicator_uuid, onderdeel_id);


--
-- Name: kompas_indicator_scoring_regels unique_indicator_scoring_per_config; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_scoring_regels
    ADD CONSTRAINT unique_indicator_scoring_per_config UNIQUE (indicator_uuid, config_id);


--
-- Name: gebied_data unique_measurement_datum; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebied_data
    ADD CONSTRAINT unique_measurement_datum UNIQUE (gebied_id, indicator_uuid, datum, scenario_id);


--
-- Name: gebied_data unique_measurement_jaar; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebied_data
    ADD CONSTRAINT unique_measurement_jaar UNIQUE (gebied_id, indicator_uuid, jaar, scenario_id);


--
-- Name: kompas_onderdelen unique_onderdeel_per_thema; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_onderdelen
    ADD CONSTRAINT unique_onderdeel_per_thema UNIQUE (thema_id, naam);


--
-- Name: kompas_themas unique_thema_per_titel; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_themas
    ADD CONSTRAINT unique_thema_per_titel UNIQUE (titel_id, naam);


--
-- Name: kompas_titels unique_titel_per_config; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_titels
    ADD CONSTRAINT unique_titel_per_config UNIQUE (config_id, naam);


--
-- Name: gebied_data unq_gebied_indicator_jaar; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebied_data
    ADD CONSTRAINT unq_gebied_indicator_jaar UNIQUE (gebied_id, indicator_uuid, jaar);


--
-- Name: visualisatie_profielen uq_visualisatie_profielen_naam; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.visualisatie_profielen
    ADD CONSTRAINT uq_visualisatie_profielen_naam UNIQUE (naam);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: visualisatie_profielen visualisatie_profielen_pkey; Type: CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.visualisatie_profielen
    ADD CONSTRAINT visualisatie_profielen_pkey PRIMARY KEY (id);


--
-- Name: idx_app_logs_category; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_app_logs_category ON public.app_logs USING btree (category);


--
-- Name: idx_app_logs_level; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_app_logs_level ON public.app_logs USING btree (level);


--
-- Name: idx_app_logs_timestamp; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_app_logs_timestamp ON public.app_logs USING btree ("timestamp" DESC);


--
-- Name: idx_app_logs_user_id; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_app_logs_user_id ON public.app_logs USING btree (user_id);


--
-- Name: idx_externe_kaartlagen_actief; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_externe_kaartlagen_actief ON public.externe_kaartlagen USING btree (actief, volgorde);


--
-- Name: idx_gebied_data_composite; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebied_data_composite ON public.gebied_data USING btree (gebied_id, indicator_uuid, jaar);


--
-- Name: idx_gebied_data_datum; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebied_data_datum ON public.gebied_data USING btree (datum) WHERE (datum IS NOT NULL);


--
-- Name: idx_gebied_data_gebied; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebied_data_gebied ON public.gebied_data USING btree (gebied_id);


--
-- Name: idx_gebied_data_indicator; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebied_data_indicator ON public.gebied_data USING btree (indicator_uuid);


--
-- Name: idx_gebied_data_jaar; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebied_data_jaar ON public.gebied_data USING btree (jaar) WHERE (jaar IS NOT NULL);


--
-- Name: idx_gebied_data_scenario; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebied_data_scenario ON public.gebied_data USING btree (scenario_id);


--
-- Name: idx_gebieden_actief; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebieden_actief ON public.gebieden USING btree (actief) WHERE (actief = true);


--
-- Name: idx_gebieden_centroid; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebieden_centroid ON public.gebieden USING gist (geom_centroid);


--
-- Name: idx_gebieden_gemeente; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebieden_gemeente ON public.gebieden USING btree (gemeente_code);


--
-- Name: idx_gebieden_geom; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebieden_geom ON public.gebieden USING gist (geom);


--
-- Name: idx_gebieden_provincie; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebieden_provincie ON public.gebieden USING btree (provincienaam);


--
-- Name: idx_gebieden_type; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebieden_type ON public.gebieden USING btree (gebiedstype_id);


--
-- Name: idx_gebiedstypes_code; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gebiedstypes_code ON public.gebiedstypes USING btree (code);


--
-- Name: idx_gemeenten_naam; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gemeenten_naam ON public.gemeenten USING btree (naam);


--
-- Name: idx_gemeenten_provincie; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_gemeenten_provincie ON public.gemeenten USING btree (provincie);


--
-- Name: idx_ind_geb_rel_gebiedstype; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_ind_geb_rel_gebiedstype ON public.indicator_gebiedstype_relaties USING btree (gebiedstype_id);


--
-- Name: idx_indicator_embeddings_vector; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_indicator_embeddings_vector ON public.indicator_embeddings USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: idx_indicatoren_bron_systeem; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_indicatoren_bron_systeem ON public.indicatoren USING btree (bron_systeem_api);


--
-- Name: idx_indicatoren_code; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_indicatoren_code ON public.indicatoren USING btree (code);


--
-- Name: idx_indicatoren_color_schema; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_indicatoren_color_schema ON public.indicatoren USING btree (color_schema_id);


--
-- Name: idx_indicatoren_geldigheid; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_indicatoren_geldigheid ON public.indicatoren USING btree (begingeldigheid, eindgeldigheid);


--
-- Name: idx_indicatoren_laatste_check; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_indicatoren_laatste_check ON public.indicatoren USING btree (laatste_check_datum);


--
-- Name: idx_indicatoren_score_type; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_indicatoren_score_type ON public.indicatoren USING btree (score_type);


--
-- Name: idx_indicatoren_status; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_indicatoren_status ON public.indicatoren USING btree (status);


--
-- Name: idx_indicatoren_uuid; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_indicatoren_uuid ON public.indicatoren USING btree (uuid);


--
-- Name: idx_kompas_config_actief; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_config_actief ON public.kompas_configuraties USING btree (is_actief) WHERE (is_actief = true);


--
-- Name: idx_kompas_config_standaard; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_config_standaard ON public.kompas_configuraties USING btree (is_standaard) WHERE (is_standaard = true);


--
-- Name: idx_kompas_extra_onderdelen_naam; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_extra_onderdelen_naam ON public.kompas_extra_onderdelen USING btree (naam);


--
-- Name: idx_kompas_extra_tags_extra; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_extra_tags_extra ON public.kompas_indicator_extra_tags USING btree (extra_onderdeel_id);


--
-- Name: idx_kompas_extra_tags_indicator; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_extra_tags_indicator ON public.kompas_indicator_extra_tags USING btree (indicator_uuid);


--
-- Name: idx_kompas_mapping_actueel; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_mapping_actueel ON public.kompas_indicator_mapping USING btree (is_actueel) WHERE (is_actueel = true);


--
-- Name: idx_kompas_mapping_config; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_mapping_config ON public.kompas_indicator_mapping USING btree (config_id);


--
-- Name: idx_kompas_mapping_indicator; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_mapping_indicator ON public.kompas_indicator_mapping USING btree (indicator_uuid);


--
-- Name: idx_kompas_mapping_onderdeel; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_mapping_onderdeel ON public.kompas_indicator_mapping USING btree (onderdeel_id);


--
-- Name: idx_kompas_onderdelen_thema; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_onderdelen_thema ON public.kompas_onderdelen USING btree (thema_id);


--
-- Name: idx_kompas_scoring_config; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_scoring_config ON public.kompas_indicator_scoring_regels USING btree (config_id);


--
-- Name: idx_kompas_scoring_indicator; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_scoring_indicator ON public.kompas_indicator_scoring_regels USING btree (indicator_uuid);


--
-- Name: idx_kompas_scoring_type; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_scoring_type ON public.kompas_indicator_scoring_regels USING btree (score_type);


--
-- Name: idx_kompas_themas_titel; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_themas_titel ON public.kompas_themas USING btree (titel_id);


--
-- Name: idx_kompas_titels_config; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_titels_config ON public.kompas_titels USING btree (config_id);


--
-- Name: idx_kompas_titels_naam; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_kompas_titels_naam ON public.kompas_titels USING btree (naam);


--
-- Name: idx_omg_deelgebieden_geom; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_omg_deelgebieden_geom ON public.omgevingsvisie_deelgebieden USING gist (geom);


--
-- Name: idx_omg_deelgebieden_geom_wgs84; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_omg_deelgebieden_geom_wgs84 ON public.omgevingsvisie_deelgebieden USING gist (geom_wgs84);


--
-- Name: idx_ov_clusters_gebied; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_ov_clusters_gebied ON public.ov_halte_clusters USING btree (gebied_id);


--
-- Name: idx_ov_clusters_geom; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_ov_clusters_geom ON public.ov_halte_clusters USING gist (geom);


--
-- Name: idx_ov_haltes_gebied; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_ov_haltes_gebied ON public.ov_haltes USING btree (gebied_id);


--
-- Name: idx_ov_haltes_geom; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_ov_haltes_geom ON public.ov_haltes USING gist (geom);


--
-- Name: idx_ov_haltes_type; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_ov_haltes_type ON public.ov_haltes USING btree (ov_type);


--
-- Name: idx_system_prompts_naam; Type: INDEX; Schema: public; Owner: omnitwin_user
--

CREATE INDEX idx_system_prompts_naam ON public.system_prompts USING btree (naam);


--
-- Name: llm_config trg_llm_config_modtime; Type: TRIGGER; Schema: public; Owner: omnitwin_user
--

CREATE TRIGGER trg_llm_config_modtime BEFORE UPDATE ON public.llm_config FOR EACH ROW EXECUTE FUNCTION public.update_llm_config_modtime();


--
-- Name: system_prompts trg_system_prompts_mod_time; Type: TRIGGER; Schema: public; Owner: omnitwin_user
--

CREATE TRIGGER trg_system_prompts_mod_time BEFORE UPDATE ON public.system_prompts FOR EACH ROW EXECUTE FUNCTION public.update_system_prompts_mod_time();


--
-- Name: gebied_data trigger_gebied_data_updated_at; Type: TRIGGER; Schema: public; Owner: omnitwin_user
--

CREATE TRIGGER trigger_gebied_data_updated_at BEFORE UPDATE ON public.gebied_data FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: gebieden trigger_gebieden_centroid; Type: TRIGGER; Schema: public; Owner: omnitwin_user
--

CREATE TRIGGER trigger_gebieden_centroid BEFORE INSERT OR UPDATE OF geom ON public.gebieden FOR EACH ROW EXECUTE FUNCTION public.update_gebied_centroid();


--
-- Name: gebieden trigger_gebieden_updated_at; Type: TRIGGER; Schema: public; Owner: omnitwin_user
--

CREATE TRIGGER trigger_gebieden_updated_at BEFORE UPDATE ON public.gebieden FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: gebiedstypes trigger_gebiedstypes_updated_at; Type: TRIGGER; Schema: public; Owner: omnitwin_user
--

CREATE TRIGGER trigger_gebiedstypes_updated_at BEFORE UPDATE ON public.gebiedstypes FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: gemeenten trigger_gemeenten_updated_at; Type: TRIGGER; Schema: public; Owner: omnitwin_user
--

CREATE TRIGGER trigger_gemeenten_updated_at BEFORE UPDATE ON public.gemeenten FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: indicator_embeddings trigger_indicator_embeddings_updated_at; Type: TRIGGER; Schema: public; Owner: omnitwin_user
--

CREATE TRIGGER trigger_indicator_embeddings_updated_at BEFORE UPDATE ON public.indicator_embeddings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: indicatoren trigger_indicatoren_updated_at; Type: TRIGGER; Schema: public; Owner: omnitwin_user
--

CREATE TRIGGER trigger_indicatoren_updated_at BEFORE UPDATE ON public.indicatoren FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: gebieden fk_gebieden_gemeente; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebieden
    ADD CONSTRAINT fk_gebieden_gemeente FOREIGN KEY (gemeente_code) REFERENCES public.gemeenten(code);


--
-- Name: gebieden fk_gebiedstype; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebieden
    ADD CONSTRAINT fk_gebiedstype FOREIGN KEY (gebiedstype_id) REFERENCES public.gebiedstypes(id) ON DELETE RESTRICT;


--
-- Name: gebied_data gebied_data_gebied_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebied_data
    ADD CONSTRAINT gebied_data_gebied_id_fkey FOREIGN KEY (gebied_id) REFERENCES public.gebieden(id) ON DELETE CASCADE;


--
-- Name: gebied_data gebied_data_indicator_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebied_data
    ADD CONSTRAINT gebied_data_indicator_uuid_fkey FOREIGN KEY (indicator_uuid) REFERENCES public.indicatoren(uuid) ON DELETE CASCADE;


--
-- Name: gebieden gebieden_gebiedstype_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.gebieden
    ADD CONSTRAINT gebieden_gebiedstype_id_fkey FOREIGN KEY (gebiedstype_id) REFERENCES public.gebiedstypes(id) ON DELETE RESTRICT;


--
-- Name: indicator_embeddings indicator_embeddings_indicator_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicator_embeddings
    ADD CONSTRAINT indicator_embeddings_indicator_uuid_fkey FOREIGN KEY (indicator_uuid) REFERENCES public.indicatoren(uuid) ON DELETE CASCADE;


--
-- Name: indicator_gebiedstype_relaties indicator_gebiedstype_relaties_gebiedstype_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicator_gebiedstype_relaties
    ADD CONSTRAINT indicator_gebiedstype_relaties_gebiedstype_id_fkey FOREIGN KEY (gebiedstype_id) REFERENCES public.gebiedstypes(id) ON DELETE CASCADE;


--
-- Name: indicator_gebiedstype_relaties indicator_gebiedstype_relaties_indicator_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicator_gebiedstype_relaties
    ADD CONSTRAINT indicator_gebiedstype_relaties_indicator_uuid_fkey FOREIGN KEY (indicator_uuid) REFERENCES public.indicatoren(uuid) ON DELETE CASCADE;


--
-- Name: indicatoren indicatoren_color_schema_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicatoren
    ADD CONSTRAINT indicatoren_color_schema_id_fkey FOREIGN KEY (color_schema_id) REFERENCES public.color_schemas(id);


--
-- Name: indicatoren indicatoren_gevalideerd_door_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.indicatoren
    ADD CONSTRAINT indicatoren_gevalideerd_door_fkey FOREIGN KEY (gevalideerd_door) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: kompas_indicator_extra_tags kompas_indicator_extra_tags_extra_onderdeel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_extra_tags
    ADD CONSTRAINT kompas_indicator_extra_tags_extra_onderdeel_id_fkey FOREIGN KEY (extra_onderdeel_id) REFERENCES public.kompas_extra_onderdelen(id) ON DELETE CASCADE;


--
-- Name: kompas_indicator_extra_tags kompas_indicator_extra_tags_indicator_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_extra_tags
    ADD CONSTRAINT kompas_indicator_extra_tags_indicator_uuid_fkey FOREIGN KEY (indicator_uuid) REFERENCES public.indicatoren(uuid) ON DELETE CASCADE;


--
-- Name: kompas_indicator_mapping kompas_indicator_mapping_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_mapping
    ADD CONSTRAINT kompas_indicator_mapping_config_id_fkey FOREIGN KEY (config_id) REFERENCES public.kompas_configuraties(id) ON DELETE CASCADE;


--
-- Name: kompas_indicator_mapping kompas_indicator_mapping_indicator_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_mapping
    ADD CONSTRAINT kompas_indicator_mapping_indicator_uuid_fkey FOREIGN KEY (indicator_uuid) REFERENCES public.indicatoren(uuid) ON DELETE CASCADE;


--
-- Name: kompas_indicator_mapping kompas_indicator_mapping_onderdeel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_mapping
    ADD CONSTRAINT kompas_indicator_mapping_onderdeel_id_fkey FOREIGN KEY (onderdeel_id) REFERENCES public.kompas_onderdelen(id) ON DELETE CASCADE;


--
-- Name: kompas_indicator_scoring_regels kompas_indicator_scoring_regels_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_scoring_regels
    ADD CONSTRAINT kompas_indicator_scoring_regels_config_id_fkey FOREIGN KEY (config_id) REFERENCES public.kompas_configuraties(id) ON DELETE CASCADE;


--
-- Name: kompas_indicator_scoring_regels kompas_indicator_scoring_regels_indicator_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_indicator_scoring_regels
    ADD CONSTRAINT kompas_indicator_scoring_regels_indicator_uuid_fkey FOREIGN KEY (indicator_uuid) REFERENCES public.indicatoren(uuid) ON DELETE CASCADE;


--
-- Name: kompas_onderdelen kompas_onderdelen_thema_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_onderdelen
    ADD CONSTRAINT kompas_onderdelen_thema_id_fkey FOREIGN KEY (thema_id) REFERENCES public.kompas_themas(id) ON DELETE CASCADE;


--
-- Name: kompas_themas kompas_themas_titel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_themas
    ADD CONSTRAINT kompas_themas_titel_id_fkey FOREIGN KEY (titel_id) REFERENCES public.kompas_titels(id) ON DELETE CASCADE;


--
-- Name: kompas_titels kompas_titels_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.kompas_titels
    ADD CONSTRAINT kompas_titels_config_id_fkey FOREIGN KEY (config_id) REFERENCES public.kompas_configuraties(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: visualisatie_profielen visualisatie_profielen_color_schema_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: omnitwin_user
--

ALTER TABLE ONLY public.visualisatie_profielen
    ADD CONSTRAINT visualisatie_profielen_color_schema_id_fkey FOREIGN KEY (color_schema_id) REFERENCES public.color_schemas(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 3gy4bFeI4foWARkSZje9qygwfD5dXKLhbefeqXjBiK82y7d3LZ316oAy286Aj2c

CREATE TABLE IF NOT EXISTS public.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash TEXT UNIQUE NOT NULL,
    label VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON public.api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON public.api_keys(is_active) WHERE is_active = TRUE;
CREATE OR REPLACE FUNCTION public.get_indicatoren_stats(p_gebiedstype_id uuid DEFAULT NULL)
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
) AS $$
BEGIN
    IF p_gebiedstype_id IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            i.uuid,
            i.naam,
            i.code,
            i.omschrijving,
            i.eenheid,
            i.categorie,
            COALESCE(COUNT(DISTINCT CASE 
                WHEN g.gebiedstype_id = p_gebiedstype_id 
                THEN gd.gebied_id 
            END), 0)::bigint as aantal_gebieden_met_data,
            COALESCE(COUNT(DISTINCT gd.id), 0)::bigint as aantal_metingen,
            MAX(gd.jaar)::integer as nieuwste_jaar
        FROM public.indicatoren i
        LEFT JOIN public.gebied_data gd ON i.uuid = gd.indicator_uuid
        LEFT JOIN public.gebieden g ON gd.gebied_id = g.id
        WHERE i.status IN ('O', 'C')
        GROUP BY i.uuid, i.naam, i.code, i.omschrijving, i.eenheid, i.categorie
        ORDER BY 
            COUNT(DISTINCT CASE 
                WHEN g.gebiedstype_id = p_gebiedstype_id 
                THEN gd.gebied_id 
            END) DESC NULLS LAST,
            i.naam;
    ELSE
        RETURN QUERY
        SELECT 
            i.uuid,
            i.naam,
            i.code,
            i.omschrijving,
            i.eenheid,
            i.categorie,
            0::bigint as aantal_gebieden_met_data,
            COUNT(DISTINCT gd.id)::bigint as aantal_metingen,
            MAX(gd.jaar)::integer as nieuwste_jaar
        FROM public.indicatoren i
        LEFT JOIN public.gebied_data gd ON i.uuid = gd.indicator_uuid
        WHERE i.status IN ('O', 'C')
        GROUP BY i.uuid, i.naam, i.code, i.omschrijving, i.eenheid, i.categorie
        ORDER BY i.naam;
    END IF;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Zorg dat postgrest dit kan lezen
GRANT EXECUTE ON FUNCTION public.get_indicatoren_stats(uuid) TO omnitwin_user;

CREATE OR REPLACE FUNCTION public.get_indicatoren_stats(p_gebiedstype_id uuid DEFAULT NULL)
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
) AS $$
BEGIN
    IF p_gebiedstype_id IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            i.uuid,
            i.naam,
            i.code,
            i.omschrijving,
            i.eenheid,
            i.categorie,
            COALESCE(COUNT(DISTINCT CASE 
                WHEN g.gebiedstype_id = p_gebiedstype_id 
                THEN gd.gebied_id 
            END), 0)::bigint as aantal_gebieden_met_data,
            COALESCE(COUNT(DISTINCT gd.id), 0)::bigint as aantal_metingen,
            MAX(gd.jaar)::integer as nieuwste_jaar
        FROM public.indicatoren i
        LEFT JOIN public.gebied_data gd ON i.uuid = gd.indicator_uuid
        LEFT JOIN public.gebieden g ON gd.gebied_id = g.id
        WHERE i.status IN ('O', 'C')
        GROUP BY i.uuid, i.naam, i.code, i.omschrijving, i.eenheid, i.categorie
        ORDER BY 
            COUNT(DISTINCT CASE 
                WHEN g.gebiedstype_id = p_gebiedstype_id 
                THEN gd.gebied_id 
            END) DESC NULLS LAST,
            i.naam;
    ELSE
        RETURN QUERY
        SELECT 
            i.uuid,
            i.naam,
            i.code,
            i.omschrijving,
            i.eenheid,
            i.categorie,
            0::bigint as aantal_gebieden_met_data,
            COUNT(DISTINCT gd.id)::bigint as aantal_metingen,
            MAX(gd.jaar)::integer as nieuwste_jaar
        FROM public.indicatoren i
        LEFT JOIN public.gebied_data gd ON i.uuid = gd.indicator_uuid
        WHERE i.status IN ('O', 'C')
        GROUP BY i.uuid, i.naam, i.code, i.omschrijving, i.eenheid, i.categorie
        ORDER BY i.naam;
    END IF;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Zorg dat postgrest dit kan lezen
GRANT EXECUTE ON FUNCTION public.get_indicatoren_stats(uuid) TO omnitwin_user;
