# D-OmniTwin — backend-image (ook gebruikt door db-init)
#
# Twee stages (#157):
#   bouw     installeert de Python-pakketten in /opt/venv en downloadt het
#            embeddingmodel; compilers en pip-downloads blijven hier achter
#   runtime  python:3.11-slim met alleen psql, de venv, het model en de code
#
# Geen systeem-GDAL nodig: fiona en pyproj brengen GDAL en PROJ mee in hun wheel.
# ETL-pakketten (geopandas, pandas, Excel, plots) zitten niet in de image:
# zie requirements-etl.txt.

# ── Bouwstage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS bouw

# Compilers alleen voor het geval een pakket geen wheel heeft (nu: allemaal wheels)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# requirements.lock is gegenereerd uit requirements.txt (commando staat bovenin
# het lockbestand). PyTorch komt van de CPU-index: geen CUDA-wheels van GBs.
COPY requirements.lock /tmp/requirements.lock
# Na de installatie weg: de delen van PyTorch die alleen dienen voor C++-extensies
# en de eigen testsuite (circa 0,2 GB; de backend doet alleen inferentie op de CPU),
# en pip/setuptools (niet nodig in de runtime)
RUN pip install --require-hashes \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r /tmp/requirements.lock \
    && T=/opt/venv/lib/python3.11/site-packages/torch \
    && rm -rf "$T/include" "$T/share/cmake" "$T/test" \
    && find "$T/bin" -type f ! -name torch_shm_manager -delete \
    && pip uninstall -y pip setuptools

# Embeddingmodel voor AI-zoeken (#118): gepinde revisie (circa 90 MB).
# Model en revisie staan in services/embedding_model.py; los gekopieerd zodat deze
# laag alleen opnieuw draait als dat bestand verandert.
ENV EMBEDDING_MODEL_PAD=/opt/models/all-MiniLM-L6-v2 \
    HF_HUB_DISABLE_TELEMETRY=1
COPY services/embedding_model.py /tmp/embedding_model.py
RUN python /tmp/embedding_model.py \
    && rm -rf /root/.cache/huggingface "$EMBEDDING_MODEL_PAD/.cache"

# ── Runtime ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# psql voor docker-entrypoint.sh (wachten op de database, schema laden);
# libexpat1 voor de GDAL in de fiona-wheel (manylinux verwacht die van het systeem)
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=bouw /opt/venv /opt/venv
# Buiten /app, zodat de bind-mount van de repo in dev het model niet verbergt
COPY --from=bouw /opt/models /opt/models

# Vanaf hier geen HuggingFace-verkeer meer: backend en db-init draaien offline
ENV PATH=/opt/venv/bin:$PATH \
    EMBEDDING_MODEL_PAD=/opt/models/all-MiniLM-L6-v2 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

WORKDIR /app

# Copy source code
COPY . .

# Draai niet als root. De code blijft van root (alleen-lezen voor de app);
# alleen de mappen waarin de app schrijft zijn van de app-gebruiker.
# UID 1000 komt meestal overeen met de ontwikkelaar op Linux (bind-mount in dev).
RUN chmod +x /app/docker-entrypoint.sh \
    && useradd --create-home --uid 1000 app \
    && mkdir -p logs exports data-upload \
    && chown app:app logs exports data-upload
USER app

# Expose port
EXPOSE 8000

# Start server via entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
