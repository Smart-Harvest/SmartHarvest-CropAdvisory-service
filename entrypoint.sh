#!/bin/bash
set -e

echo "=== Crop Advisory Service Starting ==="

MAX_RETRIES=30
RETRY=0
WAIT=1

echo "Waiting for database..."
while [ $RETRY -lt $MAX_RETRIES ]; do
    if python -c "
import sys
try:
    import psycopg2
    conn = psycopg2.connect('$DATABASE_URL_SYNC')
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'DB not ready: {e}')
    sys.exit(1)
" 2>/dev/null; then
        echo "Database is ready!"
        break
    fi
    RETRY=$((RETRY + 1))
    echo "Waiting for database... attempt $RETRY/$MAX_RETRIES (sleeping ${WAIT}s)"
    sleep $WAIT
    WAIT=$((WAIT * 2 > 10 ? 10 : WAIT * 2))
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "ERROR: Database not available after $MAX_RETRIES retries"
    exit 1
fi

echo "Running Alembic migrations..."
alembic upgrade head || {
    echo "WARNING: Alembic migration failed, attempting direct table creation..."
    python -c "
from app.database import sync_engine
from app.models import Base
Base.metadata.create_all(bind=sync_engine)
print('Tables created via fallback.')
"
}

echo "Starting Crop Advisory Service on port ${PORT:-8002}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8002} --log-level info
