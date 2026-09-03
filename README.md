# Nigeria EO-Enabled Environmental Health Intelligence Hub — Cholera Surveillance

Earth Observation–enabled cholera surveillance platform for Nigeria: a FastAPI/PostGIS backend,
React dashboard, Google Earth Engine covariate pipeline, and a measured, schema-grounded AI
Surveillance Copilot. Developed at NASRDA (National Space Research and Development Agency)
Mission Planning & Satellite Data Management.

**Live demo:** https://cholera.abokiwise.ai (mobile-friendly; demo auto-login)

**Manuscript:** `docs/paper/CHOLERA_PAPER_V9_GEE.docx` / `.pdf`

## What this is

A surveillance platform built on two strictly separated evidence tiers:

- **National tier — state-level official data.** 1,233 verified state-level cumulative
  cholera records (2021–2025), systematically extracted from 84 of 93 published NCDC
  Cholera Situation Reports (90.3% coverage). Every row passed an arithmetic integrity
  gate (deaths/cases ×100 must reconcile with the report's stated CFR within 0.15pp),
  carries a confidence tier, and is traceable to its exact source PDF.
- **Sentinel tier — LGA-level pilot.** A 2021 Cross River line-list (74 suspected
  cases, 4 deaths, 1 culture-confirmed) across four LGAs (Yakurr, Biase, Calabar
  Municipal, Bakassi), joined to GRID3 Admin-2 boundaries.

No synthetic or simulated epidemiological values anywhere. A candidate national LGA
panel was inspected, found irreconcilable with official totals, and excluded in full.

## Repository layout

```
backend/            FastAPI + SQLAlchemy + PostGIS
  app/              models, routers, services (Earth Engine, risk, agents)
  alembic/          migrations
  data/
    boundaries/     GRID3 774-LGA + state GeoJSON
    cholera_real/   verified v2 NCDC state dataset + provenance/CHANGELOG
  tests/            pytest suite (adapters, routers, services, correlation)
frontend/           React + Vite + Tailwind dashboard (mobile-responsive)
analysis/gee/       live GEE extraction scripts + frozen pilot covariates CSV
deploy/             VPS setup, systemd unit, nginx site, smoke test
docs/paper/        manuscript (V9) + figures
```

## Data sources

| Layer | Source | Status |
|---|---|---|
| National cholera burden | NCDC Cholera SitReps 2021–2025 (84/93 parsed) | Verified state-level series (`backend/data/cholera_real/final_state_cholera_dataset_v2.csv`) |
| Sentinel line-list | Cross River SMoH 2021 line-list | Ingested; pilot validation only |
| Administrative boundaries | GRID3 Nigeria Admin-2 (774 LGAs) | Observed |
| Precipitation | NASA GPM-IMERG v07 via Google Earth Engine | Computed live for pilot LGAs (`analysis/gee/`) |
| Surface water (NDWI) | Sentinel-2 SR Harmonized via GEE | Computed live |
| Vegetation (NDVI) | Sentinel-2 + Landsat-8 C2 L2 (cross-sensor) | Computed live |
| Flood history | Groundsource dated flood archive (2.65M polygons, 2000–2026) | 191 events joined to pilot LGAs |
| Health facilities | FMOH registry (46,146 records, source count) | Observed (unvalidated) |

## Quick start

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set DATABASE_URL, provider keys as needed
alembic upgrade head
uvicorn app.main:app --reload  # http://localhost:8000/docs

# Frontend
cd ../frontend
npm install
npm run dev                    # http://localhost:5173

# Seed verified state-level data (optional)
python -m app.seed_state_cholera
```

GEE covariates: `analysis/gee/extract_gee_covariates.py` (requires `earthengine-api`
and an Earth Engine–registered project; see the file's provenance notes).

## Deployment

`deploy/` contains the working production assets from the live demo host:
`setup_vps.sh` (dependency + DB + service bootstrap), `cholera-backend.service`
(systemd), `cholera-nginx.conf` (TLS site), `smoke_e2e.sh`.

## Testing

```bash
cd backend && pytest
```

## Attribution

NASRDA Mission Planning and Satellite Data Management. Manuscript citation:
Warekuromor T., Olumide A. M., & Umar Y. T. (2026). *Development and Pilot Validation
of a Scalable Earth Observation-Enabled Environmental Health Intelligence Hub for
Cholera Surveillance in Nigeria.* Manuscript V9.
