# Design: Groundsource Flood Data + Real Cholera Data Integration & Enhancements

**Date:** 2026-07-05
**Status:** Approved (brainstormed) — pending implementation plan
**Scope additions:** Google Groundsource flood events (B — overlay + risk-engine integration), time-lag correlation analytics (i), alerts/early-warning (iii), PDF/CSV reporting (iv)

---

## 1. Context & Goal

The NASRDA Cholera-Environment Correlation & Surveillance System is a GIS-enabled platform for Nigeria at LGA (and ward) level. Stack: FastAPI + SQLAlchemy + PostGIS (`geoalchemy2`) + Alembic backend; React + Vite + TS frontend with an AI workspace shell. Existing services include NASA GPM rainfall, Google Earth Engine satellite (NDWI/flood-extent/LST), a weighted `RiskCalculator`, a CSV/Excel `DataImporter`, and a `SurveillanceAgent` with multi-provider router.

**Scope change (this iteration): nationwide Nigeria.** The current implementation is a Cross River State prototype (18 LGAs, `cross_river_lgas.geojson`, `crs_bbox` in config). The real cholera data is nationwide (766 LGAs, 37 states + FCT) and Groundsource is global, so the system is expanded to all 774 LGAs. This is a foundational change that precedes all other phases.

The current "flood" signal is **satellite-derived** (NDWI + flood extent). There is no historical flood-**event** dataset, and the existing case data is synthetic/placeholder. This integration adds:

1. **Google Groundsource** (2026) — 2,646,302 historical flood events across 175 countries, 2000–2026, extracted from news articles via Gemini. Distributed as a 667 MB Parquet file (CC BY 4.0) on Zenodo (`doi:10.5281/zenodo.18647054`). Schema: `uuid, area_km2, geometry (WKB, EPSG:4326), start_date, end_date`. This provides **reported flood events with spatial footprints and dates** — a complementary signal to satellite NDWI, ideal for the project's time-lag correlation goal.
2. **Real Nigerian cholera data** — monthly per-LGA cholera surveillance CSV (2020–2025, 37 states + FCT, 766 LGAs, 55,585 rows). Columns: `State, LGA, Year, Month, Suspected_Cases, Confirmed_Cases, Deaths, Death_Rate_Percentage, Latitude, Longitude, Classification`. Stored at `backend/data/cholera_real/nigeria_cholera_2020_2025.csv`.
3. **Enhancements** — time-lag correlation analytics, rule-based alerts/early-warning, weekly/monthly PDF/CSV surveillance reports.

**Architecture choice (approved): Approach A — PostGIS-native.** Filter Groundsource to Nigeria at import, store raw `flood_events` rows in PostGIS with geometry. Single source of truth; leverages existing PostGIS stack; keeps raw footprints for map rendering and future queries; additive schema. Nigeria-subset event volume (tens of thousands of rows) is easily manageable.

---

## 1A. Foundational Change: Nationwide LGA Migration

Precedes all other phases. The system moves from an 18-LGA Cross River State prototype to all 774 Nigerian LGAs.

### 1A.1 Boundary data

- **Source:** HDX COD-AB Nigeria (`cod-ab-nga`), ADM2 GeoJSON — 774 LGAs, CC BY 4.0 (OCHA/OSGOF).
- **Files saved to repo:** `backend/data/boundaries/nigeria_lgas_774.geojson` (ADM2, 774 features) and `backend/data/boundaries/nigeria_states.geojson` (ADM1).
- **ADM2 properties used:** `adm2_name` (LGA name), `adm1_name` (state), `adm2_pcode` (e.g. `NG001001`), `area_sqkm`, `center_lat`, `center_lon`.

### 1A.2 LGA model extension

Add columns to `LGA`:
- `state` (String(100), nullable, indexed) — `adm1_name`.
- `pcode` (String(20), nullable, unique) — `adm2_pcode` (replaces the old `code` uniqueness for the national set; `code` kept for backward compat, populated from pcode).
- Keep existing `geometry` (MULTIPOLYGON, SRID 4326), `centroid_lat/lon` (populated from `center_lat/lon`), `area_sq_km` (from `area_sqkm`), `population` (null — not in boundary file), vulnerability defaults.

### 1A.3 Seed replacement

