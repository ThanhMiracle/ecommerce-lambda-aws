# syntax=docker/dockerfile:1.6

FROM python:3.11-slim

# Runtime & pip optimizations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Uncomment ONLY if requirements need native compilation
# (e.g. numpy, pandas, psycopg2, cryptography)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#       build-essential \
#     && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for layer caching
COPY product-service/requirements.txt /app/requirements.txt

# Use BuildKit cache to speed up pip installs
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/requirements.txt

# Copy application code last
COPY product-service/app /app/app
COPY shared /app/shared

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
