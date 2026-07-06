# Dashboard Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the dashboard show real, date-aware (latest-available) data and surface the new integration (flood events, real alerts, v2.0 risk components, correlation), removing all mock/random data.

**Architecture:** Backend endpoints gain date-range params and a latest-available default, return v2.0 risk fields, and expose a new `/api/flood-events` router. The frontend gains a shared date-range store, a `DateRangeSelector`, and a rebuilt `DashboardView` (Layout A: KPI row, choropleth + right rail of alerts/floods, two bottom charts). All `Math.random()` and hardcoded mock fallbacks are deleted.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / GeoAlchemy2 / pytest (backend); React 18 / TypeScript / Vite / TanStack Query / Recharts / Leaflet (frontend).

## Global Constraints

- Backend tests run with `cd backend && source venv/bin/activate && PYTHONPATH=. pytest <path> -q`. The existing pattern is `TestClient(app)` against the configured Postgres DB (see `backend/tests/test_agent_router.py`). Follow it.
- The frontend has **no test runner installed**. Frontend tasks are gated by `cd frontend && npm run build` (which runs `tsc && vite build`) and `npm run lint`, plus a manual verification step against the running dev server (http://localhost:5173). Do not introduce vitest in this plan.
- Never reintroduce `Math.random()` or hardcoded LGA fallback data (`Calabar South`, `Odukpani`, etc.) removed in Task 9.
- Keep the agent copilot sidebar mounted globally (out of scope for this plan — see the separate Chatbot Enhancement plan).
- Date semantics: "latest-available" means the window `[max_report_date - 30d, max_report_date]` where `max_report_date = max(CaseReport.report_date)`. Never use `date.today()` as a proxy for data recency.
- Every backend endpoint keeps its existing `@limiter.limit("60/minute")` decorator.

## File Structure

**Backend — create:**
- `backend/app/routers/flood_events.py` — `GET /api/flood-events` list endpoint.
- `backend/tests/test_dashboard_endpoint.py` — date-window + new-field tests.
- `backend/tests/test_flood_events_endpoint.py` — flood-events route tests.
- `backend/tests/test_risk_scores_v2_fields.py` — risk-scores extended-fields tests.

**Backend — modify:**
- `backend/app/schemas/models.py:281` — extend `DashboardSummary`.
- `backend/app/routers/lgas.py:160-218` — date params, latest-available window, real alerts, flood count.
- `backend/app/routers/analytics.py:112-170` — return v2.0 risk fields.
- `backend/app/main.py` — register the flood-events router.

**Frontend — create:**
- `frontend/src/store/dateRangeStore.ts` — zustand date-range store.
- `frontend/src/components/Dashboard/DateRangeSelector.tsx`
- `frontend/src/components/Dashboard/DashboardKpiRow.tsx`
- `frontend/src/components/Dashboard/ActiveAlertsRail.tsx`
- `frontend/src/components/Dashboard/FloodEventsRail.tsx`
- `frontend/src/components/Dashboard/CorrelationChart.tsx`
- `frontend/src/components/Dashboard/RiskBreakdownChart.tsx`

**Frontend — modify:**
- `frontend/src/types/index.ts:53` (RiskScore), `:112` (DashboardSummary) — extend types.
- `frontend/src/hooks/useApi.ts` — date-param hooks + new `useFloodEvents` / `useAlertStats`.
- `frontend/src/hooks/useDashboardLogic.ts` — delete mock fallbacks.
- `frontend/src/components/Dashboard/DashboardView.tsx` — rebuild as Layout A.
- `frontend/src/components/Reports/ReportsView.tsx:75` — remove `|| 18`.

---

### Task 1: Extend `DashboardSummary` schema

**Files:**
- Modify: `backend/app/schemas/models.py:281-292`

**Interfaces:**
- Produces: `DashboardSummary` with new fields `active_alerts_count: int`, `alert_level: str`, `flood_events_count: int`, `applied_window_start: Optional[date]`, `applied_window_end: Optional[date]`, `max_data_date: Optional[date]`. `last_updated` becomes `Optional[datetime]`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_dashboard_endpoint.py`:

```python
"""Tests for the dashboard summary endpoint."""
from datetime import date
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)  # noqa: S101


def test_dashboard_summary_has_v2_fields():
    """GET /api/lgas/dashboard returns the new v2 fields."""
    response = client.get("/api/lgas/dashboard")
    assert response.status_code == 200
    body = response.json()
    for key in (
        "total_lgas", "total_cases", "total_deaths",
        "lgas_high_risk", "lgas_medium_risk", "lgas_low_risk",
        "avg_rainfall_7day", "last_updated",
        "active_alerts_count", "alert_level", "flood_events_count",
        "applied_window_start", "applied_window_end", "max_data_date",
    ):
        assert key in body, f"missing field: {key}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_dashboard_endpoint.py -q`
Expected: FAIL — `KeyError: 'active_alerts_count'` (or similar assertion failure).

- [ ] **Step 3: Extend the schema**

Replace the `DashboardSummary` class at `backend/app/schemas/models.py:281`:

```python
class DashboardSummary(BaseModel):
    """Dashboard summary statistics."""
    total_lgas: int
    total_cases: int
    total_deaths: int
    lgas_high_risk: int
    lgas_medium_risk: int
    lgas_low_risk: int
    avg_rainfall_7day: float
    last_updated: Optional[datetime] = None
    # Real alert engine (replaces derived risk-level counts)
    active_alerts_count: int = 0
    alert_level: str = "green"
    # New integration data
    flood_events_count: int = 0
    # Date-awareness: the window actually queried
    applied_window_start: Optional[date] = None
    applied_window_end: Optional[date] = None
    max_data_date: Optional[date] = None
```

