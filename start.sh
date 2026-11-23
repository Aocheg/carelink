#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/carelink"

echo "==> Running migrations..."
alembic upgrade head || true

echo "==> Seeding demo clinical data..."
python -m app.database.seed || true

echo "==> Starting CareLink web server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
