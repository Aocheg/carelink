#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Starting CARELINK Clinical Continuity Platform           "
echo "=========================================================="

# Check and wait for database connectivity
echo "==> Verifying database connectivity..."
python - << 'EOF'
import os
import sys
import time
from sqlalchemy import create_engine, text

db_url = os.getenv("DATABASE_URL", "sqlite:///./carelink.db")
connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
max_retries = int(os.getenv("DB_CONNECT_RETRIES", "30"))
delay = float(os.getenv("DB_CONNECT_DELAY", "2.0"))

masked_url = db_url.split("@")[-1] if "@" in db_url else db_url
print(f"Connecting to database endpoint: {masked_url}")

connected = False
for attempt in range(1, max_retries + 1):
    try:
        engine = create_engine(db_url, connect_args=connect_args)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"Database connection verified (attempt {attempt}).")
        connected = True
        break
    except Exception as exc:
        print(f"Waiting for database ({attempt}/{max_retries}): {exc}")
        time.sleep(delay)

if not connected:
    print("Error: Database connection timeout reached.", file=sys.stderr)
    sys.exit(1)
EOF

echo "==> Running database migrations with Alembic..."
alembic upgrade head

if [ "${SEED_DEMO_DATA,,}" = "true" ] || [ "${SEED_DEMO_DATA}" = "1" ]; then
    echo "==> Running demo data seeder (if not already seeded)..."
    python -m app.database.seed || echo "Seeder finished or dataset already present."
fi

echo "==> Starting web application server..."
exec "$@"
