#!/bin/bash
set -e
cd ~/cholera-app/backend
# Py3.13-safe requirements: bump pins that lack 3.13 wheels / need Rust.
python3 - <<'PY'
import re
lines=open('requirements.txt').read().splitlines()
drop=re.compile(r'^(netCDF4|h5py|google-antigravity)([=<>]|$)')
bump={
 'pydantic':'pydantic>=2.9',
 'pydantic-settings':'pydantic-settings>=2.4',
 'psycopg2-binary':'psycopg2-binary>=2.9.10',
 'fastapi':'fastapi>=0.115',
 'uvicorn[standard]':'uvicorn[standard]>=0.46',
 'sqlalchemy':'sqlalchemy>=2.0.36',
 'httpx':'httpx>=0.27',
 'numpy':'numpy>=2.1',
 'sentry-sdk[fastapi]':'sentry-sdk[fastapi]>=2.0',
 'alembic':'alembic>=1.14',
 'geoalchemy2':'geoalchemy2>=0.15',
}
out=[]
for ln in lines:
    s=ln.strip()
    if not s or s.startswith('#'): out.append(ln); continue
    if drop.match(s): continue
    name=re.split(r'[=<>\[]',s)[0]
    key=s.split('==')[0]  # includes extras
    if key in bump: out.append(bump[key]); continue
    if name in bump: out.append(bump[name]); continue
    out.append(ln)
open('requirements.vps.txt','w').write('\n'.join(out)+'\n')
print('written requirements.vps.txt')
PY
echo "=== key pins now ==="; grep -iE 'pydantic|psycopg|fastapi|uvicorn|sqlalchemy|httpx|numpy' requirements.vps.txt
rm -rf venv; python3 -m venv venv
./venv/bin/pip install -q --upgrade pip wheel
echo "=== install ==="
./venv/bin/pip install -q -r requirements.vps.txt 2>&1 | tail -15
echo "=== migrations ==="
set +e
./venv/bin/alembic upgrade head 2>&1 | tail -6
RC=$?
set -e
[ $RC -ne 0 ] && { echo "alembic fail -> init_db"; ./venv/bin/python -c "from app.database import init_db; init_db()"; }
echo "=== EE ADC check ==="
GOOGLE_APPLICATION_CREDENTIALS=/home/debian/cholera-app/backend/adc.json \
./venv/bin/python -c "
from app.services.earth_engine import EarthEngineService
s=EarthEngineService(); print('configured:',s.is_configured()); print('authenticated:',s.authenticate())
"
echo "DEPLOY_SETUP_DONE"
