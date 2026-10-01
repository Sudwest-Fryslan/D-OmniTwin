-- =============================================================================
-- D-OmniTwin Schema v13 — Configureerbare Logging Infrastructuur
-- Sprint 17A: Fundament & Server/API Logs
-- Datum: 2026-05-26
-- GitHub Issue: #9
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Tabel: app_logs — Structurele applicatie-logs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_logs (
    id               BIGSERIAL    PRIMARY KEY,
    timestamp        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    level            VARCHAR(10)  NOT NULL,   -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    category         VARCHAR(50)  NOT NULL,   -- SERVER, API, AUTH, KOMPAS, KAART, etc.
    message          TEXT         NOT NULL,
    user_id          VARCHAR(255),            -- username of NULL voor anoniem
    session_id       VARCHAR(255),
    ip_address       VARCHAR(45),             -- IPv4 of IPv6
    endpoint         VARCHAR(255),            -- bijv. /api/kompas/1/hierarchie
    response_time_ms INTEGER,
    extra            JSONB                    -- vrije velden per categorie
);

CREATE INDEX IF NOT EXISTS idx_app_logs_timestamp ON app_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_app_logs_level     ON app_logs (level);
CREATE INDEX IF NOT EXISTS idx_app_logs_category  ON app_logs (category);
CREATE INDEX IF NOT EXISTS idx_app_logs_user_id   ON app_logs (user_id);

-- ---------------------------------------------------------------------------
-- Tabel: log_config — Per-categorie logging configuratie
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS log_config (
    category    VARCHAR(50)  PRIMARY KEY,
    level       VARCHAR(10)  NOT NULL DEFAULT 'INFO',
    enabled     BOOLEAN      NOT NULL DEFAULT TRUE,
    updated_at  TIMESTAMPTZ  DEFAULT NOW(),
    updated_by  VARCHAR(255)
);

-- Standaard configuratie bij initialisatie
INSERT INTO log_config (category, level, enabled, updated_at, updated_by) VALUES
    ('SERVER',   'INFO',    true, NOW(), 'system'),
    ('API',      'INFO',    true, NOW(), 'system'),
    ('AUTH',     'WARNING', true, NOW(), 'system'),
    ('KOMPAS',   'INFO',    true, NOW(), 'system'),
    ('KAART',    'INFO',    true, NOW(), 'system'),
    ('RAPPORT',  'INFO',    true, NOW(), 'system'),
    ('LLM_CHAT', 'WARNING', true, NOW(), 'system'),
    ('DATABASE', 'WARNING', true, NOW(), 'system'),
    ('ADMIN',    'INFO',    true, NOW(), 'system')
ON CONFLICT (category) DO NOTHING;
