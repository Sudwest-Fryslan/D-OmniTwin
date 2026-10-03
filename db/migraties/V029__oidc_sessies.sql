-- Inloggen via OIDC (Keycloak) in de beheeromgeving (#251, ADR 0008); idempotent.
--
-- 1. oidc_sessies: sessies van mensen die via Keycloak zijn ingelogd (backend-for-frontend).
--    Het cookie session_token bevat het ruwe token; hier staat alleen de hash (sha256, hex),
--    net als in sessions. De rollen komen uit het laatst ververste access token; dat token zelf
--    wordt niet bewaard. refresh_token en id_token zijn nodig om te verversen en om bij
--    Keycloak uit te loggen; ze verdwijnen met de sessie (uitloggen, verlopen, refresh geweigerd).
--    Geen e-mail of andere profielgegevens: alleen sub en preferred_username (audit).
-- 2. indicatoren.gevalideerd_door_sub/_gebruikersnaam: wie een ontologie goedkeurde als dat een
--    Keycloak-gebruiker was. gevalideerd_door verwijst naar users(id) en blijft voor lokale
--    accounts.

CREATE TABLE IF NOT EXISTS oidc_sessies (
    token_hash      varchar(64) PRIMARY KEY,
    onderwerp       text NOT NULL,                  -- sub
    gebruikersnaam  text,                           -- preferred_username
    rollen          text[] NOT NULL DEFAULT '{}',
    refresh_token   text,
    id_token        text,
    token_verloopt  timestamptz NOT NULL,           -- access token verlopen: eerst verversen
    verloopt        timestamptz NOT NULL,           -- sessie verlopen (refresh token of 12 uur)
    aangemaakt      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_oidc_sessies_verloopt ON oidc_sessies(verloopt);

ALTER TABLE indicatoren ADD COLUMN IF NOT EXISTS gevalideerd_door_sub text;
ALTER TABLE indicatoren ADD COLUMN IF NOT EXISTS gevalideerd_door_gebruikersnaam text;
