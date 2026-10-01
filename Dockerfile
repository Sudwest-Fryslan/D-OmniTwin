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

# Copy source code
COPY . .

# Setup entrypoint script
RUN chmod +x /app/docker-entrypoint.sh

# Draai niet als root. De code blijft van root (alleen-lezen voor de app);
# alleen de mappen waarin de app schrijft zijn van de app-gebruiker.
# UID 1000 komt meestal overeen met de ontwikkelaar op Linux (bind-mount in dev).
# /data-cache: cache voor gedownloade open data (volume bron-cache); een nieuw volume neemt de eigenaar over.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p logs exports data-upload /data-cache \
    && chown app:app logs exports data-upload /data-cache
USER app

# Expose port
EXPOSE 8000

# Start server via entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