Replace `seed_database.py` Cross River seed with a nationwide loader:
1. Load `nigeria_lgas_774.geojson`; upsert all 774 LGAs (keyed on `pcode`) with geometry, state, centroid, area.
2. `auto_seed_if_empty` in `main.py` calls the new loader. Demo scenario seeding (synthetic cases/env/risk) is gated behind a `SEED_DEMO` env flag (off by default) so production loads real data, not demo.
3. Old `cross_river_lgas.geojson` and `crs_bbox` config retained but unused for the national seed; `crs_bbox` replaced by a `nigeria_bbox` (lat 4–14, lon 3–15) used by the Groundsource importer.

### 1A.4 Name-matching

Cholera-file LGA names (766) match boundary names (774) at 671 exact; the rest are formatting variants (hyphens vs spaces, minor spelling). The existing `DataImporter._find_lga_id` fuzzy matcher (lowercase, space-removal, substring) resolves these. The matcher is extended to also try matching by `pcode` and to disambiguate using the `State` column when an LGA name appears in multiple states.

---

## 2. Data Model & Ingest

### 2.1 New table: `flood_events`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `uuid` | String, unique, indexed | Groundsource event ID |
| `lga_id` | FK → `lgas.id`, nullable, indexed | resolved at import via spatial join; null if no intersection |
| `geometry` | `Geometry('GEOMETRY', srid=4326)` | polygon or buffered point, as-is from source |
| `start_date` | Date, indexed | |
| `end_date` | Date | |
| `duration_days` | Integer | derived: `end - start + 1` |
| `area_km2` | Float | from source |
| `data_source` | String(50) | `"groundsource"` |
| `created_at` | DateTime | |

Indexes: `GIST` on `geometry`; composite `(lga_id, start_date)`.

### 2.2 New table: `alert_rules`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `name`, `description` | String | |
| `metric` | String | `risk_score` \| `flood_event_count` \| `new_cases` \| `cfr` |
| `operator` | String | `>` \| `>=` \| `<` \| `<=` |
| `threshold` | Float | |
| `window_days` | Integer | lookback (0 = latest only) |
| `severity` | String | `warning` \| `critical` |
| `enabled` | Boolean | default true |
| `created_at`, `updated_at` | DateTime | |

### 2.3 Extend `Alert` model

Add columns: `rule_id` (FK → `alert_rules.id`, nullable), `lga_id` (FK → `lgas.id`, nullable for national-level), `triggered_value` (Float), `message` (Text). Existing `status`/`severity`/`timestamp` reused for fired-alert lifecycle.

### 2.4 Groundsource importer — `app/services/groundsource_importer.py`

Idempotent bulk import, invokable via CLI and an admin endpoint:

1. Stream-read the 667 MB Parquet with `pyarrow`, filter to Nigeria bbox (lat 4–14, lon 3–15) → tens of thousands of events.
2. Decode WKB with `shapely`, build a `GeoDataFrame`, ensure EPSG:4326.
3. Spatial-join to LGA polygons (fetch LGA geometries once; in-memory `geopandas.sjoin` or PostGIS `ST_Intersects` bulk upsert). Assign `lga_id` per event; null if no intersection.
4. Bulk upsert into `flood_events` keyed on `uuid` (idempotent re-runs update existing, add new).
5. Compute `duration_days` on insert.

### 2.5 Cholera monthly adapter — extend `DataImporter`

New `CholeraMonthlyAdapter` (or method) maps the real CSV to `CaseReport`:
- `Year` + `Month` → `report_date` (1st of month); derive `epi_week`/`epi_year`.
- `LGA` → fuzzy `LGA.name` match (existing `_find_lga_id`); state column used as a disambiguator if needed.
- `Suspected_Cases` → `suspected_cases` and `new_cases`; `Confirmed_Cases` → `confirmed_cases`; `Deaths` → `deaths`.
- `Classification` → `notes`.
- **Ignore file lat/lon** (state-level for many rows; rely on existing PostGIS LGA geometry for all geo ops).
- Idempotent upsert on `(lga_id, report_date)`.
- Seed script / admin endpoint to bulk-load `backend/data/cholera_real/nigeria_cholera_2020_2025.csv`.

---

## 3. Risk Engine Integration

### 3.1 New component: `flood_event_score`

`RiskCalculator.calculate_flood_event_score(lga_id, as_of_date)`:
- Query `flood_events` where `lga_id = X` and `start_date` within lookback window (default 30 days, configurable).
- Per event: `event_value = recency_weight × area_weight`.
  - `recency_weight = exp(-Δt / 14)`, `Δt` = days since event start (~10-day half-life).
  - `area_weight = normalize(area_km2, 0, 500)` capped at 1.
