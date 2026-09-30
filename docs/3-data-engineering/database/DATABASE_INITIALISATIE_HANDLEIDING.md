# D-OmniTwin Database Initialisatie Script & Handleiding

> ⚠️ **Verouderd/aanvullend** — de actuele installatie staat in [`docs/9-beheer/installatie.md`](../../9-beheer/installatie.md). In de Docker-installatie richt de service `db-init` de database automatisch in (`docker-entrypoint.sh init`).

**Versie:** 1.0  
**Datum:** 3 februari 2026  
**Doel:** Volledige database opzet voor nieuwe installaties

---

## Inhoudsopgave

1. [Inleiding](#1-inleiding)
2. [Vereisten](#2-vereisten)
3. [Initialisatie Stappen](#3-initialisatie-stappen)
4. [Het Totaalscript](#4-het-totaalscript)
5. [Verificatie](#5-verificatie)
6. [Troubleshooting](#6-troubleshooting)
7. [Backup & Recovery](#7-backup--recovery)

---

## 1. Inleiding

Dit document bevat:
- ✅ Complete database initialisatie script
- ✅ Stap-voor-stap instructies
- ✅ Verificatie queries
- ✅ Troubleshooting guide

**Doelgroep:** Database administrators, DevOps engineers, developers

**Gebruik Cases:**
- 🆕 Nieuwe installatie (development, staging, production)
- 🔄 Database rebuild (na corruptie/migratie)
- 🧪 Test omgeving opzetten

---

## 2. Vereisten

### 2.1 Software Vereisten

| Component | Minimale Versie | Aanbevolen |
|-----------|-----------------|------------|
| **PostgreSQL** | 14.x | 15.x of hoger |
| **PostGIS** | 3.2 | 3.4 of hoger |
| **psql Client** | 14.x | Latest |
| **OS** | Linux | Ubuntu 22.04 LTS |

### 2.2 Hardware Vereisten

| Resource | Development | Production |
|----------|------------|------------|
| **RAM** | 4 GB | 16 GB+ |
| **Disk** | 10 GB | 100 GB+ (SSD) |
| **CPU** | 2 cores | 4+ cores |

### 2.3 Toegangsrechten

Je hebt nodig:
- ✅ `SUPERUSER` privileges (of `CREATEDB` + `CREATEROLE`)
- ✅ Toegang tot server via SSH (voor remote installatie)
- ✅ Firewall toegang (port 5432)

---

## 3. Initialisatie Stappen

### STAP 1: PostgreSQL Installatie (Ubuntu)

```bash
# Update package lijst
sudo apt update

# Installeer PostgreSQL 15 + PostGIS
sudo apt install -y postgresql-15 postgresql-15-postgis-3

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verificatie
sudo systemctl status postgresql
```

**Output (verwacht):**
```
● postgresql.service - PostgreSQL RDBMS
     Loaded: loaded (/lib/systemd/system/postgresql.service)
     Active: active (exited) since Mon 2026-02-03 10:00:00 UTC
```

---

### STAP 2: Database en User Aanmaken

**Als postgres user:**

```bash
# Switch naar postgres user
sudo -i -u postgres

# Start psql
psql
```

**In psql console:**

```sql
-- Creëer database user
CREATE USER omnitwin_user WITH PASSWORD 'jouw_sterke_wachtwoord_hier';

-- Creëer database
CREATE DATABASE omnitwin_db OWNER omnitwin_user;

-- Geef privileges
GRANT ALL PRIVILEGES ON DATABASE omnitwin_db TO omnitwin_user;

-- Verifieer
\l omnitwin_db
\du omnitwin_user

-- Exit psql
\q
```

**⚠️ BELANGRIJK:** Vervang `'jouw_sterke_wachtwoord_hier'` door een sterk wachtwoord (min. 16 chars, mixed case, cijfers, symbolen).

---

### STAP 3: PostGIS Extensie Activeren

```bash
# Connect als omnitwin_user
psql -U omnitwin_user -d omnitwin_db
```

```sql
-- Activeer PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verificatie
SELECT PostGIS_Version();
```

**Verwachte Output:**
```
        postgis_version        
-------------------------------
 3.4 USE_GEOS=1 USE_PROJ=1 ...
```

---

### STAP 4: Download Schema Script

**Optie A: Git Clone**

```bash
cd /tmp
git clone https://github.com/jouw-org/D-OmniTwin.git
cd D-OmniTwin
```

**Optie B: Direct Download (als je het totaalscript hebt)**

```bash
# Kopieer het script uit sectie 4 naar een file
nano /tmp/schema_init.sql
# Plak de inhoud, save (Ctrl+X, Y, Enter)
```

---

### STAP 5: Initialisatie Script Uitvoeren

```bash
# Uitvoeren van schema initialisatie
psql -U omnitwin_user -d omnitwin_db -f /tmp/schema_init.sql

# Als je authentication errors krijgt:
sudo -u postgres psql -d omnitwin_db -f /tmp/schema_init.sql
```

**Tijdens executie zie je:**
```
CREATE EXTENSION
CREATE TABLE
CREATE INDEX
...
NOTICE: ✅ Schema initialisatie complete
```

**Executie Tijd:** ~30-60 seconden (afhankelijk van server specs)

---

## 4. Het Totaalscript

### 4.1 `schema_init.sql` - Volledige Database Opzet

**Bestandslocatie:** `data/schema_init.sql`

```sql
-- ============================================================================
-- D-OMNITWIN DATABASE INITIALIZATION SCRIPT
-- ============================================================================
-- Versie: 1.0 (Consolidatie van alle schema versies)
-- Datum: 3 februari 2026
-- Doel: Volledige database setup voor nieuwe installaties
-- 
-- GEBRUIK:
--   psql -U omnitwin_user -d omnitwin_db -f schema_init.sql
-- ============================================================================

-- ============================================================================
-- SECTION 1: EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';

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

-- Tabel: gebieden
CREATE TABLE IF NOT EXISTS gebieden (
    id VARCHAR(100) PRIMARY KEY,
    gebiedstype_id UUID NOT NULL REFERENCES gebiedstypes(id) ON DELETE RESTRICT,
    naam VARCHAR(255) NOT NULL,
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
    score_type VARCHAR(10) DEFAULT '+/+' CHECK (score_type IN ('+/+', '+/-', '-/+', '-/-')),
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

-- Trigger: Update updated_at bij wijziging
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

-- Trigger: Automatisch centroid berekenen
CREATE TRIGGER trigger_gebieden_centroid
    BEFORE INSERT OR UPDATE OF geom ON gebieden
    FOR EACH ROW EXECUTE FUNCTION update_gebied_centroid();

-- ============================================================================
-- SECTION 8: SEED DATA
-- ============================================================================

-- Seed: Gebiedstypes
INSERT INTO gebiedstypes (id, naam, code, beschrijving, bron, niveau) VALUES
    ('afba67cb-6b38-4723-9c95-102a22d5b38a', 'CBS Buurten', 'CBS_BUURT', 
     'Buurtindelingen volgens het Centraal Bureau voor de Statistiek', 
     'CBS', 'Buurt'),
    ('29fc9f28-89d9-488b-bf68-2ed176187b21', 'Welstandsgebieden', 'WELSTAND', 
     'Welstandsgebieden zoals gedefinieerd in de welstandsnota', 
     'Gemeente', 'Gebied')
ON CONFLICT (id) DO NOTHING;

-- Seed: Color Schemas
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

-- Seed: Standaard Kompas Configuratie
INSERT INTO kompas_configuraties (id, naam, beschrijving, is_standaard, is_actief, icoon) VALUES
    (1, 'Volledig Kompas', 
     'Complete overzicht van alle indicatorenover alle thema''s. Geeft een 360° beeld van de leefomgeving.',
     TRUE, TRUE, '🌍')
ON CONFLICT (naam) DO NOTHING;

-- Reset sequence
SELECT setval('kompas_configuraties_id_seq', (SELECT MAX(id) FROM kompas_configuraties));

-- ============================================================================
-- SECTION 9: TABLE COMMENTS (DOCUMENTATION)
-- ============================================================================

COMMENT ON TABLE gebiedstypes IS 'Verschillende soorten gebiedsindelingen (CBS buurten, wijken, etc.)';
COMMENT ON TABLE gebieden IS 'Specifieke gebieden met hun geometrie en metadata';
COMMENT ON TABLE indicatoren IS 'KPI''s en meetwaarden met uitgebreide metadata';
COMMENT ON TABLE gebied_data IS 'Feitelijke metingen/waarden per gebied en indicator';
COMMENT ON TABLE kompas_configuraties IS 'Master configuraties voor meerdere kompas varianten';
COMMENT ON TABLE kompas_titels IS 'Niveau 1 van Kompas hiërarchie - Hoofd categorieën';
COMMENT ON TABLE kompas_themas IS 'Niveau 2 van Kompas hiërarchie - Thema''s per titel';
COMMENT ON TABLE kompas_onderdelen IS 'Niveau 3 van Kompas hiërarchie - Onderdelen per thema';
COMMENT ON TABLE color_schemas IS 'Kleurschemas voor kaart visualisatie en kompas';

COMMENT ON COLUMN gebieden.geom IS 'Geometrie in RD New (EPSG:28992) coördinatensysteem';
COMMENT ON COLUMN gebieden.geom_centroid IS 'Automatisch berekend zwaartepunt voor kaartweergave';
COMMENT ON COLUMN indicatoren.score_type IS '+/+ = hoog is goed, +/- = hoog is slecht, etc.';
COMMENT ON COLUMN gebied_data.scenario_id IS 'Scenario identifier (current, 2030, 2050, etc.)';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    table_count INTEGER;
    view_count INTEGER;
BEGIN
    -- Count tables
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    
    -- Count views
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views
    WHERE table_schema = 'public';
    
    RAISE NOTICE '';
    RAISE NOTICE '✅ =======================================================';
    RAISE NOTICE '✅ D-OMNITWIN DATABASE INITIALIZATION COMPLETE';
    RAISE NOTICE '✅ =======================================================';
    RAISE NOTICE '   Tabellen aangemaakt: %', table_count;
    RAISE NOTICE '   Views aangemaakt: %', view_count;
    RAISE NOTICE '   PostGIS versie: %', PostGIS_Version();
    RAISE NOTICE '';
    RAISE NOTICE '   Volgende stappen:';
    RAISE NOTICE '   1. Importeer geometrie data: python scripts/import_geometrie.py';
    RAISE NOTICE '   2. Importeer CBS data: python scripts/import_cbs_data.py';
    RAISE NOTICE '  3. Importeer Kompas hiërarchie: python scripts/import_kompas_hierarchie.py';
    RAISE NOTICE '✅ =======================================================';
END $$;
```

---

### 4.2 Creëer het Bestand

```bash
# Kopieer bovenstaande SQL naar bestand
sudo mkdir -p /opt/omnitwin/sql
sudo nano /opt/omnitwin/sql/schema_init.sql
# Plak SQL code, save

# Chown naar juiste user
sudo chown omnitwin_user:omnitwin_user /opt/omnitwin/sql/schema_init.sql
```

---

## 5. Verificatie

### 5.1 Database Structuur Controleren

```bash
psql -U omnitwin_user -d omnitwin_db
```

```sql
-- Check aantal tabellen
SELECT COUNT(*) as total_tables 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- Verwacht: ~20

-- Check views
SELECT COUNT(*) as total_views
FROM information_schema.views 
WHERE table_schema = 'public';
-- Verwacht: ~6

-- Check extensies
SELECT * FROM pg_extension;
-- Verwacht: postgis in lijst

-- Check seed data
SELECT * FROM gebiedstypes;
-- Verwacht: 2 rows (CBS Buurten, Welstandsgebieden)

SELECT * FROM color_schemas;
-- Verwacht: 4 rows (default, blue-red, green-brown, monochrome)

SELECT * FROM kom SELECT * FROM color_schemas;
-- Verwacht: 4 rows (default, blue-red, green-brown, monochrome)

SELECT * FROM kompas_configuraties;
-- Verwacht: 1 row (Volledig Kompas)
```

### 5.2 Spatial Functionaliteit Testen

```sql
-- Test PostGIS geometrie support
SELECT ST_AsText(ST_MakePoint(155000, 463000));
-- Verwacht: POINT(155000 463000)

-- Check spatial indexes
SELECT 
    tablename, 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE indexdef LIKE '%GIST%';
-- Verwacht: idx_gebieden_geom, idx_gebieden_centroid
```

### 5.3 Performance Test

```sql
-- Explain plan voor kaart query (moet GIST index gebruiken)
EXPLAIN ANALYZE
SELECT * FROM gebieden 
WHERE ST_Intersects(
    geom, 
    ST_MakeEnvelope(150000, 460000, 160000, 470000, 28992)
);
-- Check output: "Index Scan using idx_gebieden_geom"
```

---

## 6. Troubleshooting

### Probleem 1: PostGIS Extension Fout

**Error:**
```
ERROR:  could not open extension control file "/usr/share/postgresql/15/extension/postgis.control"
```

**Oplossing:**
```bash
# Herinstalleer PostGIS
sudo apt install --reinstall postgresql-15-postgis-3

# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

### Probleem 2: Permission Denied

**Error:**
```
ERROR:  permission denied for database omnitwin_db
```

**Oplossing:**
```sql
-- Als postgres superuser:
GRANT ALL PRIVILEGES ON DATABASE omnitwin_db TO omnitwin_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO omnitwin_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO omnitwin_user;
```

---

### Probleem 3: Schema Already Exists

**Error:**
```
ERROR:  relation "gebieden" already exists
```

**Oplossing (WAARSCHUWING: Verwijdert alle data!):**
```sql
-- Backup maken eerst!
pg_dump -U omnitwin_user omnitwin_db > /tmp/backup_$(date +%Y%m%d_%H%M%S).sql

-- Drop alle tabellen
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO omnitwin_user;

-- Run init script opnieuw
\i /opt/omnitwin/sql/schema_init.sql
```

---

### Probleem 4: Slow Queries

**Symptoom:** Queries duren >5 seconden

**Diagnose:**
```sql
-- Check missing indexes
SELECT 
    schemaname, 
    tablename, 
    attname, 
    n_distinct, 
    correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND tablename IN ('gebieden', 'gebied_data')
ORDER BY abs(correlation) ASC;
```

**Oplossing:**
```sql
-- Rebuild indexes
REINDEX TABLE gebieden;
REINDEX TABLE gebied_data;

-- Update statistics
ANALYZE gebieden;
ANALYZE gebied_data;
```

---

## 7. Backup & Recovery

### 7.1 Backup Maken

**Volledige database backup:**

```bash
# All-in-one backup (schema + data)
pg_dump -U omnitwin_user \
    -F c \
    -b \
    -v \
    -f "/backups/omnitwin_$(date +%Y%m%d_%H%M%S).backup" \
    omnitwin_db
```

**Alleen schema (geen data):**

```bash
pg_dump -U omnitwin_user \
    --schema-only \
    -f "/backups/schema_only_$(date +%Y%m%d).sql" \
    omnitwin_db
```

### 7.2 Restore vanaf Backup

**Volledige restore:**

```bash
# Drop bestaande database
dropdb -U omnitwin_user omnitwin_db

# Creëer lege database
createdb -U omnitwin_user omnitwin_db

# Restore backup
pg_restore -U omnitwin_user \
    -d omnitwin_db \
    -v \
    /backups/omnitwin_20260203_120000.backup
```

### 7.3 Automated Backup (Cron)

```bash
# Edit crontab
crontab -e

# Voeg toe: Daily backup om 02:00
0 2 * * * /usr/bin/pg_dump -U omnitwin_user -F c -f /backups/omnitwin_$(date +\%Y\%m\%d).backup omnitwin_db

# Voeg toe: Cleanup oude backups (>7 dagen)
0 3 * * * find /backups -name "omnitwin_*.backup" -mtime +7 -delete
```

---

## Samenvatting

### Snelle Setup (TL;DR)

```bash
# 1. Installeer PostgreSQL + PostGIS
sudo apt install -y postgresql-15 postgresql-15-postgis-3

# 2. Creëer database en user
sudo -u postgres psql -c "CREATE USER omnitwin_user WITH PASSWORD 'sterke_wachtwoord';"
sudo -u postgres psql -c "CREATE DATABASE omnitwin_db OWNER omnitwin_user;"

# 3. Run init script
psql -U omnitwin_user -d omnitwin_db -f /path/to/schema_init.sql

# 4. Verify
psql -U omnitwin_user -d omnitwin_db -c "SELECT COUNT(*) FROM gebiedstypes;"

# 5. Import data
python scripts/import_geometrie.py
python scripts/import_cbs_data.py
python scripts/import_kompas_hierarchie.py
```

**Totale Setup Tijd:** ~15 minuten (excl. data import)

---

**Document Versie:** 1.0  
**Laatste Update:** 3 februari 2026  
**Onderhouden door:** Database Team
