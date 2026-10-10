# Database-image: PostgreSQL 15 + PostGIS 3 + pgvector, op Debian 12 (bookworm) (#191).
#
# Tot #191 was de basis postgis/postgis:15-3.5, op Debian 11 (bullseye, end-of-life); pgvector kwam
# daar uit het bevroren archief apt-archive.postgresql.org (#189). postgis/postgis heeft voor
# PostgreSQL 15 geen bookworm-variant, dus nu de officiële postgres:15-bookworm met PostGIS en
# pgvector uit de reguliere PGDG-repository (apt.postgresql.org, staat al in het postgres-image).
#
# PostgreSQL blijft 15: bestaande volumes werken zonder pg_upgrade. PostGIS gaat van 3.5 naar de
# versie in PGDG (3.6); docker-entrypoint.sh (upgrade_postgis) werkt de extensie in de database bij.
# Een nieuwe PostgreSQL-major is een eigen stap met dump/restore (nog niet gepland).
FROM postgres:15-bookworm

ENV POSTGIS_MAJOR=3

# ca-certificates: voor remote rasterbestanden (zoals in postgis/postgis)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR \
        postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR-scripts \
        postgresql-$PG_MAJOR-pgvector \
    && rm -rf /var/lib/apt/lists/*
