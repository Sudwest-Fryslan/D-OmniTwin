-- ============================================================================
-- Schema v15: Externe Kaartlagen Beheersysteem
-- Sprint 18 Track B — Extern Lagen Beheer
-- ============================================================================
-- Configuratietabel voor externe geo-services (WFS, WMS, etc.)
-- Twee laagtypen:
--   1. 'selectie'     → geo-polygonen, klik = selecteer CBS-buurten via ST_Intersects
--   2. 'data_koppel'  → datasets met CBS buurt_code als sleutel (toekomst)
-- ============================================================================

CREATE TABLE IF NOT EXISTS externe_kaartlagen (
    id              SERIAL PRIMARY KEY,
    naam            VARCHAR(100) NOT NULL,
    beschrijving    TEXT,
    laag_type       VARCHAR(20) NOT NULL DEFAULT 'selectie'
                    CHECK (laag_type IN ('selectie', 'data_koppel')),
    bron_type       VARCHAR(20) NOT NULL DEFAULT 'WFS'
                    CHECK (bron_type IN ('WFS', 'WMS', 'GeoJSON')),

    -- Connectie-instellingen
    url             TEXT NOT NULL,
    typename        VARCHAR(100),
    srsname         VARCHAR(20) DEFAULT 'EPSG:28992',
    versie          VARCHAR(10) DEFAULT '2.0.0',

    -- Ruimtelijk filter
    filter_type     VARCHAR(20) DEFAULT 'provincie'
                    CHECK (filter_type IN ('bbox', 'provincie', 'alles')),
    filter_waarde   TEXT,

    -- Koppelveld voor data_koppel type (toekomst)
    koppel_veld     VARCHAR(100),

    -- UI-instellingen
    kleur_lijn      VARCHAR(7) DEFAULT '#8B5CF6',
    kleur_fill      VARCHAR(7) DEFAULT '#8B5CF6',
    opacity         REAL DEFAULT 0.15 CHECK (opacity >= 0 AND opacity <= 1),
    actief          BOOLEAN DEFAULT true,
    volgorde        INTEGER DEFAULT 0,

    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Index op actief + volgorde (frontend query)
CREATE INDEX IF NOT EXISTS idx_externe_kaartlagen_actief
    ON externe_kaartlagen (actief, volgorde);

-- ============================================================================
-- Seed: BAG Woonplaatsen (PDOK)
-- ============================================================================

INSERT INTO externe_kaartlagen
    (naam, beschrijving, laag_type, bron_type, url, typename,
     filter_type, filter_waarde, kleur_lijn, kleur_fill, opacity, volgorde)
VALUES (
    'BAG Woonplaatsen',
    'Woonplaatspolygonen uit de Basisregistratie Adressen en Gebouwen (Kadaster/PDOK). Klik op een woonplaats om onderliggende CBS-buurten te selecteren.',
    'selectie', 'WFS',
    'https://service.pdok.nl/kadaster/bag/wfs/v2_0',
    'bag:woonplaats',
    'provincie', 'Fryslân',
    '#8B5CF6', '#8B5CF6', 0.15, 10
)
ON CONFLICT DO NOTHING;
