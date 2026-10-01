FROM postgis/postgis:15-3.5

# Installeer de pgvector extensie.
# Dit image draait op Debian 11 (bullseye, end-of-life); PGDG heeft bullseye van
# apt.postgresql.org gehaald en bewaart de pakketten op apt-archive.postgresql.org (#189).
RUN sed -i 's#http://apt.postgresql.org/pub/repos/apt#http://apt-archive.postgresql.org/pub/repos/apt#' \
        /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y \
    postgresql-15-pgvector \
    && rm -rf /var/lib/apt/lists/*