- `sum = Σ event_value`; score = `1 - exp(-sum)` (diminishing returns; 0.0 if no events).

### 3.2 Weight rebalance

Current weights: flood 0.4 / rain 0.2 / cases 0.3 / vuln 0.1. The satellite flood budget is split to make room for the new event-based signal:

| Component | Weight |
|---|---|
| satellite flood (`flood_score`, NDWI/extent) | 0.25 |
| flood events (`flood_event_score`, new) | 0.20 |
| rainfall | 0.20 |
| cases | 0.25 |
| vulnerability | 0.10 |

Total = 1.00. Weights stored as class constants (mirrors existing pattern); exposed via admin config in a later iteration. `algorithm_version` bumps to `"2.0"` so historical `RiskScore` rows stay comparable.

### 3.3 `RiskScore` model extension

Add column `flood_event_score` (Float, nullable) alongside existing component scores; add `recent_flood_events` (Integer, nullable) raw count for transparency.

### 3.4 Scheduling & backfill

The existing APScheduler risk-recompute job is extended: for each LGA, fetch recent `flood_events`, compute `flood_event_score`, fold into the overall score. No new job. A one-time CLI backfill recomputes `RiskScore` history with v2.0 for dates with flood-event coverage (2020–2025) so trend charts reflect the new model.

---

## 4. Time-Lag Correlation Analytics

Per requirements §B. Honest resolution: cholera data is monthly, so both series are bucketed monthly (not weekly) to avoid comparing precise weekly floods against chunky monthly cholera.

### 4.1 Method

For a selected scope (LGA, state, or national), build two monthly series:
- **Flood series `F[m]`**: count of flood events (and separately total `area_km2`) with `start_date` in month `m`, from `flood_events`.
- **Cholera series `C[m]`**: sum of `new_cases` in month `m`, from `case_reports`.

Compute **Pearson r** at lags `k = 0, 1, 2, 3, 4` months: `r(k) = corr(F[m], C[m+k])`. Peak lag = strongest lead time. Lags are monthly (≈ 4× the weekly lags in the requirements doc); the UI notes this.

### 4.2 Backend

| Endpoint | Purpose |
|---|---|
| `GET /api/analytics/correlation?lga_id=&state=&from=&to=` | Returns per-lag: `pearson_r`, `p_value` (scipy), `n`, plus aligned flood/case series for trend overlays |
| `GET /api/analytics/correlation/export?...&format=csv` | Downloadable correlation table (lags × metrics) — §B.5 |

New `app/services/correlation_service.py` — pure, unit-testable functions: `build_monthly_flood_series(db, scope, from, to)`, `build_monthly_case_series(...)`, `cross_correlate(f, c, lags)`.

### 4.3 Guardrails

- On-demand per scope (bounded, fast — ~72 months × 2 series). State/national aggregates sum component-LGA series first. Cached by `(scope, from, to)` for 1 hour.
- If `n < 6` overlapping months → return `insufficient_data: true` (no misleading r).
- UI banner: *"Correlation is a decision-support signal, not proof of causation."* (§B.6)

### 4.4 Frontend

New `Correlation` view (tab in LGA detail / dashboard): lag bar chart (r by lag), dual-axis flood-vs-cholera trend overlay, "Export CSV" button. Matches the chart library already used by `Dashboard`.

---

## 5. Alerts & Early Warning

Per requirements §F.

### 5.1 Rule engine — `app/services/alert_engine.py`

Run by APScheduler daily (after the risk-recompute job). For each enabled `alert_rule`, for each LGA, evaluate `metric` over `window_days`:
- `risk_score` → latest `RiskScore.score` in window
- `flood_event_count` → count of `flood_events` in window
- `new_cases` → sum of `CaseReport.new_cases` in window
- `cfr` → `deaths/cases` over window

If `metric [operator] threshold` → fire an `Alert` (rule severity, `triggered_value`, auto `message`, `lga_id`). Deduplicate: don't re-fire an active alert for the same `(rule_id, lga_id)` until resolved/cleared.

### 5.2 Default seed rules (admin-editable)

