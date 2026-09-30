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

# Expose port
EXPOSE 8000

# Start server via entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
