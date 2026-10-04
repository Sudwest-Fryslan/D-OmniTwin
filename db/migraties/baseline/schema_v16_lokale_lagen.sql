-- ============================================================================
-- Schema V16: Lokale lagen ondersteuning
-- Sprint 18 Track B4 — Lokale geodata als externe kaartlaag
-- ============================================================================

-- 1. CHECK constraint uitbreiden met 'lokaal' bron_type
ALTER TABLE externe_kaartlagen DROP CONSTRAINT IF EXISTS externe_kaartlagen_bron_type_check;
ALTER TABLE externe_kaartlagen ADD CONSTRAINT externe_kaartlagen_bron_type_check
    CHECK (bron_type IN ('WFS', 'WMS', 'GeoJSON', 'lokaal'));

-- 2. Omgevingsvisie SWF als lokale externe kaartlaag
INSERT INTO externe_kaartlagen
    (naam, beschrijving, laag_type, bron_type, url, typename,
     srsname, versie, filter_type, filter_waarde,
     kleur_lijn, kleur_fill, opacity, actief, volgorde)
VALUES
    ('Omgevingsvisie SWF',
     'Deelgebieden uit de Omgevingsvisie van Súdwest-Fryslân (6 deelgebieden)',
     'selectie', 'lokaal',
     'Deelgebieden_omgevingsvisie.gpkg',
     'demo_gebiedsdata__deelgebieden',
     'EPSG:28992', '1.0',
     'alles', NULL,
     '#E8A838', '#E8A838', 0.15, true, 1)
ON CONFLICT DO NOTHING;
