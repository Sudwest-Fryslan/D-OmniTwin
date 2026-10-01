-- Auth hardening (#65); idempotent.
--
-- 1. Nieuwe gebruikers zijn standaard géén beheerder. Bestaande gebruikers
--    houden hun huidige is_admin-waarde.
-- 2. Sessietokens staan gehasht (sha256, hex) in sessions.token_hash; het
--    cookie bevat het ruwe token. Bestaande sessies (platte tekst) vervallen:
--    gebruikers loggen opnieuw in.
-- 3. Index op expires_at voor het opruimen van verlopen sessies.

ALTER TABLE users ALTER COLUMN is_admin SET DEFAULT false;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'sessions' AND column_name = 'token'
    ) THEN
        DELETE FROM sessions;
        ALTER TABLE sessions RENAME COLUMN token TO token_hash;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