| Rule | Metric | Op | Threshold | Window | Severity |
|---|---|---|---|---|---|
| High risk score | risk_score | ≥ | 0.6 | 0 (latest) | critical |
| Recent flooding | flood_event_count | ≥ | 1 | 14 days | warning |
| Case surge | new_cases | ≥ | 20 | 14 days | critical |
| High case fatality | cfr | ≥ | 0.05 | 14 days | warning |

### 5.3 Backend

- `GET /api/alerts` — list with filters (severity, status, LGA, date range) + pagination
- `GET /api/alerts/rules` · `POST` · `PUT` — rule CRUD
- `PATCH /api/alerts/{id}` — acknowledge/resolve
- `GET /api/alerts/export?format=csv` — exportable alert log (§F.3)

### 5.4 Frontend

Extend existing `Alerts` component dir: alert dashboard (table with status/severity/timestamp/LGA, filter bar, acknowledge action) + rule management view (admin: list/edit/enable-disable).

---

## 6. Reporting & Export

Per requirements §G.

### 6.1 Backend — `app/services/report_service.py` + `app/routers/reports.py`

| Endpoint | Purpose |
|---|---|
| `GET /api/reports/surveillance?period=weekly\|monthly&lga_id=&state=&from=&to=` | Report object: period totals (cases, deaths, CFR), top-10 hotspot LGAs by cases and by risk, flood-event summary, alerts fired, risk-level distribution |
| `GET /api/reports/surveillance/export?...&format=pdf` | PDF via `reportlab` — header, executive summary, hotspot tables, sparklines (matplotlib → PNG embedded), alerts list |
| `GET /api/reports/surveillance/export?...&format=csv` | Multi-section CSV (or zipped CSVs) of underlying tables |

### 6.2 PDF structure (printable executive summary, §G.3)

1. Header: period, scope, generated-at.
2. Executive summary: total cases, deaths, CFR, vs-previous-period delta, # LGAs at each risk level.
3. Top-10 hotspot LGAs by cases + top-10 by risk score.
4. Flood activity summary: events, total area, most-affected LGAs.
5. Alerts fired in period.
6. Methodology footnote (correlation ≠ causation; algorithm version).

### 6.3 Frontend

Extend existing `Export` component dir: "Generate Report" panel (period, scope, date range) → preview summary cards → Download PDF / Download CSV buttons. Reuses `ExportButton` pattern and toast feedback.

---

## 7. Dependencies

Add to `backend/requirements.txt`:
- `pyarrow` — stream-read Groundsource Parquet
- `geopandas` — spatial join (builds on shapely, already present)
- `reportlab` — PDF report generation
- `matplotlib` — sparklines embedded in PDF
- `scipy` — correlation p-values (lightweight, optional but included)

Already present: `geoalchemy2`, `pandas`, `shapely`, `apscheduler`.

---

## 8. Migration & Rollout

Alembic migration(s):
0. Nationwide LGA migration: add `state`, `pcode` to `lgas`; populate 774 LGAs from `nigeria_lgas_774.geojson` (data migration).
1. Create `flood_events` table (with GIST + composite indexes).
2. Create `alert_rules` table.
3. Add `flood_event_score`, `recent_flood_events` to `risk_scores`.
4. Add `rule_id`, `lga_id`, `triggered_value`, `message` to `alerts`.

Seed: default `alert_rules` rows; bulk-load cholera CSV; import Groundsource (Nigeria-filtered); backfill `RiskScore` v2.0.

Each phase is independently testable: ingest → risk → correlation → alerts → reports.

---

## 9. Testing

- Unit: `correlation_service` (series build + cross-correlate, insufficient-data guard), `RiskCalculator.calculate_flood_event_score` (decay/area math, empty case), `alert_engine` (rule evaluation + dedup), `CholeraMonthlyAdapter` (column mapping, date parse, fuzzy LGA match).
- Integration: Groundsource importer idempotency + spatial join; cholera upsert idempotency; alert fire/dedup lifecycle; report PDF/CSV generation.
- End-to-end smoke: import both datasets → recompute risk → view correlation → fire alert → generate report.

---

## 10. Out of Scope (this iteration)

- Real-time/live flood forecasting (Google Flood Hub API) — Groundsource is historical only.
- Outbound email/SMS notifications (§F.4 extension) — dashboard + export only for now.
- Ward-level correlation (LGA-level only, matching data resolution).
- RBAC enforcement on new admin endpoints (auth layer exists; rule CRUD left to a future hardening pass unless trivial to wire).
- Replacing satellite NDWI path (kept alongside flood events — Approach B from the design discussion).
