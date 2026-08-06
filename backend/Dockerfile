# Agent-Plug backend — FastAPI + uv on Python 3.14
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# libpq: langgraph-checkpoint-postgres (psycopg) needs the native libpq
# at runtime — psycopg falls back to its pure-python driver otherwise.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# uv for locked dependency installs (uv.lock is universal — includes
# linux x86_64 wheels for numpy/greenlet/etc., so no compilers needed).
RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first (layer caching: code changes don't re-resolve).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# App code (GeoLite2-Country.mmdb is copied too — GEOIP_DB_PATH default resolves here).
COPY . .

EXPOSE 8000

# Healthcheck for compose depends_on / monitoring.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"

CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
