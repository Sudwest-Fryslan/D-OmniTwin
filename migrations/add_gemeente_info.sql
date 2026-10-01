-- ============================================================================
-- MIGRATION: Add Gemeente Information
-- ============================================================================
-- Versie: 1.0
-- Datum: 8 februari 2026
-- Doel: Multi-gemeente support voor D-OmniTwin
-- 
-- Wijzigingen:
--   1. Nieuwe tabel: gemeenten (18 Friese gemeenten)
--   2. Nieuwe kolom: gebieden.gemeente_code (FK naar gemeenten)
--   3. Update bestaande gebieden: set gemeente_code = '1900' (Súdwest-Fryslân)
-- 
-- GEBRUIK:
--   psql -U $DB_USER -d $DB_NAME -f migrations/add_gemeente_info.sql
-- ============================================================================

-- Start transaction
BEGIN;

-- ============================================================================
-- STAP 1: Maak gemeenten tabel
-- ============================================================================

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

COMMENT ON TABLE gemeenten IS 'Nederlandse gemeenten met CBS codes, initieel gevuld met Friese gemeenten';
COMMENT ON COLUMN gemeenten.code IS '4-cijferige CBS gemeente code (bijv. 1900 voor Súdwest-Fryslân)';
COMMENT ON COLUMN gemeenten.is_eiland IS 'TRUE voor eilandgemeenten (Ameland, Schiermonnikoog, Terschelling, Vlieland)';

-- ============================================================================
-- STAP 2: Seed Friese gemeenten (18 stuks, per 1 januari 2026)
-- ============================================================================

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
ON CONFLICT (code) DO UPDATE SET
    naam = EXCLUDED.naam,
    provincie = EXCLUDED.provincie,
    is_eiland = EXCLUDED.is_eiland,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- STAP 3: Voeg gemeente_code en provincienaam kolommen toe aan gebieden tabel
-- ============================================================================

-- Voeg gemeente_code kolom toe (nullable initieel voor migratie)
ALTER TABLE gebieden 
    ADD COLUMN IF NOT EXISTS gemeente_code VARCHAR(4);

-- Voeg provincienaam kolom toe
ALTER TABLE gebieden 
    ADD COLUMN IF NOT EXISTS provincienaam VARCHAR(50);

-- Maak indices voor snelle filtering
CREATE INDEX IF NOT EXISTS idx_gebieden_gemeente ON gebieden(gemeente_code);
CREATE INDEX IF NOT EXISTS idx_gebieden_provincie ON gebieden(provincienaam);

COMMENT ON COLUMN gebieden.gemeente_code IS 'CBS gemeente code waar dit gebied toe behoort';
COMMENT ON COLUMN gebieden.provincienaam IS 'Naam van de provincie (bijv. Fryslân)';

-- ============================================================================
-- STAP 4: Update bestaande gebieden naar Súdwest-Fryslân (1900) + provincie
-- ============================================================================

-- Alle bestaande gebieden zijn van Súdwest-Fryslân, Fryslân
UPDATE gebieden 
SET gemeente_code = '1900',
    provincienaam = 'Fryslân'
WHERE gemeente_code IS NULL;

-- ============================================================================
-- STAP 5: Voeg foreign key constraint toe
-- ============================================================================

-- Pas constraint toe (kan falen als er nog NULL waarden zijn)
ALTER TABLE gebieden 
    ADD CONSTRAINT fk_gebieden_gemeente 
    FOREIGN KEY (gemeente_code) 
    REFERENCES gemeenten(code);

-- ============================================================================
-- STAP 6: Update trigger voor updated_at
-- ============================================================================

CREATE TRIGGER trigger_gemeenten_updated_at
    BEFORE UPDATE ON gemeenten
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    gemeente_count INTEGER;
    gebieden_with_gemeente INTEGER;
    gebieden_without_gemeente INTEGER;
BEGIN
    SELECT COUNT(*) INTO gemeente_count FROM gemeenten;
    SELECT COUNT(*) INTO gebieden_with_gemeente FROM gebieden WHERE gemeente_code IS NOT NULL;
    SELECT COUNT(*) INTO gebieden_without_gemeente FROM gebieden WHERE gemeente_code IS NULL;
    
    RAISE NOTICE '';
    RAISE NOTICE '=======================================================';
    RAISE NOTICE 'GEMEENTE MIGRATIE VOLTOOID';
    RAISE NOTICE '=======================================================';
    RAISE NOTICE '   Gemeenten aangemaakt: %', gemeente_count;
    RAISE NOTICE '   Gebieden met gemeente: %', gebieden_with_gemeente;
    RAISE NOTICE '   Gebieden zonder gemeente: %', gebieden_without_gemeente;
    
    IF gebieden_without_gemeente > 0 THEN
        RAISE WARNING '   ⚠️ Er zijn nog % gebieden zonder gemeente!', gebieden_without_gemeente;
    END IF;
    
    RAISE NOTICE '=======================================================';
END $$;

-- Commit transaction
COMMIT;
