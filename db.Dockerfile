FROM postgis/postgis:15-3.4

# Installeer de pgvector extensie
RUN apt-get update && apt-get install -y \
    postgresql-15-pgvector \
    && rm -rf /var/lib/apt/lists/*
