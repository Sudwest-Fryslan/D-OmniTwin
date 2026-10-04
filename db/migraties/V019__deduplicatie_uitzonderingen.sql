-- Deduplicatie uitzonderingen: paren die handmatig als "geen duplicaat" zijn gemarkeerd
-- Deze worden uitgesloten bij toekomstige deduplicatie-scans
CREATE TABLE IF NOT EXISTS deduplicatie_uitzonderingen (
    id SERIAL PRIMARY KEY,
    indicator_uuid_1 UUID NOT NULL,
    indicator_uuid_2 UUID NOT NULL,
    gemarkeerd_door VARCHAR(100) DEFAULT 'admin',
    gemarkeerd_op TIMESTAMP DEFAULT NOW(),
    UNIQUE(indicator_uuid_1, indicator_uuid_2)
);

-- Index voor snelle lookups bij het filteren van kandidaten
CREATE INDEX IF NOT EXISTS idx_dedup_uitz_uuid1 ON deduplicatie_uitzonderingen(indicator_uuid_1);
CREATE INDEX IF NOT EXISTS idx_dedup_uitz_uuid2 ON deduplicatie_uitzonderingen(indicator_uuid_2);
