-- ============================================================
-- Migratie v21: Z-score-referentiefuncties (#66)
--
-- Eén bron voor gemiddelde, standaarddeviatie en n van de referentiegroep:
-- zscore_referentie_waarden, zscore_referentie_stats, zscore en zscore_gebieden.
-- De definitie staat in init_data/schema/08_zscore_referentie.sql; deze migratie
-- laadt dat bestand (idempotent, alleen CREATE OR REPLACE).
--
-- Nieuwe database: docker-entrypoint.sh laadt deze migratie bij de init.
-- Bestaande database, vanuit de root van de repository:
--   psql -h <host> -U <user> -d <db> -v ON_ERROR_STOP=1 -f migrations/schema_v21_zscore_referentie.sql
-- ============================================================

\ir ../init_data/schema/08_zscore_referentie.sql
