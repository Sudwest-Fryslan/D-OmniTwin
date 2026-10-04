-- ============================================================
-- Migratie v21: Z-score-referentiefuncties (#66) en waterbuurt (#155)
--
-- Eén bron voor gemiddelde, standaarddeviatie en n van de referentiegroep:
-- zscore_referentie_waarden, zscore_referentie_stats, zscore en zscore_gebieden
-- (met minimum-n en terugval, #155). Eén definitie van waterbuurt: is_waterbuurt(),
-- markeer_waterbuurten() en de kaartview vw_gebied_kaart_basis (#155).
-- De definitie staat in db/schema/08_zscore_referentie.sql; deze migratie
-- laadt dat bestand (idempotent: CREATE OR REPLACE, DROP FUNCTION IF EXISTS bij een
-- gewijzigde signatuur, en een UPDATE die alleen ontbrekende watervlaggen zet).
--
-- Nieuwe en bestaande database: de migratierunner (python -m omnitwin.migraties, db-init)
-- past deze migratie één keer toe. Wijzig je 08_zscore_referentie.sql, voeg dan een nieuwe
-- migratie toe met dezelfde \ir-regel (de runner waarschuwt bij een gewijzigde checksum).
-- Handmatig, vanuit de root van de repository:
--   psql -h <host> -U <user> -d <db> -v ON_ERROR_STOP=1 -f db/migraties/V021__zscore_referentie.sql
-- ============================================================

\ir ../schema/08_zscore_referentie.sql
