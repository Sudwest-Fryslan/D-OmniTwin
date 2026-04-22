-- ============================================================================
-- D-OMNITWIN DATABASE INITIALIZATION SCRIPT
-- ============================================================================
-- Versie: 1.0 (Consolidatie van alle schema versies)
-- Datum: 3 februari 2026
-- Doel: Volledige database setup voor nieuwe installaties
-- 
-- LET OP: Dit script is ALLEEN voor NIEUWE installaties!
--         NIET uitvoeren op bestaande productie database!
-- 
-- GEBRUIK:
--   psql -U omnitwin_user -d omnitwin_db -f schema_latest.sql
-- ============================================================================

-- ============================================================================
-- SECTION 1: EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';

CREATE EXTENSION IF NOT EXISTS vector;
COMMENT ON EXTENSION vector IS 'pgvector — vector similarity search for AI embeddings';

-- ============================================================================
-- SECTION 2: HELPER FUNCTIONS
-- ============================================================================

-- Functie: Automatisch updated_at timestamp updaten
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Functie: Automatisch centroid berekenen voor gebieden
CREATE OR REPLACE FUNCTION update_gebied_centroid()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.geom IS NOT NULL THEN
        NEW.geom_centroid = ST_Centroid(NEW.geom);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SECTION 3: CORE TABLES (GEBIEDSMONITOR)
-- ============================================================================

