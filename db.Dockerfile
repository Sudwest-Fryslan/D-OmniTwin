FROM postgis/postgis:15-3.5

# Installeer de pgvector extensie
RUN apt-get update && apt-get install -y \
    postgresql-15-pgvector \
    && rm -rf /var/lib/apt/lists/*
