#!/usr/bin/env bash
# End-to-end smoke: load nationwide LGAs → cholera → groundsource → risk → alerts → report
set -euo pipefail
cd "$(dirname "$0")/.."

echo "1. Migrate"
alembic upgrade head

echo "2. Seed alert rules"
python -m app.seed_alert_rules

echo "3. (Ensure LGAs loaded — startup does this; trigger via /api/seed if empty)"

echo "4. Import cholera"
python -m app.seed_cholera

echo "5. Backfill risk v2.0"
python -m app.backfill_risks --start 2020-01-01 --end 2025-12-01

echo "6. Run alert engine"
python -c "from app.database import SessionLocal; from app.services.alert_engine import run_alert_engine; db=SessionLocal(); print(run_alert_engine(db)); db.close()"

echo "7. Smoke endpoints"
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
print('correlation', c.get('/api/analytics/correlation', params={'from_year':2020,'to_year':2025}).status_code)
print('alerts rules', c.get('/api/alerts/rules').status_code)
print('report', c.get('/api/reports/surveillance', params={'from':'2024-06-01','to':'2024-06-30'}).status_code)
"
echo "E2E smoke complete."