Confirm `Optional` and `date` are imported at the top of `backend/app/schemas/models.py` (they are already used elsewhere in the file; if not, add `from datetime import date, datetime` and `from typing import Optional`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_dashboard_endpoint.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/models.py backend/tests/test_dashboard_endpoint.py
git commit -m "feat(backend): extend DashboardSummary with alert/flood/date-window fields"
```

---

### Task 2: Latest-available date window + date params in `/api/lgas/dashboard`

**Files:**
- Modify: `backend/app/routers/lgas.py:160-218`

**Interfaces:**
- Consumes: `DashboardSummary` from Task 1.
- Produces: `GET /api/lgas/dashboard?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` returning the extended schema, with `applied_window_start/end` and `max_data_date` populated and `last_updated` = real max data date.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_dashboard_endpoint.py`:

```python
def test_dashboard_explicit_date_window():
    """Explicit start/end dates are reflected in applied_window."""
    response = client.get(
        "/api/lgas/dashboard",
        params={"start_date": "2024-01-01", "end_date": "2024-12-31"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["applied_window_start"] == "2024-01-01"
    assert body["applied_window_end"] == "2024-12-31"


def test_dashboard_latest_available_default():
    """With no dates, applied_window_end == max_data_date (latest-available)."""
    response = client.get("/api/lgas/dashboard")
    assert response.status_code == 200
    body = response.json()
    # If there is any case data, the default window ends at max_data_date.
    if body["max_data_date"] is not None:
        assert body["applied_window_end"] == body["max_data_date"]
    else:
        # No data at all: window fields are null, counts are zero.
        assert body["applied_window_start"] is None
        assert body["total_cases"] == 0


def test_dashboard_rejects_bad_dates():
    """Invalid date strings return 422."""
    response = client.get(
        "/api/lgas/dashboard",
        params={"start_date": "not-a-date"},
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_dashboard_endpoint.py -q`
Expected: FAIL — applied_window fields not set / bad-date returns 200 not 422.

- [ ] **Step 3: Rewrite the endpoint**

Replace the body of `get_dashboard_summary` at `backend/app/routers/lgas.py:160` (keep the decorator and signature, add `start_date`/`end_date` query params):

```python
@router.get("/dashboard", response_model=DashboardSummary)
@limiter.limit("60/minute")
def get_dashboard_summary(
    request: Request,
    start_date: Optional[date] = Query(None, description="Window start (ISO)"),
    end_date: Optional[date] = Query(None, description="Window end (ISO)"),
    db: Session = Depends(get_db),
):
    """Get dashboard summary statistics over a date window.

    With no params, defaults to the latest-available 30-day window
    (ending at the most recent CaseReport.report_date).
    """
    # Resolve the date window (latest-available default)
    max_report_date = db.query(func.max(CaseReport.report_date)).scalar()
    if end_date is not None:
        window_end = end_date
    else:
        window_end = max_report_date  # may be None if no case data

    if start_date is not None:
        window_start = start_date
    elif window_end is not None:
        window_start = window_end - timedelta(days=30)
    else:
        window_start = None

    # Count LGAs
    total_lgas = db.query(func.count(LGA.id)).scalar()

    # Cases/deaths over the resolved window
    case_q = db.query(func.sum(CaseReport.new_cases), func.sum(CaseReport.deaths))
    if window_start is not None and window_end is not None:
        case_q = case_q.filter(
            CaseReport.report_date >= window_start,
            CaseReport.report_date <= window_end,
        )
    case_stats = case_q.first()
    total_cases = case_stats[0] or 0
    total_deaths = case_stats[1] or 0

    # Latest risk levels count (unchanged logic)
    subquery = (
        db.query(
            RiskScore.lga_id,
            func.max(RiskScore.score_date).label("max_date"),
        )
        .group_by(RiskScore.lga_id)
        .subquery()
    )
    latest_scores = (
        db.query(RiskScore)
        .join(
            subquery,
            (RiskScore.lga_id == subquery.c.lga_id)
            & (RiskScore.score_date == subquery.c.max_date),
        )
        .all()
    )
    high_risk = sum(1 for rs in latest_scores if rs.level == "red")
    medium_risk = sum(1 for rs in latest_scores if rs.level == "yellow")
    low_risk = sum(1 for rs in latest_scores if rs.level == "green")

    # Average rainfall over latest-available 7d (relative to window_end, not today)
    rain_end = window_end or date.today()
    rain_start = rain_end - timedelta(days=7)
    avg_rainfall = (
        db.query(func.avg(EnvironmentalData.rainfall_mm))
        .filter(
            EnvironmentalData.observation_date >= rain_start,
            EnvironmentalData.observation_date <= rain_end,
        )
        .scalar()
        or 0.0
    )

    return DashboardSummary(
        total_lgas=total_lgas,
        total_cases=total_cases,
        total_deaths=total_deaths,
        lgas_high_risk=high_risk,
        lgas_medium_risk=medium_risk,
        lgas_low_risk=low_risk,
        avg_rainfall_7day=round(avg_rainfall, 2),
        last_updated=max_report_date,  # real max data date, not today
        active_alerts_count=0,  # filled in Task 3
        alert_level="green",    # filled in Task 3
        flood_events_count=0,   # filled in Task 3
        applied_window_start=window_start,
        applied_window_end=window_end,
        max_data_date=max_report_date,
    )
```

Ensure imports at the top of `lgas.py` include `Query`, `Optional`, `date`, `timedelta` (most already present; add any missing).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_dashboard_endpoint.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/lgas.py backend/tests/test_dashboard_endpoint.py
git commit -m "feat(backend): date-aware latest-available window for dashboard endpoint"
```

---

### Task 3: Wire real alerts + flood-events count into the dashboard

**Files:**
- Modify: `backend/app/routers/lgas.py` (the `return DashboardSummary(...)` from Task 2)

**Interfaces:**
- Consumes: `Alert` model (`backend/app/models/alert.py`), `FloodEvent` model (`backend/app/models/flood_event.py`).
- Produces: `active_alerts_count` = count of active alerts; `alert_level` = highest severity among active alerts (`critical`→`red`, else `warning`→`yellow`, else `green`); `flood_events_count` = flood events overlapping the window.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_dashboard_endpoint.py`:

```python
def test_dashboard_alert_and_flood_fields_are_integers():
    """active_alerts_count and flood_events_count are ints (>= 0)."""
    response = client.get("/api/lgas/dashboard")
    body = response.json()
    assert isinstance(body["active_alerts_count"], int)
    assert body["active_alerts_count"] >= 0
    assert isinstance(body["flood_events_count"], int)
    assert body["flood_events_count"] >= 0
    assert body["alert_level"] in ("green", "yellow", "red")
```

- [ ] **Step 2: Run test to verify it fails / passes**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_dashboard_endpoint.py::test_dashboard_alert_and_flood_fields_are_integers -q`
Expected: PASS already (Task 2 returned zeros). The point of this task is to make them **real**, so add a stronger assertion once wired — update the test to assert the fields reflect the DB:

```python
def test_dashboard_alert_count_matches_db():
    from app.models import Alert
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        expected = db.query(Alert).filter(Alert.is_active == True).count()
    finally:
        db.close()
    body = client.get("/api/lgas/dashboard").json()
    assert body["active_alerts_count"] == expected
```

Run again — Expected: FAIL (`active_alerts_count` is 0, not `expected`).

- [ ] **Step 3: Wire real counts**

In `backend/app/routers/lgas.py`, ensure `Alert` and `FloodEvent` are imported:

```python
from app.models import LGA, RiskScore, CaseReport, EnvironmentalData, Alert, FloodEvent
```

Replace the three placeholder fields in the `return DashboardSummary(...)` (Task 2) with computed values. Add this block immediately before the `return`:

```python
    # Real alert engine counts
    active_alerts = db.query(Alert).filter(Alert.is_active == True).all()
    active_alerts_count = len(active_alerts)
    if any(a.severity == "critical" for a in active_alerts):
        alert_level = "red"
    elif any(a.severity == "warning" for a in active_alerts):
        alert_level = "yellow"
    else:
        alert_level = "green"

    # Flood events overlapping the window
    flood_q = db.query(func.count(FloodEvent.id))
    if window_start is not None and window_end is not None:
        flood_q = flood_q.filter(
            FloodEvent.start_date <= window_end,
            FloodEvent.end_date >= window_start,
        )
    flood_events_count = flood_q.scalar() or 0
```

And update the `return` to use them:

```python
        active_alerts_count=active_alerts_count,
        alert_level=alert_level,
        flood_events_count=flood_events_count,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_dashboard_endpoint.py -q`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/lgas.py backend/tests/test_dashboard_endpoint.py
git commit -m "feat(backend): real alert + flood-event counts on dashboard summary"
```

---

### Task 4: Extend `/api/analytics/risk-scores` to return v2.0 fields

**Files:**
- Modify: `backend/app/routers/analytics.py:156-170` (the return list-comprehension)

**Interfaces:**
- Produces: each risk-score dict now includes `flood_event_score`, `recent_flood_events`, `vulnerability_score`, `algorithm_version`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_risk_scores_v2_fields.py`:

```python
"""Tests for v2.0 fields on the risk-scores endpoint."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)  # noqa: S101


def test_risk_scores_return_v2_fields():
    response = client.get("/api/analytics/risk-scores", params={"limit": 5})
    assert response.status_code == 200
    scores = response.json()
    for s in scores:
        for key in (
            "flood_event_score",
            "recent_flood_events",
            "vulnerability_score",
            "algorithm_version",
        ):
            assert key in s, f"missing v2 field: {key}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_risk_scores_v2_fields.py -q`
Expected: FAIL — missing `flood_event_score`.

- [ ] **Step 3: Extend the return dict**

In `backend/app/routers/analytics.py`, replace the list-comprehension dict (around line 156) with:

```python
    return [
        {
            "lga_id": rs.lga_id,
            "lga_name": lga_name,
            "score": rs.score,
            "level": rs.level,
            "score_date": rs.score_date.isoformat(),
            "recent_cases": rs.recent_cases,
            "recent_deaths": rs.recent_deaths,
            "rainfall_mm": rs.rainfall_mm,
            "flood_score": rs.flood_score,
            "case_score": rs.case_score,
            "flood_event_score": rs.flood_event_score,
            "recent_flood_events": rs.recent_flood_events,
            "vulnerability_score": rs.vulnerability_score,
            "algorithm_version": rs.algorithm_version,
        }
        for rs, lga_name in scores
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_risk_scores_v2_fields.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/analytics.py backend/tests/test_risk_scores_v2_fields.py
git commit -m "feat(backend): return v2.0 risk components from risk-scores endpoint"
```

---

### Task 5: New `/api/flood-events` router

**Files:**
- Create: `backend/app/routers/flood_events.py`
- Modify: `backend/app/main.py` (register router)
- Test: `backend/tests/test_flood_events_endpoint.py`

**Interfaces:**
- Produces: `GET /api/flood-events?lga_id=&start_date=&end_date=&limit=` → `list[dict]` of `{id, uuid, lga_id, lga_name, start_date, end_date, duration_days, area_km2, created_at}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_flood_events_endpoint.py`:

```python
"""Tests for the flood-events endpoint."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)  # noqa: S101


def test_flood_events_list_shape():
    response = client.get("/api/flood-events", params={"limit": 5})
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    for e in events:
        for key in (
            "id", "uuid", "lga_id", "lga_name",
            "start_date", "end_date", "duration_days", "area_km2",
        ):
            assert key in e, f"missing field: {key}"


def test_flood_events_limit_cap():
    response = client.get("/api/flood-events", params={"limit": 500})
    assert response.status_code == 422  # limit max is 200


def test_flood_events_lga_filter():
    response = client.get("/api/flood-events", params={"lga_id": 1, "limit": 5})
    assert response.status_code == 200
    for e in response.json():
        assert e["lga_id"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_flood_events_endpoint.py -q`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Create the router**

Create `backend/app/routers/flood_events.py`:

```python
"""Flood events router — exposes Groundsource flood events."""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import FloodEvent, LGA
from app.rate_limit import limiter  # adjust import to match the app's limiter location

router = APIRouter(prefix="/api/flood-events", tags=["flood-events"])


@router.get("", response_model=list[dict])
@limiter.limit("60/minute")
def list_flood_events(
    request: Request,
    lga_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List recent flood events, optionally filtered by LGA and date window."""
    q = db.query(FloodEvent, LGA.name).outerjoin(LGA, FloodEvent.lga_id == LGA.id)
    if lga_id is not None:
        q = q.filter(FloodEvent.lga_id == lga_id)
    if start_date is not None:
        q = q.filter(FloodEvent.end_date >= start_date)
    if end_date is not None:
        q = q.filter(FloodEvent.start_date <= end_date)
    rows = q.order_by(FloodEvent.start_date.desc()).limit(limit).all()

    return [
        {
            "id": fe.id,
            "uuid": fe.uuid,
            "lga_id": fe.lga_id,
            "lga_name": lga_name,
            "start_date": fe.start_date.isoformat() if fe.start_date else None,
            "end_date": fe.end_date.isoformat() if fe.end_date else None,
            "duration_days": fe.duration_days,
            "area_km2": fe.area_km2,
            "created_at": fe.created_at.isoformat() if fe.created_at else None,
        }
        for fe, lga_name in rows
    ]
```

**Verify the limiter import:** check how `lgas.py` imports `limiter` and match it exactly (e.g. `from app.main import limiter` or `from app.rate_limit import limiter`). Use the same import the existing routers use.

- [ ] **Step 4: Register the router**

In `backend/app/main.py`, add the import near the other router imports and register it:

```python
from app.routers import flood_events as flood_events_router
# ...
app.include_router(flood_events_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_flood_events_endpoint.py -q`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/flood_events.py backend/app/main.py backend/tests/test_flood_events_endpoint.py
git commit -m "feat(backend): /api/flood-events router for Groundsource flood events"
```

---

### Task 6: Extend frontend `RiskScore` + `DashboardSummary` types

**Files:**
- Modify: `frontend/src/types/index.ts:53` (RiskScore), `:112` (DashboardSummary)

**Interfaces:**
- Produces: `RiskScore` with `flood_event_score?`, `recent_flood_events?`, `algorithm_version?`; `DashboardSummary` with `active_alerts_count`, `alert_level`, `flood_events_count`, `applied_window_start`, `applied_window_end`, `max_data_date`, and `last_updated` optional.

- [ ] **Step 1: Extend the types**

In `frontend/src/types/index.ts`, add the v2 fields to `RiskScore` (after `vulnerability_score?`):

```typescript
export interface RiskScore {
  id: number;
  lga_id: number;
  lga_name?: string;
  score_date: string;
  score: number;
  level: RiskLevel;
  flood_score?: number;
  rainfall_score?: number;
  case_score?: number;
  vulnerability_score?: number;
  flood_event_score?: number;
  recent_flood_events?: number;
  algorithm_version?: string;
  recent_cases?: number;
  recent_deaths?: number;
  rainfall_mm?: number;
  calculated_at: string;
}
```

Read the existing `DashboardSummary` at `:112` and add the new fields (keep existing ones):

```typescript
export interface DashboardSummary {
  total_lgas: number;
  total_cases: number;
  total_deaths: number;
  lgas_high_risk: number;
  lgas_medium_risk: number;
  lgas_low_risk: number;
  avg_rainfall_7day: number;
  last_updated: string | null;
  active_alerts_count: number;
  alert_level: 'green' | 'yellow' | 'red';
  flood_events_count: number;
  applied_window_start: string | null;
  applied_window_end: string | null;
  max_data_date: string | null;
}
```

- [ ] **Step 2: Typecheck + build**

Run: `cd frontend && npm run build`
Expected: PASS (no type errors). If `tsc` reports errors in components that destructure `DashboardSummary`, leave them — they are fixed in later tasks. If errors are only in `DashboardView.tsx`/`useDashboardLogic.ts`, proceed; otherwise fix the type typo.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat(frontend): extend RiskScore + DashboardSummary types with v2/date fields"
```

---

### Task 7: Date-range store + `apiService` methods + hooks

**Files:**
- Create: `frontend/src/store/dateRangeStore.ts`
- Modify: `frontend/src/hooks/useApi.ts` (apiService + hooks + queryKeys)

**Interfaces:**
- Produces:
  - `dateRangeStore` with `{ start: string|null, end: string|null, setRange(start,end), clear() }` (ISO `YYYY-MM-DD`).
  - `apiService.getDashboardSummary(start?, end?)`, `apiService.getAllRiskScores()`, `apiService.getFloodEvents(params)`, `apiService.getAlertStats()`.
  - Hooks `useDashboard(start,end)`, `useFloodEvents(params)`, `useAlertStats()`.

- [ ] **Step 1: Create the date-range store**

Create `frontend/src/store/dateRangeStore.ts`:

```typescript
import { create } from 'zustand';

interface DateRangeState {
  start: string | null; // ISO YYYY-MM-DD
  end: string | null;
  setRange: (start: string | null, end: string | null) => void;
  clear: () => void;
}

export const useDateRangeStore = create<DateRangeState>((set) => ({
  start: null,
  end: null,
  setRange: (start, end) => set({ start, end }),
  clear: () => set({ start: null, end: null }),
}));
```

- [ ] **Step 2: Extend `apiService`**

In `frontend/src/hooks/useApi.ts`, update `getDashboardSummary` and add methods (insert near the existing ones):

```typescript
  getDashboardSummary: async (start?: string | null, end?: string | null): Promise<DashboardSummary> => {
    const params: Record<string, string> = {};
    if (start) params.start_date = start;
    if (end) params.end_date = end;
    const response = await api.get('/lgas/dashboard', { params });
    return response.data;
  },

  getFloodEvents: async (params?: { lga_id?: number; start_date?: string; end_date?: string; limit?: number }): Promise<FloodEvent[]> => {
    const response = await api.get('/flood-events', { params });
    return response.data;
  },

  getAlertStats: async (): Promise<AlertStats> => {
    const response = await api.get('/alerts/stats/summary');
    return response.data;
  },
```

Add `FloodEvent` and `AlertStats` types to `frontend/src/types/index.ts`:

```typescript
export interface FloodEvent {
  id: number;
  uuid: string;
  lga_id: number | null;
  lga_name: string | null;
  start_date: string | null;
  end_date: string | null;
  duration_days: number | null;
  area_km2: number | null;
  created_at: string | null;
}

export interface AlertStats {
  total_active: number;
  by_severity: { critical: number; warning: number; info: number };
  by_level: { red: number; yellow: number; green: number };
  unacknowledged: number;
  acknowledged: number;
  by_type: Record<string, number>;
}
```

- [ ] **Step 3: Update hooks**

In `frontend/src/hooks/useApi.ts`, replace `useDashboard` and add `useFloodEvents` + `useAlertStats`. Make `queryKeys.dashboard` a function of the range:

```typescript
export function useDashboard(start?: string | null, end?: string | null) {
  return useQuery({
    queryKey: ['dashboard', start ?? null, end ?? null],
    queryFn: () => apiService.getDashboardSummary(start, end),
    staleTime: 2 * 60 * 1000,
    refetchInterval: false,
  });
}

export function useFloodEvents(params?: { lga_id?: number; start_date?: string; end_date?: string; limit?: number }) {
  return useQuery({
    queryKey: ['flood-events', params ?? null],
    queryFn: () => apiService.getFloodEvents(params),
    staleTime: 2 * 60 * 1000,
  });
}

export function useAlertStats() {
  return useQuery({
    queryKey: ['alerts', 'stats'],
    queryFn: apiService.getAlertStats,
    staleTime: 60 * 1000,
  });
}
```

Leave `queryKeys.dashboard` defined for any other consumers, but the hook now uses an inline key.

- [ ] **Step 4: Typecheck + build**

Run: `cd frontend && npm run build`
Expected: PASS. (Existing callers of `useDashboard()` with no args still typecheck since args are optional; they will be updated in Task 13.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/dateRangeStore.ts frontend/src/hooks/useApi.ts frontend/src/types/index.ts
git commit -m "feat(frontend): date-range store + flood-events/alert-stats hooks"
```

---

### Task 8: `DateRangeSelector` component

**Files:**
- Create: `frontend/src/components/Dashboard/DateRangeSelector.tsx`

**Interfaces:**
- Consumes: `useDateRangeStore` (Task 7), `useDashboard` applied window (for the "Data through" badge).
- Produces: a rendered selector with presets (30d, 90d, 12m, custom) that calls `setRange`; shows `Data through: {max_data_date}`.

- [ ] **Step 1: Create the component**

Create `frontend/src/components/Dashboard/DateRangeSelector.tsx`:

```typescript
import { useState } from 'react';
import { useDateRangeStore } from '../../store/dateRangeStore';

const PRESETS: { label: string; days: number }[] = [
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
  { label: '12m', days: 365 },
];

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function DateRangeSelector({ maxDataDate }: { maxDataDate: string | null }) {
  const { start, end, setRange } = useDateRangeStore();
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  // Anchor for presets: the latest-available data date, else today.
  const anchor = maxDataDate ? new Date(maxDataDate) : new Date();

  const applyPreset = (days: number) => {
    const e = new Date(anchor);
    const s = new Date(anchor);
    s.setDate(s.getDate() - days);
    setRange(iso(s), iso(e));
  };

  const applyCustom = () => {
    if (customStart && customEnd) setRange(customStart, customEnd);
  };

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="text-gray-500">Date range:</span>
      {PRESETS.map((p) => (
        <button
          key={p.label}
          onClick={() => applyPreset(p.days)}
          className="px-2 py-1 rounded border border-gray-300 hover:bg-gray-100"
        >
          {p.label}
        </button>
      ))}
      <input type="date" value={customStart} onChange={(e) => setCustomStart(e.target.value)} className="border border-gray-300 rounded px-1 py-0.5" />
      <span>–</span>
      <input type="date" value={customEnd} onChange={(e) => setCustomEnd(e.target.value)} className="border border-gray-300 rounded px-1 py-0.5" />
      <button onClick={applyCustom} className="px-2 py-1 rounded border border-gray-300 hover:bg-gray-100">Apply</button>
      <button onClick={() => setRange(null, null)} className="px-2 py-1 rounded border border-gray-300 hover:bg-gray-100">Latest</button>
      {maxDataDate && (
        <span className="ml-2 text-gray-400">Data through: {maxDataDate}</span>
      )}
      {(start || end) && (
        <span className="text-gray-400">
          ({start ?? '…'} → {end ?? '…'})
        </span>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Typecheck + build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Dashboard/DateRangeSelector.tsx
git commit -m "feat(frontend): DateRangeSelector with presets + custom range"
```

---

### Task 9: Delete mock fallbacks from `useDashboardLogic`

**Files:**
- Modify: `frontend/src/hooks/useDashboardLogic.ts:11-15, 46-55, 76-82`

**Interfaces:**
- Produces: `useSatelliteFeedLogic`, `useChartDataLogic`, `useRiskChartLogic` return empty/real data only — never mock arrays or `Math.random()`.

- [ ] **Step 1: Remove mock fallbacks**

In `frontend/src/hooks/useDashboardLogic.ts`:

- `useSatelliteFeedLogic`: replace the `if (!satelliteData || satelliteData.length === 0) { return [ ...mock... ] }` block with `return [];`.
- `useChartDataLogic`: delete the entire `useChartDataLogic` function (it is replaced by `CorrelationChart` + the real correlation hook in Task 12). Remove its import usages.
- `useRiskChartLogic`: replace the `if (!riskScores || riskScores.length === 0) { return [ ...mock... ] }` block with `return [];`.

After edits, `useSatelliteFeedLogic` looks like:

```typescript
export function useSatelliteFeedLogic() {
  const { data: satelliteData, isLoading } = useSatelliteData();

  const feedItems = useMemo(() => {
    if (!satelliteData || satelliteData.length === 0) return [];
    return [...satelliteData]
      .sort((a, b) => (b.ndwi || 0) - (a.ndwi || 0))
      .slice(0, 3)
      .map(item => ({
        label: item.lga_name,
        time: format(new Date(item.observation_date), 'h:mm a'),
        color: item.flood_observed ? 'red' : (item.ndwi || 0) > 0.15 ? 'yellow' : 'green',
        ndwi: item.ndwi || 0,
        rainfall: item.rainfall_mm || 0,
      }));
  }, [satelliteData]);

  return { feedItems, isLoading };
}
```

And `useRiskChartLogic` returns `[]` when empty (the rest unchanged).

- [ ] **Step 2: Typecheck + build**

Run: `cd frontend && npm run build`
Expected: FAIL — `DashboardView.tsx` imports `useChartDataLogic` which was deleted. That is expected; it is fixed in Task 12/13. Do not commit yet if the build fails solely due to that import — proceed to Task 12 to restore a real chart, then commit this task together with Task 12. If other errors appear, fix them.

- [ ] **Step 3: Commit (after Task 12 unblocks the build)**

```bash
git add frontend/src/hooks/useDashboardLogic.ts
git commit -m "refactor(frontend): remove mock/random fallbacks from dashboard logic"
```

---

### Task 10: `DashboardKpiRow` component

**Files:**
- Create: `frontend/src/components/Dashboard/DashboardKpiRow.tsx`

**Interfaces:**
- Consumes: `DashboardSummary` (Task 6 type).
- Produces: a 5-card KPI row: Confirmed cases, Active alerts, Alert level, Rainfall 7d, Flood events.

- [ ] **Step 1: Create the component**

Create `frontend/src/components/Dashboard/DashboardKpiRow.tsx`:

```typescript
import type { DashboardSummary } from '../../types';

interface KpiProps {
  title: string;
  value: string | number;
  subtitle?: string;
}

function Kpi({ title, value, subtitle }: KpiProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="text-xs text-gray-500">{title}</div>
      <div className="text-xl font-semibold text-gray-900">{value}</div>
      {subtitle && <div className="text-xs text-gray-400">{subtitle}</div>}
    </div>
  );
}

const LEVEL_LABEL: Record<string, string> = {
  green: 'Low',
  yellow: 'Medium',
  red: 'High',
};

export function DashboardKpiRow({ summary }: { summary: DashboardSummary | undefined }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      <Kpi title="Confirmed cases" value={summary?.total_cases ?? 0} subtitle="in selected window" />
      <Kpi title="Active alerts" value={summary?.active_alerts_count ?? 0} subtitle="real alerts" />
      <Kpi
        title="Alert level"
        value={summary ? LEVEL_LABEL[summary.alert_level] ?? '—' : '—'}
        subtitle={`${summary?.lgas_high_risk ?? 0} high-risk LGAs`}
      />
      <Kpi title="Rainfall 7d" value={`${summary?.avg_rainfall_7day ?? 0} mm`} subtitle="latest available" />
      <Kpi title="Flood events" value={summary?.flood_events_count ?? 0} subtitle="in window" />
    </div>
  );
}
```

- [ ] **Step 2: Typecheck + build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Dashboard/DashboardKpiRow.tsx
git commit -m "feat(frontend): DashboardKpiRow with real KPIs"
```

---

### Task 11: `ActiveAlertsRail` + `FloodEventsRail` components

**Files:**
- Create: `frontend/src/components/Dashboard/ActiveAlertsRail.tsx`
- Create: `frontend/src/components/Dashboard/FloodEventsRail.tsx`

**Interfaces:**
- Consumes: `useAlerts` (existing) for active alerts; `useFloodEvents` (Task 7) for flood events.
- Produces: two compact list panels (top 5 each).

- [ ] **Step 1: Create `ActiveAlertsRail`**

```typescript
import { useAlerts } from '../../hooks/useApi';
import { useNavigate } from 'react-router-dom';

export function ActiveAlertsRail() {
  const { data: alerts, isLoading } = useAlerts({ is_acknowledged: false });
  const navigate = useNavigate();
  const top = (alerts ?? []).slice(0, 5);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">🚨 Active alerts</h3>
        <button className="text-xs text-blue-600" onClick={() => navigate('/alerts')}>View all</button>
      </div>
      {isLoading && <div className="text-xs text-gray-400">Loading…</div>}
      {!isLoading && top.length === 0 && <div className="text-xs text-gray-400">No active alerts</div>}
      <ul className="space-y-1">
        {top.map((a) => (
          <li key={a.id} className="text-xs flex justify-between">
            <span>{a.title ?? a.type}</span>
            <span className={a.severity === 'critical' ? 'text-red-600' : 'text-yellow-600'}>
              {a.severity}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Create `FloodEventsRail`**

```typescript
import { useFloodEvents } from '../../hooks/useApi';
import { useDateRangeStore } from '../../store/dateRangeStore';

export function FloodEventsRail() {
  const { start, end } = useDateRangeStore();
  const { data: events, isLoading } = useFloodEvents({
    start_date: start ?? undefined,
    end_date: end ?? undefined,
    limit: 5,
  });
  const top = events ?? [];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <h3 className="font-semibold text-sm mb-2">🌊 Recent flood events</h3>
      {isLoading && <div className="text-xs text-gray-400">Loading…</div>}
      {!isLoading && top.length === 0 && <div className="text-xs text-gray-400">No flood events in window</div>}
      <ul className="space-y-1">
        {top.map((e) => (
          <li key={e.id} className="text-xs flex justify-between">
            <span>{e.lga_name ?? 'Unknown LGA'}</span>
            <span className="text-gray-500">
              {e.duration_days ?? 0}d · {Math.round(e.area_km2 ?? 0)}km²
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Typecheck + build**

Run: `cd frontend && npm run build`
Expected: PASS. (If `Alert` type lacks `title`, use `a.type` — confirm against `frontend/src/types/index.ts` `Alert` interface and adjust.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Dashboard/ActiveAlertsRail.tsx frontend/src/components/Dashboard/FloodEventsRail.tsx
git commit -m "feat(frontend): ActiveAlertsRail + FloodEventsRail dashboard panels"
```

---

### Task 12: `CorrelationChart` + `RiskBreakdownChart` components

**Files:**
- Create: `frontend/src/components/Dashboard/CorrelationChart.tsx`
- Create: `frontend/src/components/Dashboard/RiskBreakdownChart.tsx`

**Interfaces:**
- Consumes: `useCorrelation` (existing), `useRiskScores` (existing, now returns v2 fields).
- Produces: `CorrelationChart` (replaces the deleted `useChartDataLogic` random chart); `RiskBreakdownChart` (stacked case_score + flood_score + flood_event_score for top 5 LGAs).

- [ ] **Step 1: Create `CorrelationChart`**

```typescript
import { useCorrelation } from '../../hooks/useApi';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export function CorrelationChart() {
  // Nationwide correlation by year; adjust params as needed.
  const currentYear = new Date().getFullYear();
  const { data, isLoading } = useCorrelation({ from_year: currentYear - 2, to_year: currentYear });

  const rows = (data?.by_year ?? []).map((r: any) => ({
    year: String(r.year),
    coefficient: Number((r.coefficient ?? 0).toFixed(2)),
    lag_weeks: r.lag_weeks ?? 0,
  }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <h3 className="font-semibold text-sm mb-2">📈 Flood ↔ Cholera correlation</h3>
      {isLoading && <div className="text-xs text-gray-400">Loading…</div>}
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="year" />
          <YAxis domain={[-1, 1]} />
          <Tooltip />
          <Bar dataKey="coefficient" fill="#6b3ed6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

**Verify the correlation response shape:** read `backend/app/routers/analytics.py` `/correlation` (around line 299) and `correlation_service.build_correlation_report` to confirm the field names (`by_year`, `coefficient`, `lag_weeks`). Adjust the mapping to match the actual response.

- [ ] **Step 2: Create `RiskBreakdownChart`**

```typescript
import { useRiskScores } from '../../hooks/useApi';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts';

export function RiskBreakdownChart() {
  const { data: scores, isLoading } = useRiskScores();
  const top = (scores ?? [])
    .slice()
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, 5)
    .map((s) => ({
      name: s.lga_name ?? `LGA ${s.lga_id}`,
      case_score: Math.round((s.case_score ?? 0) * 100),
      flood_score: Math.round((s.flood_score ?? 0) * 100),
      flood_event_score: Math.round((s.flood_event_score ?? 0) * 100),
    }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <h3 className="font-semibold text-sm mb-2">📊 Top LGAs — v2.0 risk breakdown</h3>
      {isLoading && <div className="text-xs text-gray-400">Loading…</div>}
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={top}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="case_score" stackId="a" fill="#1392ec" />
          <Bar dataKey="flood_score" stackId="a" fill="#fa6238" />
          <Bar dataKey="flood_event_score" stackId="a" fill="#6b3ed6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 3: Typecheck + build**

Run: `cd frontend && npm run build`
Expected: PASS. If `useCorrelation`'s param shape differs, align with the existing hook signature in `useApi.ts`.

- [ ] **Step 4: Commit (this commit also unblocks Task 9)**

```bash
git add frontend/src/components/Dashboard/CorrelationChart.tsx frontend/src/components/Dashboard/RiskBreakdownChart.tsx frontend/src/hooks/useDashboardLogic.ts
git commit -m "feat(frontend): real correlation + v2.0 risk-breakdown charts; remove random chart"
```

---

### Task 13: Rebuild `DashboardView` as Layout A + remove `|| 18` fallbacks

**Files:**
- Modify: `frontend/src/components/Dashboard/DashboardView.tsx`
- Modify: `frontend/src/components/Reports/ReportsView.tsx:75`

**Interfaces:**
- Consumes: `DateRangeSelector`, `DashboardKpiRow`, `ActiveAlertsRail`, `FloodEventsRail`, `CorrelationChart`, `RiskBreakdownChart` (Tasks 8–12), `useDashboard` (Task 7), `useDateRangeStore`, `ChoroplethMap` (existing).

- [ ] **Step 1: Rewrite `DashboardView`**

Replace the default export of `frontend/src/components/Dashboard/DashboardView.tsx` with a Layout A composition. Keep the existing `ChoroplethMap` import. Remove imports of `useChartDataLogic` and `CaseRainfallChart` (deleted). Minimal replacement:

```typescript
import { useDashboard } from '../../hooks/useApi';
import { useDateRangeStore } from '../../store/dateRangeStore';
import { DateRangeSelector } from './DateRangeSelector';
import { DashboardKpiRow } from './DashboardKpiRow';
import { ActiveAlertsRail } from './ActiveAlertsRail';
import { FloodEventsRail } from './FloodEventsRail';
import { CorrelationChart } from './CorrelationChart';
import { RiskBreakdownChart } from './RiskBreakdownChart';
import ChoroplethMap from '../Map/ChoroplethMap'; // confirm exact path/import

export default function DashboardView() {
  const { start, end } = useDateRangeStore();
  const { data: dashboard, isLoading } = useDashboard(start, end);

  if (isLoading && !dashboard) {
    return <div className="p-6 text-gray-500">Loading dashboard…</div>;
  }

  return (
    <div className="space-y-4">
      <DateRangeSelector maxDataDate={dashboard?.max_data_date ?? null} />
      <DashboardKpiRow summary={dashboard} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 p-3">
          <h3 className="font-semibold text-sm mb-2">Geospatial Risk Map</h3>
          <ChoroplethMap />
        </div>
        <div className="space-y-4">
          <ActiveAlertsRail />
          <FloodEventsRail />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CorrelationChart />
        <RiskBreakdownChart />
      </div>
    </div>
  );
}
```

**Verify the `ChoroplethMap` import path** by checking the existing `DashboardView.tsx` line 1 / 409 import and match it exactly (it may be `../Maps/ChoroplethMap` or similar). Keep the existing default-vs-named import style.

You may keep the existing `KPICard`, `SatelliteFeed`, `FloodCholeraChart`, `FloodingRiskChart` helper components in the file as dead code only if you also keep their imports valid; otherwise delete them to avoid lint errors. Prefer deleting unused helpers.

- [ ] **Step 2: Remove the `|| 18` fallback in ReportsView**

In `frontend/src/components/Reports/ReportsView.tsx` around line 75, change `dashboard?.total_lgas || 18` to `dashboard?.total_lgas ?? 0` (or render the real count only).

- [ ] **Step 3: Typecheck + build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: PASS (no type errors, no lint errors). Fix any unused-import errors by removing the imports.

- [ ] **Step 4: Manual verification**

With the backend (port 8000) and frontend (port 5173) running, open http://localhost:5173/ and confirm:
- KPI row shows real values (Confirmed cases > 0 for the latest-available window; Active alerts reflects `/api/alerts`; Flood events reflects `/api/flood-events`).
- "Data through: {date}" badge shows the real max data date (a 2025 date, not today).
- Date range preset buttons change the KPIs.
- Alerts rail and Flood events rail populate (or show the empty-state message).
- Correlation chart renders bars (not random data).
- Risk breakdown chart shows stacked components for top 5 LGAs.
- No `Math.random()`-driven chart remains.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Dashboard/DashboardView.tsx frontend/src/components/Reports/ReportsView.tsx
git commit -m "feat(frontend): rebuild dashboard as Layout A with real date-aware data"
```

---

## Self-Review (completed)

- **Spec coverage:** B1 (dashboard date window + real alerts + flood count) → Tasks 1–3. B2 (risk-scores v2 fields) → Task 4. B3 (flood-events router) → Task 5. B4 (wire existing correlation/alerts) → Tasks 7, 11, 12. F1 (date-range context) → Tasks 7, 8. F2 (Layout A rebuild + new components) → Tasks 10–13. F3 (remove mock data + `|| 18`) → Tasks 9, 13. F4 (types + hooks) → Tasks 6, 7. All spec items covered.
- **Placeholder scan:** Two intentional "verify the import/shape" notes point the engineer at the exact file to confirm before writing code (limiter import, ChoroplethMap path, correlation response shape, Alert.title). These are verification steps, not placeholders — each has a concrete fallback. No TBD/TODO.
- **Type consistency:** `DashboardSummary` fields (Task 1 schema → Task 6 TS type → Task 10 KpiRow) match. `RiskScore` v2 fields (Task 4 backend → Task 6 TS → Task 12 chart) match. `FloodEvent` / `AlertStats` (Task 7) match the router shapes (Task 5, alerts router). `useDashboard(start, end)` signature consistent across Tasks 7, 8, 13.
