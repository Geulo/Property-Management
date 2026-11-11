# syntax=docker/dockerfile:1
# Property service: accounts and properties. Started from the Assignment 1 template.

# Pinned base: the -slim variant of the same Python as in Assignment 1
FROM python:3.12-slim

# PORT is the default the service listens on; DATABASE_URL and SECRET_KEY are secrets
# and come in at run time (compose, or Container Apps secrets), never baked in here.
ENV PORT=8000 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Unprivileged user the service runs as
RUN useradd --system --no-create-home --uid 10001 appuser

# Dependencies before source: editing app code reuses this cached layer
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Only what the service needs to run: no tests, no .env, no .git (see .dockerignore)
COPY app.py ./
COPY src/ ./src/

USER appuser

EXPOSE 8000

# Docker marks the container unhealthy when /health stops answering 200
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health', timeout=2)" || exit 1

CMD ["python", "app.py"]
