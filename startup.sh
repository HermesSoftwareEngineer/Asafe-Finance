#!/bin/bash
set -e

# Run Alembic migrations if version files exist
if ls alembic/versions/*.py 1>/dev/null 2>&1; then
  echo "Running database migrations..."
  alembic upgrade head
fi

echo "Starting Asafe Finance on port ${PORT:-8080}..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}" \
  --workers 1 \
  --no-access-log
