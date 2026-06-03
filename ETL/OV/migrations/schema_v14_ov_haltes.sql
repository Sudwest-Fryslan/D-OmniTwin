-- =============================================================================
-- D-OmniTwin — Schema v14: OV Haltes
-- Issue #11: feat(etl): OV-haltes ophalen uit OpenStreetMap
-- =============================================================================
-- Aangemaakt: 2026-06-03
-- Doel: Tabellen voor ruwe OSM OV-nodes, gededupliceerde clusters en
--       staging-aggregaten per buurt.
-- =============================================================================

-- Tabel 1: Ruwe OSM nodes — alle opgehaalde halte-nodes bewaren
CREATE TABLE IF NOT EXISTS ov_haltes (
    osm_id        BIGINT PRIMARY KEY,
    naam          TEXT,
    ov_type       TEXT,          -- bus / trein / tram / veerboot / metro
    osm_pt_type   TEXT,          -- platform / stop_position / station / ferry_terminal / bus_stop
    network       TEXT,          -- operator/netwerk (bijv. Arriva, NS)
    ref           TEXT,          -- haltenummer
    gemeente_code TEXT,
    gebied_id     TEXT,          -- = gebieden.id (CBS buurt-code bijv. BU00980903)
    provincie     TEXT CHECK (provincie IN ('FR','GR','DR')),
    geom          geometry(Point, 28992),
    peildatum     DATE DEFAULT CURRENT_DATE,
    tags          JSONB
);

CREATE INDEX IF NOT EXISTS idx_ov_haltes_geom   ON ov_haltes USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_ov_haltes_gebied ON ov_haltes(gebied_id);
CREATE INDEX IF NOT EXISTS idx_ov_haltes_type   ON ov_haltes(ov_type);


-- Tabel 2: Gededupliceerde clusters — indicator-basis
-- Deduplicatie: naam + ov_type + 75m proximity clustering
CREATE TABLE IF NOT EXISTS ov_halte_clusters (
    cluster_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    naam          TEXT,
    ov_type       TEXT,
    n_platforms   INT DEFAULT 1,  -- aantal OSM nodes in dit cluster
    gebied_id     TEXT,            -- = gebieden.id
    gemeente_code TEXT,
    provincie     TEXT CHECK (provincie IN ('FR','GR','DR')),
    geom          geometry(Point, 28992),
    peildatum     DATE DEFAULT CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_ov_clusters_geom   ON ov_halte_clusters USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_ov_clusters_gebied ON ov_halte_clusters(gebied_id);


-- Tabel 3: Staging/verificatietabel — aggregaten per buurt per jaar
CREATE TABLE IF NOT EXISTS ov_haltes_per_buurt (
    gebied_id       TEXT,       -- = gebieden.id
    jaar            INT,
    totaal_haltes   INT DEFAULT 0,
    haltes_bus      INT DEFAULT 0,
    haltes_tram     INT DEFAULT 0,
    haltes_trein    INT DEFAULT 0,
    haltes_veerboot INT DEFAULT 0,
    haltes_metro    INT DEFAULT 0,
    PRIMARY KEY (gebied_id, jaar)
);
