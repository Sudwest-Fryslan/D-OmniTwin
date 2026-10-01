FROM python:3.11-slim

# Install system dependencies for geo packages and postgres utilities
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install python dependencies
# requirements.lock is gegenereerd uit requirements.txt (commando staat bovenin
# het lockbestand). PyTorch komt van de CPU-index: geen CUDA-wheels van GBs.
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.lock

# Embeddingmodel voor AI-zoeken (#118): gepinde revisie, in de image (circa 90 MB).
# Buiten /app, zodat de bind-mount van de repo in dev het niet verbergt.
# Model en revisie staan in services/embedding_model.py; los gekopieerd zodat deze
# laag alleen opnieuw draait als dat bestand verandert.
ENV EMBEDDING_MODEL_PAD=/opt/models/all-MiniLM-L6-v2 \
    HF_HUB_DISABLE_TELEMETRY=1
COPY services/embedding_model.py /tmp/embedding_model.py
RUN python /tmp/embedding_model.py && rm /tmp/embedding_model.py \
    && rm -rf /root/.cache/huggingface "$EMBEDDING_MODEL_PAD/.cache"
# Vanaf hier geen HuggingFace-verkeer meer: backend en db-init draaien offline
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# Copy source code
COPY . .

# Setup entrypoint script
RUN chmod +x /app/docker-entrypoint.sh

# Draai niet als root. De code blijft van root (alleen-lezen voor de app);
# alleen de mappen waarin de app schrijft zijn van de app-gebruiker.
# UID 1000 komt meestal overeen met de ontwikkelaar op Linux (bind-mount in dev).
RUN useradd --create-home --uid 1000 app \
    && mkdir -p logs exports data-upload \
    && chown app:app logs exports data-upload
USER app

# Expose port
EXPOSE 8000

# Start server via entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
