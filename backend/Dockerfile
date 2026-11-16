FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install uv for fast, reproducible dependency installation.
RUN pip install --no-cache-dir uv

# Install dependencies first (better layer caching).
COPY pyproject.toml ./
COPY app ./app
RUN uv pip install --system --no-cache .

# Remaining project files (schema, migrations, config).
COPY cruisealert_schema.sql alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000

# The api service uses this CMD; worker/beat services override it in Railway:
#   worker: celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
#   beat:   celery -A app.workers.celery_app beat --loglevel=info
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
