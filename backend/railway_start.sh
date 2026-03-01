#!/bin/bash

# Railway startup script - runs migrations then starts the server
set -e

echo "🔍 Checking database connection..."
echo "DATABASE_URL: ${DATABASE_URL:0:30}..."

echo "🩹 Checking alembic_version overlap..."
python - <<'PY'
import os
from sqlalchemy import create_engine, text

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not set; skipping overlap check")
    raise SystemExit(0)

if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(db_url, future=True)
with engine.begin() as conn:
    has_table = conn.execute(text("SELECT to_regclass('public.alembic_version')")).scalar()
    if not has_table:
        print("No alembic_version table yet; skipping overlap check")
        raise SystemExit(0)

    rows = [r[0] for r in conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()]
    print(f"Current alembic_version rows: {rows}")

    # Hotfix for overlap where both ancestor and descendant are present.
    if "055_backfill_ad_image_perf" in rows and "054_add_ad_image_performance_table" in rows:
        conn.execute(
            text(
                "DELETE FROM alembic_version "
                "WHERE version_num = '054_add_ad_image_performance_table'"
            )
        )
        print("Removed stale ancestor revision row: 054_add_ad_image_performance_table")
PY

echo "📦 Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed! Check logs above"
    exit 1
fi

echo "🚀 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