-- Tabel: gebiedstypes
CREATE TABLE IF NOT EXISTS gebiedstypes (
    id UUID PRIMARY KEY,
    naam VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE,
    beschrijving TEXT,
    bron VARCHAR(255),
    niveau VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_gebiedstypes_code ON gebiedstypes(code);

-- Tabel: gemeenten
CREATE TABLE IF NOT EXISTS gemeenten (
    code VARCHAR(4) PRIMARY KEY,
    naam VARCHAR(100) NOT NULL,
    provincie VARCHAR(50) NOT NULL,
    is_eiland BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_gemeenten_provincie ON gemeenten(provincie);
CREATE INDEX IF NOT EXISTS idx_gemeenten_naam ON gemeenten(naam);

-- Tabel: gebieden
CREATE TABLE IF NOT EXISTS gebieden (
    id VARCHAR(100) PRIMARY KEY,
    gebiedstype_id UUID NOT NULL REFERENCES gebiedstypes(id) ON DELETE RESTRICT,
    gemeente_code VARCHAR(4) REFERENCES gemeenten(code),
    naam VARCHAR(255) NOT NULL,
    provincienaam VARCHAR(50),
    geom GEOMETRY(MULTIPOLYGON, 28992),
    geom_centroid GEOMETRY(POINT, 28992),
    metadata JSONB,
    actief BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_gebieden_geom ON gebieden USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_gebieden_centroid ON gebieden USING GIST(geom_centroid);
CREATE INDEX IF NOT EXISTS idx_gebieden_type ON gebieden(gebiedstype_id);
CREATE INDEX IF NOT EXISTS idx_gebieden_actief ON gebieden(actief) WHERE actief = TRUE;
CREATE INDEX IF NOT EXISTS idx_gebieden_gemeente ON gebieden(gemeente_code);
CREATE INDEX IF NOT EXISTS idx_gebieden_provincie ON gebieden(provincienaam);

-- Tabel: indicatoren
CREATE TABLE IF NOT EXISTS indicatoren (
    id SERIAL PRIMARY KEY,
    uuid UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    naam VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE,
    omschrijving TEXT,
    definitie TEXT,
    eenheid VARCHAR(50),
    interpretatie_logica VARCHAR(20) DEFAULT 'pos_is_pos',
    min_waarde DECIMAL,
    max_waarde DECIMAL,
    bron VARCHAR(255),
    status VARCHAR(1) DEFAULT 'O',
    begingeldigheid TIMESTAMP,
    eindgeldigheid TIMESTAMP,
    categorie VARCHAR(100),
    score_type VARCHAR(10) DEFAULT '+/+' CHECK (score_type IN ('+/+', '+/-', '-/+', '-/-', '-=-')),
    color_schema_id INTEGER,
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_status CHECK (status IN ('C', 'O', 'B'))
);
CREATE INDEX IF NOT EXISTS idx_indicatoren_uuid ON indicatoren(uuid);
CREATE INDEX IF NOT EXISTS idx_indicatoren_code ON indicatoren(code);
CREATE INDEX IF NOT EXISTS idx_indicatoren_status ON indicatoren(status);
CREATE INDEX IF NOT EXISTS idx_indicatoren_score_type ON indicatoren(score_type);

-- Tabel: indicator_gebiedstype_relaties
CREATE TABLE IF NOT EXISTS indicator_gebiedstype_relaties (
    indicator_uuid UUID NOT NULL REFERENCES indicatoren(uuid) ON DELETE CASCADE,
    gebiedstype_id UUID NOT NULL REFERENCES gebiedstypes(id) ON DELETE CASCADE,
    verplicht BOOLEAN DEFAULT FALSE,
    display_volgorde INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (indicator_uuid, gebiedstype_id)
);
CREATE INDEX IF NOT EXISTS idx_ind_geb_rel_gebiedstype ON indicator_gebiedstype_relaties(gebiedstype_id);

-- Tabel: gebied_data
CREATE TABLE IF NOT EXISTS gebied_data (
    id BIGSERIAL PRIMARY KEY,
    gebied_id VARCHAR(100) NOT NULL REFERENCES gebieden(id) ON DELETE CASCADE,
    indicator_uuid UUID NOT NULL REFERENCES indicatoren(uuid) ON DELETE CASCADE,
    waarde DECIMAL NOT NULL,
    jaar INTEGER,
    datum TIMESTAMP,
    scenario_id VARCHAR(50) DEFAULT 'current',
    bron VARCHAR(255),
    kwaliteit VARCHAR(20),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_measurement_jaar UNIQUE (gebied_id, indicator_uuid, jaar, scenario_id),
    CONSTRAINT unique_measurement_datum UNIQUE (gebied_id, indicator_uuid, datum, scenario_id),
    CONSTRAINT check_jaar_of_datum CHECK (
        (jaar IS NOT NULL AND datum IS NULL) OR 
        (jaar IS NULL AND datum IS NOT NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_gebied_data_gebied ON gebied_data(gebied_id);
CREATE INDEX IF NOT EXISTS idx_gebied_data_indicator ON gebied_data(indicator_uuid);
CREATE INDEX IF NOT EXISTS idx_gebied_data_jaar ON gebied_data(jaar) WHERE jaar IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_gebied_data_scenario ON gebied_data(scenario_id);
CREATE INDEX IF NOT EXISTS idx_gebied_data_composite ON gebied_data(gebied_id, indicator_uuid, jaar);

-- ============================================================================
-- SECTION 4: KOMPAS TABLES
-- ============================================================================

-- Tabel: kompas_configuraties
CREATE TABLE IF NOT EXISTS kompas_configuraties (
    id SERIAL PRIMARY KEY,
    naam VARCHAR(150) UNIQUE NOT NULL,
    beschrijving TEXT,
    is_standaard BOOLEAN DEFAULT FALSE,
    is_actief BOOLEAN DEFAULT TRUE,
    icoon VARCHAR(50) DEFAULT '🌍',
    versie INT DEFAULT 1,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_kompas_config_standaard ON kompas_configuraties(is_standaard) WHERE is_standaard = TRUE;
CREATE INDEX IF NOT EXISTS idx_kompas_config_actief ON kompas_configuraties(is_actief) WHERE is_actief = TRUE;

-- Tabel: kompas_titels
CREATE TABLE IF NOT EXISTS kompas_titels (
    id SERIAL PRIMARY KEY,
    config_id INT NOT NULL REFERENCES kompas_configuraties(id) ON DELETE CASCADE,
    naam VARCHAR(150) NOT NULL,
    kleur VARCHAR(7) DEFAULT '#3B82F6',
    volgorde INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_titel_per_config UNIQUE (config_id, naam)
);
CREATE INDEX IF NOT EXISTS idx_kompas_titels_config ON kompas_titels(config_id);

-- Tabel: kompas_themas
CREATE TABLE IF NOT EXISTS kompas_themas (
    id SERIAL PRIMARY KEY,
    titel_id INT NOT NULL REFERENCES kompas_titels(id) ON DELETE CASCADE,
    naam VARCHAR(150) NOT NULL,
    volgorde INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_thema_per_titel UNIQUE (titel_id, naam)
);
CREATE INDEX IF NOT EXISTS idx_kompas_themas_titel ON kompas_themas(titel_id);

-- Tabel: kompas_onderdelen
CREATE TABLE IF NOT EXISTS kompas_onderdelen (
    id SERIAL PRIMARY KEY,
    thema_id INT NOT NULL REFERENCES kompas_themas(id) ON DELETE CASCADE,
    naam VARCHAR(150) NOT NULL,
    volgorde INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_onderdeel_per_thema UNIQUE (thema_id, naam)
);
CREATE INDEX IF NOT EXISTS idx_kompas_onderdelen_thema ON kompas_onderdelen(thema_id);

-- Tabel: kompas_extra_onderdelen
CREATE TABLE IF NOT EXISTS kompas_extra_onderdelen (
    id SERIAL PRIMARY KEY,
    naam VARCHAR(100) UNIQUE NOT NULL,
    beschrijving TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel: kompas_indicator_mapping
CREATE TABLE IF NOT EXISTS kompas_indicator_mapping (
    id SERIAL PRIMARY KEY,
    config_id INT NOT NULL REFERENCES kompas_configuraties(id) ON DELETE CASCADE,
    indicator_uuid UUID NOT NULL REFERENCES indicatoren(uuid) ON DELETE CASCADE,
    onderdeel_id INT NOT NULL REFERENCES kompas_onderdelen(id) ON DELETE CASCADE,
    weging FLOAT DEFAULT 1.0,
    is_actueel BOOLEAN DEFAULT FALSE,
    indicator_swf VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_indicator_onderdeel_config UNIQUE (config_id, indicator_uuid, onderdeel_id)
);
CREATE INDEX IF NOT EXISTS idx_kompas_mapping_config ON kompas_indicator_mapping(config_id);
CREATE INDEX IF NOT EXISTS idx_kompas_mapping_indicator ON kompas_indicator_mapping(indicator_uuid);
CREATE INDEX IF NOT EXISTS idx_kompas_mapping_onderdeel ON kompas_indicator_mapping(onderdeel_id);

-- Tabel: kompas_indicator_extra_tags
CREATE TABLE IF NOT EXISTS kompas_indicator_extra_tags (
    indicator_uuid UUID NOT NULL REFERENCES indicatoren(uuid) ON DELETE CASCADE,
    extra_onderdeel_id INT NOT NULL REFERENCES kompas_extra_onderdelen(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (indicator_uuid, extra_onderdeel_id)
);

-- Tabel: kompas_indicator_scoring_regels
CREATE TABLE IF NOT EXISTS kompas_indicator_scoring_regels (
    id SERIAL PRIMARY KEY,
    indicator_uuid UUID NOT NULL REFERENCES indicatoren(uuid) ON DELETE CASCADE,
    config_id INT NOT NULL REFERENCES kompas_configuraties(id) ON DELETE CASCADE,
    score_type VARCHAR(50) NOT NULL CHECK (score_type IN ('positive_ascending', 'positive_descending', 'threshold_based', 'custom')),
    thresholds JSONB,
    inverse BOOLEAN DEFAULT FALSE,
    eenheid VARCHAR(50),
    doel_waarde FLOAT,
    beschrijving TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_indicator_scoring_per_config UNIQUE (indicator_uuid, config_id)
);

-- ============================================================================
-- SECTION 5: ADMIN TABLES
-- ============================================================================

-- Tabel: color_schemas
CREATE TABLE IF NOT EXISTS color_schemas (
    id SERIAL PRIMARY KEY,
    naam VARCHAR(100) UNIQUE NOT NULL,
    beschrijving TEXT,
    colors JSONB NOT NULL,
    is_actief BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Foreign key toevoegen (na color_schemas bestaat)
ALTER TABLE indicatoren 
    ADD CONSTRAINT fk_color_schema 
    FOREIGN KEY (color_schema_id) 
    REFERENCES color_schemas(id);
CREATE INDEX IF NOT EXISTS idx_indicatoren_color_schema ON indicatoren(color_schema_id);

-- ============================================================================
-- SECTION 5.5: USER MANAGEMENT TABLES
-- ============================================================================
-- Vereist voor authenticatie (auth.py) en Admin Panel toegang

-- Tabel: users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = TRUE;

-- Tabel: sessions (HttpOnly cookie-gebaseerde sessies)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

-- Tabel: api_keys (database-gestuurde API sleutels)
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash TEXT UNIQUE NOT NULL,
    label VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- SECTION 6: DATABASE VIEWS
-- ============================================================================

-- View: Basis kaart data (geometrie + metadata, excl. water)
CREATE OR REPLACE VIEW vw_gebied_kaart_basis AS
SELECT 
    g.id,
    g.naam,
    g.gebiedstype_id,
    gt.naam as gebiedstype_naam,
    g.actief,
    ST_AsGeoJSON(ST_Transform(g.geom, 4326))::json as geometry
FROM gebieden g
INNER JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
WHERE g.actief = true 
  AND (g.metadata->>'water' IS NULL OR g.metadata->>'water' != 'JA')
  AND g.naam NOT ILIKE '%buitenwater%'
  AND g.naam NOT ILIKE '%Wadden Sea%'
  AND g.naam NOT ILIKE '%IJsselmeer%';

-- View: Actuele indicator data (meest recente waarde)
CREATE OR REPLACE VIEW vw_gebied_indicator_actueel AS
SELECT DISTINCT ON (gd.gebied_id, gd.indicator_uuid)
    gd.gebied_id,
    gd.indicator_uuid,
    gd.waarde,
    gd.jaar,
    gd.datum,
    gd.bron
FROM gebied_data gd
ORDER BY gd.gebied_id, gd.indicator_uuid, gd.jaar DESC;

-- View: Kompas hiërarchie
CREATE OR REPLACE VIEW v_kompas_hierarchie AS
SELECT 
    kc.id as config_id,
    kc.naam as config_naam,
    kc.icoon as config_icoon,
    kt.id as titel_id,
    kt.naam as titel_naam,
    kt.kleur as titel_kleur,
    kth.id as thema_id,
    kth.naam as thema_naam,
    ko.id as onderdeel_id,
    ko.naam as onderdeel_naam,
    kim.indicator_uuid,
    i.naam as indicator_naam,
    kim.is_actueel,
    kim.weging,
    sr.score_type,
    sr.inverse,
    sr.eenheid,
    sr.doel_waarde
FROM kompas_configuraties kc
JOIN kompas_titels kt ON kc.id = kt.config_id
LEFT JOIN kompas_themas kth ON kt.id = kth.titel_id
LEFT JOIN kompas_onderdelen ko ON kth.id = ko.thema_id
LEFT JOIN kompas_indicator_mapping kim ON ko.id = kim.onderdeel_id AND kim.config_id = kc.id
LEFT JOIN indicatoren i ON kim.indicator_uuid = i.uuid
LEFT JOIN kompas_indicator_scoring_regels sr ON kim.indicator_uuid = sr.indicator_uuid AND sr.config_id = kc.id
WHERE kc.is_actief = TRUE
ORDER BY kc.id, kt.volgorde, kth.volgorde, ko.volgorde, i.naam;

-- View: Kompas configuratie statistieken
CREATE OR REPLACE VIEW v_kompas_config_stats AS
SELECT 
    kc.id,
    kc.naam,
    kc.beschrijving,
    kc.is_standaard,
    kc.is_actief,
    kc.icoon,
    COUNT(DISTINCT kth.id) as aantal_themas,
    COUNT(DISTINCT ko.id) as aantal_onderdelen,
    COUNT(DISTINCT kim.indicator_uuid) as aantal_indicatoren,
    COUNT(sr.id) as aantal_scoring_regels
FROM kompas_configuraties kc
LEFT JOIN kompas_titels kt ON kc.id = kt.config_id
LEFT JOIN kompas_themas kth ON kt.id = kth.titel_id
LEFT JOIN kompas_onderdelen ko ON kth.id = ko.thema_id
LEFT JOIN kompas_indicator_mapping kim ON ko.id = kim.onderdeel_id AND kim.config_id = kc.id
LEFT JOIN kompas_indicator_scoring_regels sr ON kim.indicator_uuid = sr.indicator_uuid AND sr.config_id = kc.id
WHERE kc.is_actief = TRUE
GROUP BY kc.id, kc.naam, kc.beschrijving, kc.is_standaard, kc.is_actief, kc.icoon
ORDER BY kc.is_standaard DESC, kc.naam;

-- View: Admin indicatoren
CREATE OR REPLACE VIEW v_admin_indicatoren AS
SELECT 
    i.uuid,
    i.naam,
    i.definitie,
    i.bron,
    i.eenheid,
    i.score_type,
    i.color_schema_id,
    cs.naam as color_schema_naam,
    cs.colors as color_schema_colors,
    i.admin_notes
FROM indicatoren i
LEFT JOIN color_schemas cs ON i.color_schema_id = cs.id;

-- View: Score types documentatie
CREATE OR REPLACE VIEW v_score_types AS
SELECT 
    '+/+' as code, 
    'Positive Ascending' as naam,
    'Hoge waarde = Goed (Groen)' as beschrijving,
    'Inkomen, Levensverwachting' as voorbeelden
UNION ALL SELECT 
    '+/-', 
    'Positive Descending',
    'Hoge waarde = Slecht (Rood)',
    'Werkloosheid, Schulden'
UNION ALL SELECT 
    '-/+', 
    'Negative Ascending',
    'Lage waarde = Goed (Groen)',
    'Criminaliteit, Overlast'
UNION ALL SELECT 
    '-/-', 
    'Negative Descending',
    'Lage waarde = Slecht (Rood)',
    'Vaccinatiegraad, Participatie';

-- ============================================================================
-- SECTION 7: TRIGGERS
-- ============================================================================

CREATE TRIGGER trigger_gebiedstypes_updated_at
    BEFORE UPDATE ON gebiedstypes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_gebieden_updated_at
    BEFORE UPDATE ON gebieden
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_indicatoren_updated_at
    BEFORE UPDATE ON indicatoren
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_gebied_data_updated_at
    BEFORE UPDATE ON gebied_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_gemeenten_updated_at
    BEFORE UPDATE ON gemeenten
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_gebieden_centroid
    BEFORE INSERT OR UPDATE OF geom ON gebieden
    FOR EACH ROW EXECUTE FUNCTION update_gebied_centroid();

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SECTION 8: SEED DATA
-- ============================================================================

INSERT INTO gebiedstypes (id, naam, code, beschrijving, bron, niveau) VALUES
    ('afba67cb-6b38-4723-9c95-102a22d5b38a', 'CBS Buurten', 'CBS_BUURT', 
     'Buurtindelingen volgens het Centraal Bureau voor de Statistiek', 
     'CBS', 'Buurt'),
    ('29fc9f28-89d9-488b-bf68-2ed176187b21', 'Welstandsgebieden', 'WELSTAND', 
     'Welstandsgebieden zoals gedefinieerd in de welstandsnota', 
     'Gemeente', 'Gebied')
ON CONFLICT (id) DO NOTHING;

INSERT INTO gemeenten (code, naam, provincie, is_eiland) VALUES
    ('0059', 'Achtkarspelen', 'Fryslân', false),
    ('0060', 'Ameland', 'Fryslân', true),
    ('1891', 'Dantumadiel', 'Fryslân', false),
    ('1940', 'De Fryske Marren', 'Fryslân', false),
    ('0072', 'Harlingen', 'Fryslân', false),
    ('0074', 'Heerenveen', 'Fryslân', false),
    ('0080', 'Leeuwarden', 'Fryslân', false),
    ('1970', 'Noardeast-Fryslân', 'Fryslân', false),
    ('0085', 'Ooststellingwerf', 'Fryslân', false),
    ('0086', 'Opsterland', 'Fryslân', false),
    ('0088', 'Schiermonnikoog', 'Fryslân', true),
    ('0090', 'Smallingerland', 'Fryslân', false),
    ('1900', 'Súdwest-Fryslân', 'Fryslân', false),
    ('0093', 'Terschelling', 'Fryslân', true),
    ('0737', 'Tytsjerksteradiel', 'Fryslân', false),
    ('0096', 'Vlieland', 'Fryslân', true),
    ('1949', 'Waadhoeke', 'Fryslân', false),
    ('0098', 'Weststellingwerf', 'Fryslân', false)
ON CONFLICT (code) DO NOTHING;

INSERT INTO color_schemas (naam, beschrijving, colors) VALUES
    ('default', 'Standaard rood-geel-groen', 
     '{"min": "#ef4444", "mid": "#fbbf24", "max": "#10b981"}'),
    ('blue-red', 'Blauw naar rood', 
     '{"min": "#3b82f6", "mid": "#a855f7", "max": "#ef4444"}'),
    ('green-brown', 'Groen naar bruin (natuur)', 
     '{"min": "#10b981", "mid": "#84cc16", "max": "#a16207"}'),
    ('monochrome', 'Grijstinten', 
     '{"min": "#1f2937", "mid": "#6b7280", "max": "#e5e7eb"}')
ON CONFLICT (naam) DO NOTHING;

INSERT INTO kompas_configuraties (id, naam, beschrijving, is_standaard, is_actief, icoon) VALUES
    (1, 'Volledig Kompas', 
     'Complete overzicht van alle indicatoren over alle thema''s. Geeft een 360° beeld van de leefomgeving.',
     TRUE, TRUE, '🌍')
ON CONFLICT (naam) DO NOTHING;

SELECT setval('kompas_configuraties_id_seq', (SELECT COALESCE(MAX(id), 1) FROM kompas_configuraties));

-- ============================================================================
-- SECTION 9: TABLE COMMENTS
-- ============================================================================

COMMENT ON TABLE gebiedstypes IS 'Verschillende soorten gebiedsindelingen (CBS buurten, wijken, etc.)';
COMMENT ON TABLE gemeenten IS 'Nederlandse gemeenten met CBS codes, initieel gevuld met Friese gemeenten';
COMMENT ON TABLE gebieden IS 'Specifieke gebieden met hun geometrie en metadata';
COMMENT ON TABLE indicatoren IS 'KPIs en meetwaarden met uitgebreide metadata';
COMMENT ON TABLE gebied_data IS 'Feitelijke metingen/waarden per gebied en indicator';
COMMENT ON TABLE kompas_configuraties IS 'Master configuraties voor meerdere kompas varianten';
COMMENT ON TABLE kompas_titels IS 'Niveau 1 van Kompas hiërarchie - Hoofd categorieën';
COMMENT ON TABLE kompas_themas IS 'Niveau 2 van Kompas hiërarchie - Themas per titel';
COMMENT ON TABLE kompas_onderdelen IS 'Niveau 3 van Kompas hiërarchie - Onderdelen per thema';
COMMENT ON TABLE color_schemas IS 'Kleurschemas voor kaart visualisatie en kompas';
COMMENT ON TABLE users IS 'Applicatiegebruikers voor Admin Panel en beheerscherm';
COMMENT ON TABLE sessions IS 'Actieve inlogsessies via HttpOnly cookies (12 uur geldig)';
COMMENT ON TABLE api_keys IS 'Gehashte API sleutels voor script/ETL toegang tot admin endpoints';
COMMENT ON COLUMN gebieden.geom IS 'Geometrie in RD New (EPSG:28992) coördinatensysteem';
COMMENT ON COLUMN gebieden.geom_centroid IS 'Automatisch berekend zwaartepunt voor kaartweergave';
COMMENT ON COLUMN gebieden.gemeente_code IS 'CBS gemeente code waar dit gebied toe behoort';
COMMENT ON COLUMN indicatoren.score_type IS '+/+ = hoog is goed, +/- = hoog is slecht, etc.';
COMMENT ON COLUMN gebied_data.scenario_id IS 'Scenario identifier (current, 2030, 2050, etc.)';
COMMENT ON COLUMN users.hashed_password IS 'Bcrypt gehashed wachtwoord — nooit plain text opslaan';
COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash van de API key — plain key wordt nooit opgeslagen';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    table_count INTEGER;
    view_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views
    WHERE table_schema = 'public';
    
    RAISE NOTICE '';
    RAISE NOTICE '=======================================================';
    RAISE NOTICE 'D-OMNITWIN DATABASE INITIALIZATION COMPLETE';
    RAISE NOTICE '=======================================================';
    RAISE NOTICE '   Tabellen aangemaakt: %', table_count;
    RAISE NOTICE '   Views aangemaakt: %', view_count;
    RAISE NOTICE '';
    RAISE NOTICE '   Volgende stappen:';
    RAISE NOTICE '   1. Seed data laden:   python init_data/scripts/seed_fryslan.py --stap alle';
    RAISE NOTICE '   2. Admin aanmaken:    python init_data/scripts/create_admin.py';
    RAISE NOTICE '   3. App starten:       python run_dev.py';
    RAISE NOTICE '=======================================================';
END $$;
