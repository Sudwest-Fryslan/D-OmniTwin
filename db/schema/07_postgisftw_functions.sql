-- Functies voor pg_featureserv (OGC API Features "functions").
-- pg_featureserv publiceert automatisch alle set-returning functies in schema postgisftw
-- onder /api/geo/functions/postgisftw.<naam>/items?<param>=<waarde>.
-- Functies geven alleen de kolommen terug die de frontend nodig heeft (geen metadata e.d.).
-- Idempotent: veilig om opnieuw uit te voeren.

CREATE SCHEMA IF NOT EXISTS postgisftw;

-- postgisftw.buurten_in_deelgebied (#68) staat sinds #231 in
-- db/migraties/V030__organisatie.sql: de functie filtert op de gemeentecodes van de
-- eigen organisatie (tabel organisatie), en die tabel bestaat pas na de migraties.
