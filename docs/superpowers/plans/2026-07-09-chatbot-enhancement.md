# Chatbot Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the surveillance copilot context-aware (receives dashboard state), give it typed domain tools, harden DSML streaming with an `ERROR` event, persist conversations client-side, secure the agent endpoints, and consolidate provider/model defaults into one config source.

**Architecture:** The agent stays a LiteLLM-backed streamer with the newline-delimited `THOUGHT/TEXT/UI_SPEC` protocol; we add an `ERROR` event type, a `context` field, four typed domain tools (querying models directly, not raw SQL), and a router-scoped API-key gate + rate limiting. The zustand `agentStore` gains localStorage persistence, dashboard-context building, an inline error state, a `prefillPrompt` action, and provider/model initialization from `/api/agent/providers/status`.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / litellm / pytest (backend); React 18 / TypeScript / Vite / zustand / TanStack Query (frontend).

**Design spec:** `docs/superpowers/specs/2026-07-07-dashboard-chatbot-enhancement-design.md`, Section 2 (C1–C9).

## Global Constraints

- Backend tests run with `cd backend && source venv/bin/activate && PYTHONPATH=. pytest <path> -q`. The existing pattern is `TestClient(app)` against the configured Postgres DB plus direct `SessionLocal()` unit tests (see `backend/tests/test_agent_router.py`, `backend/tests/test_agent_service.py`). Follow whichever fits.
- The frontend has **no test runner installed**. Frontend tasks are gated by `cd frontend && npm run build` (runs `tsc && vite build`) and `npm run lint`, plus a manual verification step against the running dev server (http://localhost:5173). Do not introduce vitest in this plan.
- The newline-delimited stream protocol is `THOUGHT:<json>\n`, `TEXT:<json>\n`, `UI_SPEC:<json>\n`. This plan adds **`ERROR:<json>\n`** as a fourth event type. Frontend and backend must agree on all four.
- `query_db` stays as a fallback tool; the four typed tools are preferred and documented in `SYSTEM_INSTRUCTIONS`. `query_db` gains a hard row cap.
- Every backend endpoint keeps a `@limiter.limit(...)` decorator and a `request: Request` parameter (slowapi requires `request`).
- **No backend auth exists today** (the frontend `authStore` is purely client-side demo logic with no token). C7 therefore adds a router-scoped API-key gate env-gated by `AGENT_API_KEY` (open in dev when unset) — not a full user-auth system. This is a deliberate, documented deviation from the spec wording "the app's auth dependency"; see Task 8 and Self-Review.
- **Dependency on the Dashboard Refactor plan (Section 1):** The frontend tasks that build dashboard `context` (Task 9) and add "Ask copilot about this" buttons (Task 10) assume `frontend/src/store/dateRangeStore.ts` and the dashboard rail components (`ActiveAlertsRail`, `FloodEventsRail`, `DashboardKpiRow`, `RiskChoropleth`) from the dashboard-refactor plan exist. All **backend** tasks (1–8) are independent of Section 1. If Section 1 is not merged, Tasks 9–10 are blocked but Tasks 1–8 can proceed.
- The four typed tools query SQLAlchemy models directly (`RiskScore`, `Alert`, `FloodEvent`, `CaseReport`, `LGA`); they do **not** depend on Section 1 routers. The v2 risk columns (`flood_event_score`, `recent_flood_events`, `vulnerability_score`, `algorithm_version`) already exist on the `RiskScore` model (`backend/app/models/environmental.py:70-80`).

## File Structure

**Backend — create:**
- `backend/app/services/agent_tools.py` — typed domain tool functions (`get_lga_risk`, `get_active_alerts`, `get_flood_events`, `get_cholera_cases`).
- `backend/app/security.py` — `secure_filename` + `safe_upload_path` helpers (C8) and `require_agent_key` dependency (C7).
- `backend/tests/test_agent_tools.py` — typed-tool service tests.
- `backend/tests/test_agent_context.py` — context-injection + provider-defaults tests.
- `backend/tests/test_agent_dsml.py` — DSML filter boundary tests.
- `backend/tests/test_agent_security.py` — filename/path sanitization + API-key auth tests.

**Backend — modify:**
- `backend/app/config.py:8` — add `agent_default_provider`, `agent_default_model`, `agent_api_key`, `agent_rate_limit_chat`.
- `backend/app/routers/agent.py:19-23` — `ChatRequest` gains `context`; defaults read from `Settings`; upload/data sanitized; rate-limit + auth decorators.
- `backend/app/services/agent_service.py` — `SurveillanceAgent` gains `context` + Settings-based defaults; typed tools wired into `_tools_schema`/dispatch; `query_db` row cap; `ERROR` event; DSML filter hardening; `provider_status()` returns defaults.

**Frontend — modify:**
- `frontend/src/store/agentStore.ts` — localStorage persistence, `context` building, `ERROR:` handling, `prefillPrompt`, provider/model init from `/providers/status`, `error` field on messages.
- `frontend/src/components/Agent/AgentSidebar.tsx` — inline error rendering; consume `pendingPrompt`.
- `frontend/src/components/Dashboard/ActiveAlertsRail.tsx`, `FloodEventsRail.tsx`, `DashboardKpiRow.tsx`, `RiskChoropleth` — "Ask copilot about this" buttons (Section 1 components).

---

### Task 1: Consolidate provider/model defaults into `Settings` (C9)

**Files:**
- Modify: `backend/app/config.py:8-76`
- Modify: `backend/app/routers/agent.py:19-23`
- Modify: `backend/app/services/agent_service.py:194-207` (`__init__`), `:59-61` (`provider_status`)
- Test: `backend/tests/test_agent_context.py` (create)

**Interfaces:**
- Produces: `Settings.agent_default_provider` (`str`, default `"deepseek"`), `Settings.agent_default_model` (`str`, default `"deepseek-v4-flash"`), `Settings.agent_api_key` (`Optional[str]`, default `None` — used by Task 8), `Settings.agent_rate_limit_chat` (`str`, default `"20/minute"` — used by Task 8).
- Produces: `provider_status()` returns `dict` with the existing `{provider: bool}` keys **plus** `"default_provider": str` and `"default_model": str`.
- Produces: `ChatRequest.provider` / `ChatRequest.model` default to the Settings values; `SurveillanceAgent.__init__` defaults likewise.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_agent_context.py`:

```python
"""Tests for agent provider-default consolidation (C9)."""
from app.config import get_settings
from app.services.agent_service import provider_status


def test_settings_has_agent_defaults():
    """Settings exposes agent_default_provider and agent_default_model."""
    s = get_settings()
    assert isinstance(s.agent_default_provider, str) and s.agent_default_provider
    assert isinstance(s.agent_default_model, str) and s.agent_default_model


def test_provider_status_returns_defaults():
    """provider_status() includes default_provider and default_model."""
    status = provider_status()
    s = get_settings()
    assert status["default_provider"] == s.agent_default_provider
    assert status["default_model"] == s.agent_default_model
    # Existing per-provider booleans still present
    for p in ("google", "anthropic", "deepseek", "openrouter", "nvidia_nim"):
        assert p in status and isinstance(status[p], bool)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_context.py -q`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'agent_default_provider'`.

- [ ] **Step 3: Add the settings**

In `backend/app/config.py`, inside `class Settings(BaseSettings)`, add after the AI provider keys block (after line 51):

```python
    # Agent copilot defaults (single source of truth — C9)
    agent_default_provider: str = "deepseek"
    agent_default_model: str = "deepseek-v4-flash"
    # Router-scoped API key gate for /api/agent/* (C7). None = open in dev.
    agent_api_key: Optional[str] = None
    # Stricter rate limit for the LLM-spend chat endpoint (C7)
    agent_rate_limit_chat: str = "20/minute"
```

- [ ] **Step 4: Extend `provider_status()`**

In `backend/app/services/agent_service.py`, replace `provider_status` (lines 59-61):

```python
def provider_status() -> dict:
    """Return provider key availability plus the configured defaults."""
    from app.config import get_settings
    s = get_settings()
    return {
        **{p: _has_key(p) for p in PROVIDER_ENV_KEYS},
        "default_provider": s.agent_default_provider,
        "default_model": s.agent_default_model,
    }
```

- [ ] **Step 5: Point `ChatRequest` defaults at `Settings`**

In `backend/app/routers/agent.py`, replace the `ChatRequest` class (lines 19-23). Add the import and the `context` field is added in Task 2 — for now only change the defaults:

```python
from app.config import get_settings


class ChatRequest(BaseModel):
    message: str
    provider: str = Field(default_factory=lambda: get_settings().agent_default_provider)
    model: str = Field(default_factory=lambda: get_settings().agent_default_model)
    history: list[ChatMessage] = []
```

Add `from pydantic import BaseModel, Field` to the imports at the top of `agent.py` (replace the existing `from pydantic import BaseModel`).

- [ ] **Step 6: Point `SurveillanceAgent.__init__` defaults at `Settings`**

In `backend/app/services/agent_service.py`, replace the `__init__` signature defaults (lines 194-200):

```python
    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        history: list[dict] | None = None,
    ):
        from app.config import get_settings
        s = get_settings()
        self.provider = provider or s.agent_default_provider
        self.model = model or s.agent_default_model
        self.api_key = api_key
        # conversation history (list of {role, content} dicts)
        self.history: list[dict] = history or []
        # Instance system instructions copy
        self.system_instructions = self.SYSTEM_INSTRUCTIONS
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_context.py tests/test_agent_router.py -q`
Expected: PASS. The existing `test_providers_status_endpoint` still passes (it only checks the five provider keys are present and bool — extra keys are allowed).

- [ ] **Step 8: Commit**

```bash
git add backend/app/config.py backend/app/routers/agent.py backend/app/services/agent_service.py backend/tests/test_agent_context.py
git commit -m "feat(agent): consolidate provider/model defaults into Settings (C9)"
```

---

### Task 2: Context injection into the system prompt (C1 backend)

**Files:**
- Modify: `backend/app/routers/agent.py:19-23` (`ChatRequest` — add `context`), `:26-33` (pass `context` to agent)
- Modify: `backend/app/services/agent_service.py` (`__init__` accepts `context`; build system instructions with context block)
- Test: `backend/tests/test_agent_context.py` (append)

**Interfaces:**
- Produces: `ChatRequest.context: AgentContext | None`, where `AgentContext` has optional fields `lga_id: int | None`, `lga_name: str | None`, `date_range: dict | None` (`{start?: str, end?: str}`), `active_alerts: dict | None`, `current_view: str | None`.
- Produces: `SurveillanceAgent.__init__(..., context: dict | None = None)`. When `context` is present and non-empty, `self.system_instructions` is extended with a "Current dashboard context" block built by the static method `SurveillanceAgent._context_block(context) -> str`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_agent_context.py`:

```python
from app.services.agent_service import SurveillanceAgent


def test_context_block_contains_values():
    """_context_block renders a structured context string."""
    block = SurveillanceAgent._context_block({
        "lga_name": "Calabar South",
        "lga_id": 12,
        "date_range": {"start": "2025-11-01", "end": "2025-11-30"},
        "active_alerts": {"total_active": 2, "critical": 1},
        "current_view": "/",
    })
    assert "Calabar South" in block
    assert "2025-11-01" in block
    assert "Current dashboard context" in block


def test_agent_system_instructions_include_context():
    """An agent constructed with context has it in system_instructions."""
    agent = SurveillanceAgent(context={"lga_name": "Odukpani", "current_view": "/"})
    assert "Odukpani" in agent.system_instructions


def test_agent_without_context_omits_block():
    """An agent constructed without context has no context block."""
    agent = SurveillanceAgent()
    assert "Current dashboard context" not in agent.system_instructions
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_context.py -q`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'context'` / `_context_block` missing.

- [ ] **Step 3: Add `AgentContext` to `ChatRequest`**

In `backend/app/routers/agent.py`, replace the `ChatRequest`/`ChatMessage` block (lines 14-23) with:

```python
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AgentContext(BaseModel):
    """Dashboard context passed with each chat request (C1)."""
    lga_id: int | None = None
    lga_name: str | None = None
    date_range: dict | None = None  # {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    active_alerts: dict | None = None  # shallow summary, e.g. {"total_active": n}
    current_view: str | None = None  # route path


class ChatRequest(BaseModel):
    message: str
    provider: str = Field(default_factory=lambda: get_settings().agent_default_provider)
    model: str = Field(default_factory=lambda: get_settings().agent_default_model)
    history: list[ChatMessage] = []
    context: AgentContext | None = None
```

- [ ] **Step 4: Pass `context` through `chat_endpoint`**

In `backend/app/routers/agent.py`, replace the `chat_endpoint` body (lines 27-33) so the agent receives context:

```python
@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in request.history]
    agent_instance = SurveillanceAgent(
        provider=request.provider,
        model=request.model,
        history=history,
        context=request.context.model_dump(exclude_none=True) if request.context else None,
    )
```

Leave the rest of `chat_endpoint` (the `try`/`response_generator`/`StreamingResponse`) unchanged.

- [ ] **Step 5: Add `_context_block` and wire `context` in `__init__`**

In `backend/app/services/agent_service.py`, update `__init__` (the version from Task 1) to accept `context` and build system instructions:

```python
    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        history: list[dict] | None = None,
        context: dict | None = None,
    ):
        from app.config import get_settings
        s = get_settings()
        self.provider = provider or s.agent_default_provider
        self.model = model or s.agent_default_model
        self.api_key = api_key
        self.history: list[dict] = history or []
        self.system_instructions = self.SYSTEM_INSTRUCTIONS + self._context_block(context or {})

    @staticmethod
    def _context_block(context: dict) -> str:
        """Render a structured 'Current dashboard context' block for the system prompt."""
        if not context:
            return ""
        lines = ["\n\n## Current dashboard context"]
        if context.get("current_view"):
            lines.append(f"- Current view: {context['current_view']}")
        if context.get("lga_name"):
            lines.append(f"- Selected LGA: {context['lga_name']}"
                         + (f" (id={context['lga_id']})" if context.get("lga_id") else ""))
        dr = context.get("date_range") or {}
        if dr.get("start") or dr.get("end"):
            lines.append(f"- Date range: {dr.get('start', '?')} → {dr.get('end', '?')}")
        aa = context.get("active_alerts") or {}
        if aa:
            lines.append(f"- Active alerts: {aa}")
        lines.append(
            "When the user asks about 'this', 'here', or 'current', resolve to the "
            "selected LGA and date range above. Prefer the typed domain tools over raw SQL."
        )
        return "\n".join(lines) + "\n"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_context.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/agent.py backend/app/services/agent_service.py backend/tests/test_agent_context.py
git commit -m "feat(agent): inject dashboard context into the system prompt (C1)"
```

---

### Task 3: Typed domain tool service module (C2 part 1)

**Files:**
- Create: `backend/app/services/agent_tools.py`
- Test: `backend/tests/test_agent_tools.py` (create)

**Interfaces:**
- Produces: `agent_tools.get_lga_risk(db, lga_id_or_name) -> dict` — latest `RiskScore` for the LGA with v2 components (`score`, `level`, `flood_score`, `case_score`, `flood_event_score`, `recent_flood_events`, `vulnerability_score`, `algorithm_version`, `recent_cases`, `recent_deaths`, `score_date`), plus `lga_id`/`lga_name`. Returns `{"error": "..."}` if not found.
- Produces: `agent_tools.get_active_alerts(db, lga_id=None, severity=None, limit=20) -> list[dict]` — active alerts (capped at `limit`, max 100), each `{id, lga_id, lga_name, level, severity, type, title, message, created_at}`.
- Produces: `agent_tools.get_flood_events(db, lga_id=None, start_date=None, end_date=None, limit=20) -> list[dict]` — recent flood events, each `{uuid, lga_id, lga_name, start_date, end_date, duration_days, area_km2}`.
- Produces: `agent_tools.get_cholera_cases(db, lga_id=None, start_date=None, end_date=None, limit=50) -> list[dict]` — aggregated cases per LGA over the window, each `{lga_id, lga_name, new_cases, deaths, confirmed_cases}`.
- All functions take a `db: Session` (caller opens/closes). They never raise on missing data — they return `[]`/`{"error": ...}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_agent_tools.py`:

```python
"""Tests for the typed domain tools (C2)."""
from datetime import date

from app.database import SessionLocal
from app.services import agent_tools


def _db():
    return SessionLocal()


def test_get_lga_risk_returns_v2_fields_or_error():
    db = _db()
    try:
        result = agent_tools.get_lga_risk(db, "Calabar South")
    finally:
        db.close()
    # Either a real risk row with v2 fields, or a clean error dict — never an exception.
    if "error" not in result:
        for key in (
            "lga_id", "lga_name", "score", "level", "flood_event_score",
            "recent_flood_events", "vulnerability_score", "algorithm_version",
        ):
            assert key in result, f"missing field: {key}"


def test_get_active_alerts_caps_and_shapes():
    db = _db()
    try:
        alerts = agent_tools.get_active_alerts(db, limit=5)
    finally:
        db.close()
    assert isinstance(alerts, list)
    assert len(alerts) <= 5
    for a in alerts:
        for key in ("id", "lga_name", "level", "severity", "type", "title", "created_at"):
            assert key in a


def test_get_flood_events_caps_and_shapes():
    db = _db()
    try:
        events = agent_tools.get_flood_events(db, limit=5)
    finally:
        db.close()
    assert isinstance(events, list)
    assert len(events) <= 5
    for e in events:
        for key in ("uuid", "lga_name", "start_date", "end_date", "duration_days", "area_km2"):
            assert key in e


def test_get_cholera_cases_caps_and_shapes():
    db = _db()
    try:
        cases = agent_tools.get_cholera_cases(db, start_date="2024-01-01", end_date="2025-12-31", limit=5)
    finally:
        db.close()
    assert isinstance(cases, list)
    assert len(cases) <= 5
    for c in cases:
        for key in ("lga_id", "lga_name", "new_cases", "deaths"):
            assert key in c


def test_get_active_alerts_rejects_oversize_limit():
    db = _db()
    try:
        alerts = agent_tools.get_active_alerts(db, limit=99999)
    finally:
        db.close()
    assert len(alerts) <= 100  # hard cap
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_tools.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.agent_tools'`.

- [ ] **Step 3: Implement the tool functions**

Create `backend/app/services/agent_tools.py`:

```python
"""Typed domain tools for the surveillance agent (C2).

These query SQLAlchemy models directly so the agent never needs raw SQL for
common questions. Each function takes an open ``db: Session`` (caller closes it)
and never raises on missing data.
"""
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Alert, CaseReport, FloodEvent, LGA, RiskScore

# Hard caps so a runaway tool call cannot dump the whole DB.
MAX_ALERTS = 100
MAX_FLOOD_EVENTS = 200
MAX_CASES = 200


def _resolve_lga(db: Session, lga_id: Optional[int], lga_name: Optional[str]):
    """Return (lga_id, lga_name) for the given identifier, or (None, None)."""
    if lga_id:
        lga = db.query(LGA).filter(LGA.id == lga_id).first()
        return lga.id, lga.name if lga else None
    if lga_name:
        lga = db.query(LGA).filter(LGA.name.ilike(lga_name)).first()
        return (lga.id, lga.name) if lga else (None, None)
    return None, None


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def get_lga_risk(db: Session, lga_id_or_name) -> dict:
    """Latest v2.0 RiskScore + components for an LGA (by id or name)."""
    if isinstance(lga_id_or_name, int):
        lga_id, lga_name = _resolve_lga(db, lga_id_or_name, None)
    else:
        lga_id, lga_name = _resolve_lga(db, None, str(lga_id_or_name))
    if lga_id is None:
        return {"error": f"LGA not found: {lga_id_or_name}"}

    rs = (
        db.query(RiskScore)
        .filter(RiskScore.lga_id == lga_id)
        .order_by(RiskScore.score_date.desc())
        .first()
    )
    if rs is None:
        return {"error": f"No risk score for LGA id={lga_id}"}
    return {
        "lga_id": lga_id,
        "lga_name": lga_name,
        "score": rs.score,
        "level": rs.level,
        "flood_score": rs.flood_score,
        "rainfall_score": rs.rainfall_score,
        "case_score": rs.case_score,
        "flood_event_score": rs.flood_event_score,
        "recent_flood_events": rs.recent_flood_events,
        "vulnerability_score": rs.vulnerability_score,
        "recent_cases": rs.recent_cases,
        "recent_deaths": rs.recent_deaths,
        "algorithm_version": rs.algorithm_version,
        "score_date": rs.score_date.isoformat() if rs.score_date else None,
    }


def get_active_alerts(
    db: Session, lga_id: Optional[int] = None, severity: Optional[str] = None, limit: int = 20
) -> list[dict]:
    """Active alerts, optionally filtered by LGA and severity, capped."""
    limit = max(1, min(int(limit or 20), MAX_ALERTS))
    q = (
        db.query(Alert, LGA.name.label("lga_name"))
        .outerjoin(LGA, Alert.lga_id == LGA.id)
        .filter(Alert.is_active.is_(True))
    )
    if lga_id is not None:
        q = q.filter(Alert.lga_id == lga_id)
    if severity:
        q = q.filter(Alert.severity == severity)
    rows = q.order_by(Alert.created_at.desc()).limit(limit).all()
    return [
        {
            "id": a.id,
            "lga_id": a.lga_id,
            "lga_name": lga_name,
            "level": a.level,
            "severity": a.severity,
            "type": a.type,
            "title": a.title,
            "message": a.message,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a, lga_name in rows
    ]


def get_flood_events(
    db: Session,
    lga_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """Recent flood events, optionally filtered by LGA and a date window."""
    limit = max(1, min(int(limit or 20), MAX_FLOOD_EVENTS))
    q = (
        db.query(FloodEvent, LGA.name.label("lga_name"))
        .outerjoin(LGA, FloodEvent.lga_id == LGA.id)
    )
    if lga_id is not None:
        q = q.filter(FloodEvent.lga_id == lga_id)
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start:
        q = q.filter(FloodEvent.start_date >= start)
    if end:
        q = q.filter(FloodEvent.start_date <= end)
    rows = q.order_by(FloodEvent.start_date.desc()).limit(limit).all()
    return [
        {
            "uuid": fe.uuid,
            "lga_id": fe.lga_id,
            "lga_name": lga_name,
            "start_date": fe.start_date.isoformat() if fe.start_date else None,
            "end_date": fe.end_date.isoformat() if fe.end_date else None,
            "duration_days": fe.duration_days,
            "area_km2": fe.area_km2,
        }
        for fe, lga_name in rows
    ]


def get_cholera_cases(
    db: Session,
    lga_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Aggregated cholera cases per LGA over a window, capped."""
    limit = max(1, min(int(limit or 50), MAX_CASES))
    q = (
        db.query(
            LGA.id.label("lga_id"),
            LGA.name.label("lga_name"),
            func.coalesce(func.sum(CaseReport.new_cases), 0).label("new_cases"),
            func.coalesce(func.sum(CaseReport.deaths), 0).label("deaths"),
            func.coalesce(func.sum(CaseReport.confirmed_cases), 0).label("confirmed_cases"),
        )
        .join(CaseReport, CaseReport.lga_id == LGA.id)
    )
    if lga_id is not None:
        q = q.filter(CaseReport.lga_id == lga_id)
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start:
        q = q.filter(CaseReport.report_date >= start)
    if end:
        q = q.filter(CaseReport.report_date <= end)
    rows = q.group_by(LGA.id, LGA.name).order_by(func.sum(CaseReport.new_cases).desc()).limit(limit).all()
    return [
        {
            "lga_id": r.lga_id,
            "lga_name": r.lga_name,
            "new_cases": int(r.new_cases or 0),
            "deaths": int(r.deaths or 0),
            "confirmed_cases": int(r.confirmed_cases or 0),
        }
        for r in rows
    ]
```

- [ ] **Step 4: Verify model imports exist**

Run this one-liner to confirm `Alert, CaseReport, FloodEvent, LGA, RiskScore` are all exported from `app.models`:

```bash
cd backend && source venv/bin/activate && python -c "from app.models import Alert, CaseReport, FloodEvent, LGA, RiskScore; print('ok')"
```
Expected: prints `ok`. (These are all defined in `app/models/` and re-exported via `app/models/__init__.py`.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_tools.py -q`
Expected: PASS. (Tests assert shape/caps, not specific DB values, so they pass regardless of seeded data.)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent_tools.py backend/tests/test_agent_tools.py
git commit -m "feat(agent): typed domain tool service module (C2 part 1)"
```

---

### Task 4: Wire typed tools into the agent + `query_db` row cap (C2 part 2)

**Files:**
- Modify: `backend/app/services/agent_service.py:184-192` (`SYSTEM_INSTRUCTIONS`), `:211-224` (`query_db` row cap), `:277-368` (`_tools_schema`), `:670-710` (dispatch loop — extract `_dispatch_tool`)
- Test: `backend/tests/test_agent_tools.py` (append)

**Interfaces:**
- Consumes: `agent_tools.get_lga_risk / get_active_alerts / get_flood_events / get_cholera_cases` from Task 3.
- Produces: `SurveillanceAgent._dispatch_tool(self, name: str, args: dict) -> str` — returns the tool result as a JSON string. Called by `_chat_raw`'s tool-call loop. Handles `query_db`, `analyze_file`, `generate_ui_spec`, and the four typed tools.
- Produces: `_tools_schema()` returns seven tools (the original three plus `get_lga_risk`, `get_active_alerts`, `get_flood_events`, `get_cholera_cases`).
- Produces: `query_db` caps results at 500 rows (appends `LIMIT 500` when the query has no `LIMIT`).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_agent_tools.py`:

```python
from app.services.agent_service import SurveillanceAgent


def test_tools_schema_includes_typed_tools():
    names = {t["function"]["name"] for t in SurveillanceAgent._tools_schema()}
    assert {"get_lga_risk", "get_active_alerts", "get_flood_events", "get_cholera_cases"} <= names


def test_dispatch_get_active_alerts_returns_json():
    agent = SurveillanceAgent()
    res = agent._dispatch_tool("get_active_alerts", {"limit": 3})
    import json
    parsed = json.loads(res)
    assert isinstance(parsed, list)
    assert len(parsed) <= 3


def test_dispatch_unknown_tool_returns_error_json():
    agent = SurveillanceAgent()
    import json
    res = json.loads(agent._dispatch_tool("no_such_tool", {}))
    assert "error" in res


def test_query_db_row_cap_applied():
    """query_db appends LIMIT 500 when the query lacks one."""
    agent = SurveillanceAgent()
    res = agent.query_db("SELECT 1 AS n")  # trivially small; just exercises the path
    import json
    parsed = json.loads(res)
    # Either a list of rows or an error dict, but never an exception.
    assert isinstance(parsed, (list, dict))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_tools.py -q`
Expected: FAIL — `_dispatch_tool` missing; typed tools absent from schema.

- [ ] **Step 3: Update `SYSTEM_INSTRUCTIONS`**

In `backend/app/services/agent_service.py`, replace `SYSTEM_INSTRUCTIONS` (lines 184-192):

```python
    SYSTEM_INSTRUCTIONS = (
        "You are the Cholera Environmental Surveillance Copilot. "
        "You help epidemiologists and health officers analyse disease data for Cross River State, Nigeria.\n"
        "You have seven tools available. Prefer the TYPED DOMAIN TOOLS over raw SQL:\n"
        "  • get_lga_risk(lga_id_or_name) — latest v2.0 risk score + components for an LGA.\n"
        "  • get_active_alerts(lga_id?, severity?, limit?) — active alerts (capped).\n"
        "  • get_flood_events(lga_id?, start_date?, end_date?, limit?) — recent flood events.\n"
        "  • get_cholera_cases(lga_id?, start_date?, end_date?, limit?) — aggregated cases per LGA.\n"
        "  • query_db — read-only SQL SELECT against LGA/case tables (fallback; capped at 500 rows).\n"
        "  • analyze_file — descriptive analytics (describe, corr, head) on an uploaded CSV/Excel file.\n"
        "  • generate_ui_spec — build a custom interactive UI layout for an uploaded file.\n"
        "Dates are ISO (YYYY-MM-DD). When the dashboard context names an LGA, pass its name to "
        "get_lga_risk rather than querying the lgas table.\n"
        "Always explain your reasoning before calling a tool and summarise findings clearly after."
    )
```

- [ ] **Step 4: Add a row cap to `query_db`**

In `backend/app/services/agent_service.py`, replace `query_db` (lines 211-224):

```python
    def query_db(self, SQL_query: str) -> str:
        """Run a read-only SQL SELECT query against LGA and case tables (<=500 rows)."""
        if not _READ_ONLY_RE.match(SQL_query):
            return json.dumps({"error": "Only SELECT statements are allowed."})
        if not re.search(r"\blimit\b", SQL_query, re.IGNORECASE):
            SQL_query = f"{SQL_query.rstrip(';')} LIMIT 500"
        db = SessionLocal()
        try:
            from sqlalchemy import text
            result = db.execute(text(SQL_query)).fetchall()[:500]
            return json.dumps([dict(row._mapping) for row in result], default=str)
        except Exception as exc:
            logger.warning("query_db error: %s", exc)
            return json.dumps({"error": str(exc)})
        finally:
            db.close()
```

- [ ] **Step 5: Add the four typed tools to `_tools_schema()`**

In `backend/app/services/agent_service.py`, inside `_tools_schema()` (after the `generate_ui_spec` entry, before the closing `]` at line 367), append:

```python
            {
                "type": "function",
                "function": {
                    "name": "get_lga_risk",
                    "description": "Get the latest v2.0 risk score and its components for an LGA, by id or name.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lga_id_or_name": {
                                "type": "string",
                                "description": "LGA id (int as string) or LGA name, e.g. 'Calabar South'.",
                            }
                        },
                        "required": ["lga_id_or_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_active_alerts",
                    "description": "List active surveillance alerts, optionally filtered by LGA and severity.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lga_id": {"type": "integer"},
                            "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                            "limit": {"type": "integer", "description": "Max results (default 20, max 100)."},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_flood_events",
                    "description": "List recent flood events, optionally filtered by LGA and a date window.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lga_id": {"type": "integer"},
                            "start_date": {"type": "string", "description": "ISO date YYYY-MM-DD."},
                            "end_date": {"type": "string", "description": "ISO date YYYY-MM-DD."},
                            "limit": {"type": "integer", "description": "Max results (default 20, max 200)."},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_cholera_cases",
                    "description": "Get aggregated cholera cases per LGA over a date window.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lga_id": {"type": "integer"},
                            "start_date": {"type": "string", "description": "ISO date YYYY-MM-DD."},
                            "end_date": {"type": "string", "description": "ISO date YYYY-MM-DD."},
                            "limit": {"type": "integer", "description": "Max results (default 50, max 200)."},
                        },
                    },
                },
            },
```

- [ ] **Step 6: Extract `_dispatch_tool` and use it in `_chat_raw`**

In `backend/app/services/agent_service.py`, add this method to `SurveillanceAgent` (place it just before `_tools_schema`, around line 276):

```python
    def _dispatch_tool(self, name: str, args: dict) -> str:
        """Execute a tool by name and return its result as a JSON string."""
        from app.services import agent_tools

        if name == "query_db":
            return self.query_db(args.get("SQL_query", ""))
        if name == "analyze_file":
            return self.analyze_file(args.get("file_path", ""), args.get("operation", "head"))
        if name == "generate_ui_spec":
            return self.generate_ui_spec(args.get("file_path", ""), args.get("ui_config", ""))
        if name in ("get_lga_risk", "get_active_alerts", "get_flood_events", "get_cholera_cases"):
            db = SessionLocal()
            try:
                if name == "get_lga_risk":
                    return json.dumps(
                        agent_tools.get_lga_risk(db, args.get("lga_id_or_name")),
                        default=str,
                    )
                if name == "get_active_alerts":
                    return json.dumps(
                        agent_tools.get_active_alerts(
                            db, args.get("lga_id"), args.get("severity"), args.get("limit", 20)
                        ),
                        default=str,
                    )
                if name == "get_flood_events":
                    return json.dumps(
                        agent_tools.get_flood_events(
                            db,
                            args.get("lga_id"),
                            args.get("start_date"),
                            args.get("end_date"),
                            args.get("limit", 20),
                        ),
                        default=str,
                    )
                if name == "get_cholera_cases":
                    return json.dumps(
                        agent_tools.get_cholera_cases(
                            db,
                            args.get("lga_id"),
                            args.get("start_date"),
                            args.get("end_date"),
                            args.get("limit", 50),
                        ),
                        default=str,
                    )
            except Exception as exc:
                logger.warning("typed tool %s error: %s", name, exc)
                return json.dumps({"error": str(exc)})
            finally:
                db.close()
        return json.dumps({"error": f"Unknown tool: {name}"})
```

Then replace the tool-execution block in `_chat_raw` (lines 682-699, the `if name == "query_db": ... else: res = ...` block) with a single call. The block currently starts at `if name == "query_db":` and ends at `else: res = json.dumps({"error": f"Unknown tool: {name}"})`. Replace it with:

```python
                    if name == "generate_ui_spec":
                        # generate_ui_spec still emits a UI_SPEC event in addition to its result.
                        res = self._dispatch_tool(name, args)
                        try:
                            ui_config_obj = json.loads(args.get("ui_config", ""))
                            yield "ui_spec", json.dumps({"file_path": args.get("file_path", ""), "config": ui_config_obj})
                        except Exception as exc:
                            yield "thought", f"⚠️ Error parsing generate_ui_spec json: {exc}"
                    else:
                        res = self._dispatch_tool(name, args)
```

Leave the surrounding `yield "thought", f"🔧 Executing tool ..."` and `yield "thought", f"📦 Tool ... output: ..."` lines unchanged.

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_tools.py tests/test_agent_service.py tests/test_agent_router.py -q`
Expected: PASS. The existing `test_agent_router.py::test_agent_chat_endpoint` still passes (typed tools are additive; mock mode is unchanged).

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/agent_service.py backend/tests/test_agent_tools.py
git commit -m "feat(agent): wire typed domain tools + query_db row cap (C2 part 2)"
```

---

### Task 5: `ERROR` streaming event (C4 backend)

**Files:**
- Modify: `backend/app/services/agent_service.py:370-390` (`chat` passes through `error`), `:626-743` (`_chat_raw` emits `error` and ends stream on per-chunk exceptions)
- Test: `backend/tests/test_agent_context.py` (append)

**Interfaces:**
- Produces: `_chat_raw` may yield `("error", "<message>")`. `chat()` passes it through unchanged (like `thought`/`ui_spec`). The router's `response_generator` formats it as `ERROR:<json>\n` via the existing `else: yield f"{token_type.upper()}:{json.dumps(token)}\n"` branch — no router change needed.
- Replaces the broad `except Exception` at lines 740-743 (catch-into-THOUGHT/TEXT) with an `ERROR` event + early return.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_agent_context.py`:

```python
import pytest
import litellm
from app.services.agent_service import SurveillanceAgent


@pytest.mark.asyncio
async def test_error_event_emitted_on_stream_exception(monkeypatch):
    """A mid-stream exception yields an 'error' event and ends the stream."""
    monkeypatch.setattr("app.services.agent_service._has_key", lambda p: True)

    async def fake_acompletion(**kwargs):
        async def gen():
            raise RuntimeError("boom in stream")
            yield  # noqa: never reached — makes this an async generator
        return gen()

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)

    agent = SurveillanceAgent(provider="deepseek", model="x")
    events = [t async for t, _ in agent.chat("hi")]
    assert "error" in events
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_context.py::test_error_event_emitted_on_stream_exception -q`
Expected: FAIL — current code catches the exception into a `THOUGHT`/`TEXT` pair, so no `"error"` event is yielded.

- [ ] **Step 3: Pass `error` events through in `chat()`**

In `backend/app/services/agent_service.py`, the `chat()` method (lines 372-390) currently does `if token_type == "text": ... else: yield token_type, token`. The `else` already passes `error` through unchanged, so `chat()` needs **no code change**. Confirm by reading lines 380-386: the `else: yield token_type, token` branch handles it. No edit required here.

- [ ] **Step 4: Emit `error` and end the stream in `_chat_raw`**

In `backend/app/services/agent_service.py`, replace the entire `try/except` block at the end of `_chat_raw` (lines 626-743 — from `try:` through the final `except Exception as exc:` block) with a version that wraps the streaming loop and emits `error`. The new block:

```python
        try:
            max_turns = 10
            for turn in range(max_turns):
                # On the last turn, force a final text response by not offering tools
                active_tools = self._tools_schema() if turn < max_turns - 1 else None
                response = await litellm.acompletion(
                    model=model_str,
                    messages=messages,
                    tools=active_tools,
                    stream=True,
                )

                tool_calls_acc: list[dict] = []
                try:
                    async for chunk in response:
                        delta = chunk.choices[0].delta

                        reasoning = getattr(delta, "reasoning_content", None)
                        if reasoning:
                            yield "thought", reasoning

                        if getattr(delta, "tool_calls", None):
                            for tc in delta.tool_calls:
                                while len(tool_calls_acc) <= tc.index:
                                    tool_calls_acc.append({"id": "", "name": "", "arguments": ""})
                                if tc.id:
                                    tool_calls_acc[tc.index]["id"] = tc.id
                                if tc.function.name:
                                    tool_calls_acc[tc.index]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls_acc[tc.index]["arguments"] += tc.function.arguments

                        if getattr(delta, "content", None):
                            yield "text", delta.content
                except Exception as exc:
                    logger.exception("agent_service stream error")
                    yield "error", f"Streaming error: {exc}"
                    return

                if not tool_calls_acc:
                    break

                # ── Execute any tool calls ─────────────────────────────────────
                tool_results_messages: list[dict] = []

                for idx, tc in enumerate(tool_calls_acc):
                    name = tc["name"]
                    args_str = tc["arguments"]
                    tc_id = tc["id"] or f"call_{idx}_{turn}"

                    try:
                        args = json.loads(args_str) if args_str else {}
                    except json.JSONDecodeError:
                        args = {}

                    yield "thought", f"🔧 Executing tool `{name}` with args: `{json.dumps(args)}`"

                    if name == "generate_ui_spec":
                        res = self._dispatch_tool(name, args)
                        try:
                            ui_config_obj = json.loads(args.get("ui_config", ""))
                            yield "ui_spec", json.dumps({"file_path": args.get("file_path", ""), "config": ui_config_obj})
                        except Exception as exc:
                            yield "thought", f"⚠️ Error parsing generate_ui_spec json: {exc}"
                    else:
                        try:
                            res = self._dispatch_tool(name, args)
                        except Exception as exc:
                            logger.exception("tool dispatch error")
                            yield "error", f"Tool '{name}' failed: {exc}"
                            return

                    yield "thought", f"📦 Tool `{name}` output: {res[:400]}{'...' if len(res) > 400 else ''}"

                    tool_results_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "name": name,
                            "content": res,
                        }
                    )

                assistant_tool_calls_msg = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc["id"] or f"call_{i}_{turn}",
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            },
                        }
                        for i, tc in enumerate(tool_calls_acc)
                    ],
                }

                messages.append(assistant_tool_calls_msg)
                messages.extend(tool_results_messages)

                yield "thought", "💬 Synthesising response from tool outputs…"

        except litellm.exceptions.AuthenticationError as exc:
            yield "error", f"Authentication failed for `{self.provider}`: {exc}"
        except litellm.exceptions.RateLimitError as exc:
            yield "error", f"Rate limit reached: {exc}"
        except Exception as exc:
            logger.exception("agent_service chat error")
            yield "error", f"Unexpected error: {exc}"
```

This replaces the previous `except` blocks that yielded `thought`/`text` with `error` events, and adds an inner `try/except` around the per-chunk loop and tool dispatch that emits `error` then `return`s.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_context.py tests/test_agent_router.py tests/test_agent_service.py -q`
Expected: PASS. `test_agent_chat_endpoint` still passes (mock mode path is untouched and produces TEXT/THOUGHT/UI_SPEC).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent_service.py backend/tests/test_agent_context.py
git commit -m "feat(agent): emit ERROR streaming event on per-chunk exceptions (C4)"
```

---

### Task 6: DSML filter hardening (C5)

**Files:**
- Modify: `backend/app/services/agent_service.py:82-175` (`StreamingDSMLFilter`), `:372-390` (`chat` drains warnings)
- Test: `backend/tests/test_agent_dsml.py` (create)

**Interfaces:**
- Produces: `StreamingDSMLFilter.warnings: list[str]` — populated when a DSML block exceeds 1000 chars without closing (no silent drop). `chat()` drains `warnings` as `thought` events before `flush()`.
- Produces: end-tag matching accepts `</|dsml|tool_calls>`, `</|dsml|toolcalls>` (no underscore), and `</dsml>`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_agent_dsml.py`:

```python
"""Boundary tests for the StreamingDSMLFilter (C5)."""
from app.services.agent_service import StreamingDSMLFilter


def _drain(chunks):
    f = StreamingDSMLFilter()
    out = [f.feed(c) for c in chunks] + [f.flush()]
    return "".join(out), f


def test_existing_behaviour_preserved():
    """The original test case still filters the DSML block."""
    chunks = [
        "Hello ", "world!", " < | DSML | tool_calls>",
        "< | DSML | invoke name=\"analyze_file\">", "some args",
        "</ | DSML | invoke>", "</ | DSML | tool_calls>", " Done!",
    ]
    out, _ = _drain(chunks)
    assert out == "Hello world!  Done!"


def test_end_tag_without_underscore():
    """An end tag variant without the underscore still closes the DSML block."""
    out, f = _drain(["<|dsml|tool_calls>hidden</|dsml|toolcalls> after"])
    assert "hidden" not in out
    assert "after" in out
    assert not f.in_dsml


def test_start_tag_split_across_chunks():
    """A start tag split mid-token is held and matched, not leaked."""
    out, _ = _drain(["hi <", "|dsml|tool_calls>x</|dsml|tool_calls> bye"])
    assert out == "hi  bye"


def test_nested_unknown_tags_filtered():
    """Unknown nested tags inside a DSML block are filtered, not leaked."""
    out, _ = _drain(["<dsml><inner>x</inner></dsml>after"])
    assert "x" not in out
    assert "inner" not in out
    assert out == "after"


def test_overflow_emits_warning_no_silent_drop():
    """A DSML block exceeding 1000 chars with no close warns and keeps prior text."""
    huge = "<|dsml|tool_calls>" + ("a" * 1200)
    out, f = _drain(["before ", huge])
    assert "before " in out  # pre-tag text not lost
    assert len(f.warnings) >= 1
    assert "1000" in f.warnings[0]


def test_end_tag_split_across_chunks():
    """An end tag split across two chunks still closes the block."""
    out, f = _drain(["<|dsml|tool_calls>x</|dsml|tool_", "calls> after"])
    assert "x" not in out
    assert "after" in out
    assert not f.in_dsml
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_dsml.py -q`
Expected: FAIL — `warnings` attribute missing; `test_end_tag_without_underscore` fails (no-underscore variant not matched); `test_overflow_emits_warning_no_silent_drop` fails (no warnings).

- [ ] **Step 3: Harden the filter**

In `backend/app/services/agent_service.py`, replace the entire `StreamingDSMLFilter` class (lines 82-175):

```python
class StreamingDSMLFilter:
    """Filters out DSML blocks from a text stream.

    Robust to tags split across chunk boundaries, nested/unknown tags, and
    unclosed blocks. An unclosed block exceeding the buffer cap is truncated
    with a recorded warning instead of being silently dropped.
    """

    # Normalized end-tag variants (lowercased, spaces removed, double-pipes collapsed).
    _END_TAGS = ("</|dsml|tool_calls>", "</|dsml|toolcalls>", "</dsml>")
    _START_TAGS = ("<|dsml", "<dsml")
    _BUFFER_CAP = 1000

    def __init__(self):
        self.buffer = ""
        self.in_dsml = False
        self.warnings: list[str] = []
        self._overflow_warned = False

    def _normalize(self, text: str) -> str:
        text = text.replace("｜", "|")
        text = text.replace(" ", "")
        while "||" in text:
            text = text.replace("||", "|")
        return text.lower()

    def feed(self, chunk: str) -> str:
        self.buffer += chunk
        output = []

        while True:
            if not self.in_dsml:
                idx = self.buffer.find("<")
                if idx == -1:
                    output.append(self.buffer)
                    self.buffer = ""
                    break

                sub = self.buffer[idx:]
                normalized = self._normalize(sub)

                if normalized.startswith(self._START_TAGS):
                    output.append(self.buffer[:idx])
                    self.buffer = sub
                    self.in_dsml = True
                    continue

                # Partial match for a start tag → hold in buffer
                if any(len(normalized) < len(p) and p.startswith(normalized) for p in self._START_TAGS):
                    output.append(self.buffer[:idx])
                    self.buffer = sub
                    break

                output.append(self.buffer[:idx + 1])
                self.buffer = self.buffer[idx + 1:]
            else:
                idx_end = self.buffer.lower().find("</")
                if idx_end == -1:
                    if len(self.buffer) > self._BUFFER_CAP:
                        if not self._overflow_warned:
                            self.warnings.append(
                                "⚠️ DSML block exceeded 1000 chars without a closing tag; truncating."
                            )
                            self._overflow_warned = True
                        self.buffer = self.buffer[-self._BUFFER_CAP:]
                    break

                sub = self.buffer[idx_end:]
                normalized = self._normalize(sub)

                if normalized.startswith(self._END_TAGS):
                    gt_idx = sub.find(">")
                    if gt_idx != -1:
                        self.buffer = sub[gt_idx + 1:]
                        self.in_dsml = False
                        continue

                # Partial match for an end tag → hold
                if any(len(normalized) < len(p) and p.startswith(normalized) for p in self._END_TAGS):
                    self.buffer = sub
                    break

                self.buffer = self.buffer[idx_end + 1:]
                break

        return "".join(output)

    def flush(self) -> str:
        if not self.in_dsml:
            res = self.buffer
            self.buffer = ""
            return res
        return ""
```

- [ ] **Step 4: Drain warnings in `chat()`**

In `backend/app/services/agent_service.py`, in `chat()` (lines 388-390), replace the flush block:

```python
        for warning in filter_obj.warnings:
            yield "thought", warning
        filter_obj.warnings.clear()

        flushed = filter_obj.flush()
        if flushed:
            yield "text", flushed
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_dsml.py tests/test_agent_service.py -q`
Expected: PASS — including the original `test_streaming_dsml_filter` in `test_agent_service.py`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent_service.py backend/tests/test_agent_dsml.py
git commit -m "fix(agent): harden DSML filter — split tags, variants, overflow warning (C5)"
```

---

### Task 7: Upload/data path sanitization (C8)

**Files:**
- Create: `backend/app/security.py`
- Modify: `backend/app/routers/agent.py:113-118` (`upload_endpoint`), `:121-134` (`get_data_endpoint`)
- Test: `backend/tests/test_agent_security.py` (create)

**Interfaces:**
- Produces: `security.secure_filename(name: str) -> str` — strips directory components, rejects `..`, keeps only `[A-Za-z0-9._-]`, never returns empty (falls back to `"upload"`).
- Produces: `security.safe_upload_path(file_path: str, upload_dir: str = UPLOAD_DIR) -> str` — resolves `file_path` against `upload_dir` (or accepts an absolute path inside it) and returns the resolved path; raises `HTTPException(400)` on traversal outside `upload_dir`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_agent_security.py`:

```python
"""Tests for agent upload/data path sanitization (C8)."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)  # noqa: S101


def test_secure_filename_strips_traversal():
    from app.security import secure_filename
    assert secure_filename("../../etc/passwd") == "passwd"
    assert secure_filename("normal_file.csv") == "normal_file.csv"
    assert secure_filename("a/b/c.csv") == "c.csv"
    assert secure_filename("..") == "upload"


def test_safe_upload_path_rejects_traversal():
    from app.security import safe_upload_path
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        safe_upload_path("../../etc/passwd")
    with pytest.raises(HTTPException):
        safe_upload_path("/etc/passwd")


def test_safe_upload_path_accepts_in_dir():
    from app.security import safe_upload_path
    p = safe_upload_path("data/agent_uploads/foo.csv")
    assert p.endswith("foo.csv")


def test_upload_sanitizes_filename():
    """POST /api/agent/upload with a traversal filename stores a safe basename."""
    import io
    files = {"file": ("../../evil.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")}
    res = client.post("/api/agent/upload", files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["filename"] == "evil.csv"
    assert ".." not in body["file_path"]
    # cleanup
    if os.path.exists(body["file_path"]):
        os.remove(body["file_path"])


def test_data_rejects_traversal_path():
    """GET /api/agent/data with a traversal path returns 400, not 500."""
    res = client.get("/api/agent/data", params={"file_path": "../../etc/passwd"})
    assert res.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_security.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.security'`.

- [ ] **Step 3: Create the security helpers**

Create `backend/app/security.py`:

```python
"""Security helpers for the agent router (C7/C8)."""
import os
import re

from fastapi import HTTPException

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def secure_filename(name: str) -> str:
    """Return a safe basename, stripped of path components and unsafe chars.

    Rejects traversal: only ``[A-Za-z0-9._-]`` survives, and directory
    components are dropped. Never returns empty.
    """
    if not name:
        return "upload"
    # Take the basename only (defends against both / and \ separators).
    base = re.split(r"[\\/]", name)[-1]
    cleaned = _SAFE_CHARS.sub("", base).strip(".")
    return cleaned or "upload"


def safe_upload_path(file_path: str, upload_dir: str = "data/agent_uploads") -> str:
    """Resolve *file_path* and ensure it lives inside *upload_dir*.

    Accepts either a bare filename, a path already inside ``upload_dir``,
    or an absolute path inside ``upload_dir``. Raises ``HTTPException(400)``
    on any traversal outside ``upload_dir``.
    """
    upload_dir_abs = os.path.abspath(upload_dir)
    # Strip any leading separators so an absolute path is re-anchored safely.
    candidate = os.path.join(upload_dir_abs, os.path.basename(file_path))
    # If the caller passed a path already containing the upload dir, honor it
    # after normalization.
    norm = os.path.abspath(file_path)
    if os.path.commonpath([norm, upload_dir_abs]) == upload_dir_abs:
        candidate = norm
    candidate_abs = os.path.abspath(candidate)
    if os.path.commonpath([candidate_abs, upload_dir_abs]) != upload_dir_abs:
        raise HTTPException(status_code=400, detail="Invalid file path.")
    return candidate_abs
```

- [ ] **Step 4: Sanitize the upload endpoint**

In `backend/app/routers/agent.py`, replace `upload_endpoint` (lines 113-118):

```python
@router.post("/upload")
async def upload_endpoint(file: UploadFile = File(...)):
    from app.security import secure_filename
    safe_name = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "file_path": file_path, "filename": safe_name}
```

- [ ] **Step 5: Validate the data endpoint path**

In `backend/app/routers/agent.py`, replace the path-resolution head of `get_data_endpoint` (lines 121-134 — from `async def get_data_endpoint` through the `raise HTTPException(status_code=404, ...)` block) with a sanitized version:

```python
@router.get("/data")
async def get_data_endpoint(file_path: str):
    """Retrieve and parse CSV/Excel file rows as JSON objects."""
    from app.security import safe_upload_path
    try:
        file_path = safe_upload_path(file_path)
    except HTTPException:
        raise
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {os.path.basename(file_path)}")
    try:
```

Leave the rest of `get_data_endpoint` (the pandas parsing body) unchanged. The old multi-location fallback lookup is removed — files are now only ever served from within `UPLOAD_DIR`, which is where `upload_endpoint` writes them.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_security.py tests/test_agent_router.py -q`
Expected: PASS. Note: `test_agent_data_geocoding` in `test_agent_router.py` (if it relies on the old multi-location fallback) may need its fixture path adjusted — if it fails, update the test to pass a path inside `data/agent_uploads/`. Do not re-add the traversal fallback.

- [ ] **Step 7: Commit**

```bash
git add backend/app/security.py backend/app/routers/agent.py backend/tests/test_agent_security.py
git commit -m "fix(agent): sanitize upload filename + validate data path (C8)"
```

---

### Task 8: Rate limiting + API-key auth on `/api/agent/*` (C7)

**Files:**
- Modify: `backend/app/security.py` (add `require_agent_key`)
- Modify: `backend/app/routers/agent.py` (add `request: Request` + `@limiter.limit` + `Depends(require_agent_key)` to chat/upload/data)
- Test: `backend/tests/test_agent_security.py` (append)

**Interfaces:**
- Produces: `security.require_agent_key` — a FastAPI dependency reading the `X-Agent-Key` header. When `Settings.agent_api_key` is unset (dev default), the endpoint is open. When set, requests without a matching header get `401`.
- Produces: `POST /api/agent/chat` is rate-limited at `Settings.agent_rate_limit_chat` (default `"20/minute"`) and gated by `require_agent_key`. `POST /api/agent/upload` at `10/minute`, `GET /api/agent/data` at `60/minute`, both gated. `GET /api/agent/providers/status` and `GET /api/agent/active-spec` remain open + `60/minute` (status must be fetchable before any auth).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_agent_security.py`:

```python
def test_chat_open_when_no_api_key_configured(monkeypatch):
    """With AGENT_API_KEY unset, chat works without a header (dev default)."""
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "agent_api_key", None)
    res = client.post("/api/agent/chat", json={"message": "hello"})
    assert res.status_code == 200


def test_chat_requires_key_when_configured(monkeypatch):
    """With AGENT_API_KEY set, chat without the header is 401."""
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "agent_api_key", "secret-key")
    res = client.post("/api/agent/chat", json={"message": "hello"})
    assert res.status_code == 401


def test_chat_accepts_valid_key(monkeypatch):
    """With AGENT_API_KEY set, chat with the matching header is 200."""
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "agent_api_key", "secret-key")
    res = client.post(
        "/api/agent/chat",
        json={"message": "hello"},
        headers={"X-Agent-Key": "secret-key"},
    )
    assert res.status_code == 200


def test_providers_status_open_without_key(monkeypatch):
    """providers/status stays open so the frontend can bootstrap."""
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "agent_api_key", "secret-key")
    res = client.get("/api/agent/providers/status")
    assert res.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_security.py -q`
Expected: FAIL — `test_chat_requires_key_when_configured` gets 200 (no gate yet).

- [ ] **Step 3: Add the `require_agent_key` dependency**

In `backend/app/security.py`, append:

```python
from fastapi import Header
from app.config import get_settings


async def require_agent_key(x_agent_key: str | None = Header(default=None, alias="X-Agent-Key")) -> bool:
    """Gate agent endpoints behind an API key when one is configured.

    When ``Settings.agent_api_key`` is unset (the dev default), the endpoint
    is open. When set, requests must supply a matching ``X-Agent-Key`` header.
    """
    expected = get_settings().agent_api_key
    if expected and x_agent_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing agent API key.")
    return True
```

- [ ] **Step 4: Apply rate limits + auth to the agent endpoints**

In `backend/app/routers/agent.py`, update the imports (top of file) to add:

```python
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from app.rate_limiter import limiter, upload_limit
from app.config import get_settings
from app.security import require_agent_key
```

(Adjust the existing `from fastapi import ...` line to include `Depends`, `Request` and keep `UploadFile`, `File`.)

Then update the endpoint signatures:

`chat_endpoint` — add `request: Request`, the rate-limit decorator, and the auth dependency:

```python
@router.post("/chat")
@limiter.limit(get_settings().agent_rate_limit_chat)
async def chat_endpoint(request: Request, payload: ChatRequest = Depends()):
    history = [{"role": m.role, "content": m.content} for m in payload.history]
    agent_instance = SurveillanceAgent(
        provider=payload.provider,
        model=payload.model,
        history=history,
        context=payload.context.model_dump(exclude_none=True) if payload.context else None,
    )
```

Rename the internal `request` references inside `chat_endpoint` from `request` to `payload` (there are none beyond the parameter — `request.message` etc. become `payload.message`). Update the `response_generator` to use `payload.message`:

```python
            async for token_type, token in agent_instance.chat(payload.message):
```

`upload_endpoint` — add `request: Request`, rate limit, auth:

```python
@router.post("/upload")
@limiter.limit(upload_limit())
async def upload_endpoint(request: Request, file: UploadFile = File(...)):
```

`get_data_endpoint` — add `request: Request`, rate limit, auth:

```python
@router.get("/data")
@limiter.limit("60/minute")
async def get_data_endpoint(request: Request, file_path: str):
```

`providers_status_endpoint` and `get_active_spec` — add `request: Request` + `@limiter.limit("60/minute")` (no auth):

```python
@router.get("/providers/status")
@limiter.limit("60/minute")
async def providers_status_endpoint(request: Request):
    return provider_status()


@router.get("/active-spec")
@limiter.limit("60/minute")
async def get_active_spec(request: Request):
```

Apply the auth dependency to chat/upload/data by adding `Depends(require_agent_key)` as a parameter to each of those three:

```python
async def chat_endpoint(request: Request, payload: ChatRequest = Depends(), _auth: bool = Depends(require_agent_key)):
async def upload_endpoint(request: Request, file: UploadFile = File(...), _auth: bool = Depends(require_agent_key)):
async def get_data_endpoint(request: Request, file_path: str, _auth: bool = Depends(require_agent_key)):
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && source venv/bin/activate && PYTHONPATH=. pytest tests/test_agent_security.py tests/test_agent_router.py tests/test_agent_context.py -q`
Expected: PASS. `test_agent_chat_endpoint` passes because the test env has `AGENT_API_KEY` unset (open). The four C7 tests pass.

- [ ] **Step 6: Manual rate-limit verification**

With the backend running, send 25 rapid `POST /api/agent/chat` requests (no API key configured). Expect the 21st onward to return `429`. This is a manual check because slowapi timing under TestClient is not deterministic enough to assert in CI.

- [ ] **Step 7: Commit**

```bash
git add backend/app/security.py backend/app/routers/agent.py backend/tests/test_agent_security.py
git commit -m "feat(agent): rate-limit + API-key gate on /api/agent/* (C7)"
```

---

### Task 9: `agentStore` — persistence, context, `ERROR` handling, provider init, prefill (C1/C4/C6/C9 frontend)

**Files:**
- Modify: `frontend/src/store/agentStore.ts` (whole file)
- Gate: `cd frontend && npm run build && npm run lint` + manual verification (no test runner)

**Interfaces:**
- Consumes: `useAppStore` (`frontend/src/store/appStore.ts`) for `selectedLGA` / `selectedLGAId` / `filters.dateRange` — used to build `context`. These exist today, so this task does **not** depend on Section 1.
- Produces: `ChatMessage` gains `error?: boolean`. `AgentState` gains `pendingPrompt: string | null`, `userOverrodeProvider: boolean`, and actions `prefillPrompt(text)`, `clearPendingPrompt()`, `setLastAssistantError()`.
- Produces: `sendMessage` posts `{ message, provider, model, history, context }` where `context` is built from `useAppStore` + `window.location.pathname`.
- Produces: `ERROR:` stream lines mark the last assistant message errored and append the message. `messages` + `thoughts` + `provider` + `model` persist to `localStorage` (`cholera-agent-storage`); `clearChat` clears storage.
- Produces: `fetchKeysStatus` initializes `provider`/`model` from the response's `default_provider`/`default_model` (Task 1) when the user has not overridden them.

- [ ] **Step 1: Update imports and `ChatMessage`**

In `frontend/src/store/agentStore.ts`, change the top import and the `ChatMessage` interface:

```ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { useAppStore } from './appStore';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  error?: boolean;
}
```

- [ ] **Step 2: Extend the `AgentState` interface**

Add the new fields/actions to `AgentState` (insert near the other UI state and actions):

```ts
  // Prefill (C3) + provider-override tracking (C9)
  pendingPrompt: string | null;
  userOverrodeProvider: boolean;

  // ...existing actions...
  prefillPrompt: (text: string) => void;
  clearPendingPrompt: () => void;
  setLastAssistantError: () => void;
```

- [ ] **Step 3: Wrap the store creator in `persist` and add the new state/actions**

Replace the `export const useAgentStore = create<AgentState>()((set, get) => ({` line and the initial-state block so the whole creator is wrapped in `persist`. The new initial state adds `pendingPrompt: null`, `userOverrodeProvider: false`. Replace the `provider`/`model` lines, the `clearChat`, `fetchKeysStatus`, and `setProvider` actions, and add the three new actions. The full new creator opening + changed actions:

```ts
export const useAgentStore = create<AgentState>()(
  persist(
    (set, get) => ({
      messages: [],
      thoughts: [],
      isStreaming: false,

      provider: 'deepseek',
      model: 'deepseek-v4-flash',
      userOverrodeProvider: false,

      providerKeysStatus: DEFAULT_KEYS_STATUS,
      keysStatusLoaded: false,

      sidebarOpen: true,
      consoleOpen: false,
      consoleHeight: 220,

      generatedUiSpec: null,
      uploadedDataset: null,
      hasNewUiNotification: false,

      pendingPrompt: null,

      addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
      appendToLastAssistant: (text) =>
        set((s) => {
          const msgs = [...s.messages];
          const last = msgs[msgs.length - 1];
          if (last && last.role === 'assistant') {
            msgs[msgs.length - 1] = { ...last, content: last.content + text };
          }
          return { messages: msgs };
        }),
      setLastAssistantError: () =>
        set((s) => {
          const msgs = [...s.messages];
          const last = msgs[msgs.length - 1];
          if (last && last.role === 'assistant') {
            msgs[msgs.length - 1] = { ...last, error: true };
          }
          return { messages: msgs };
        }),
      addThought: (thought) => set((s) => ({ thoughts: [...s.thoughts, thought] })),
      setStreaming: (streaming) => set({ isStreaming: streaming }),
      setProvider: (provider) => {
        const opt = PROVIDER_OPTIONS.find((p) => p.id === provider);
        set({ provider, model: opt?.models[0]?.id || '', userOverrodeProvider: true });
      },
      setModel: (model) => set({ model, userOverrodeProvider: true }),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setConsoleOpen: (open) => set({ consoleOpen: open }),
      setConsoleHeight: (height) =>
        set({ consoleHeight: Math.max(120, Math.min(500, height)) }),
      setGeneratedUiSpec: (generatedUiSpec) => set({ generatedUiSpec }),
      setUploadedDataset: (uploadedDataset) => set({ uploadedDataset }),
      setHasNewUiNotification: (hasNewUiNotification) => set({ hasNewUiNotification }),
      clearChat: () =>
        set({
          messages: [],
          thoughts: [],
          generatedUiSpec: null,
          uploadedDataset: null,
          hasNewUiNotification: false,
          pendingPrompt: null,
        }),
      clearThoughts: () => set({ thoughts: [] }),

      prefillPrompt: (text) => set({ sidebarOpen: true, pendingPrompt: text }),
      clearPendingPrompt: () => set({ pendingPrompt: null }),

      fetchKeysStatus: async () => {
        try {
          const res = await fetch(`${API_BASE}/providers/status`);
          if (!res.ok) return;
          const data = await res.json();
          set((s) => ({
            providerKeysStatus: { ...DEFAULT_KEYS_STATUS, ...data },
            keysStatusLoaded: true,
            // Initialize provider/model from server defaults unless the user chose one.
            ...(s.userOverrodeProvider
              ? {}
              : {
                  provider: (data.default_provider as AgentProvider) || s.provider,
                  model: data.default_model || s.model,
                }),
          }));
        } catch {
          // silently ignore — will show null (unknown) in UI
        }
      },
```

Leave the `sendMessage` and `uploadFile` actions in place for now (they are edited in Step 4 and Step 5). Close the creator with the persist config — at the very end of the file, replace the final `}));` with:

```ts
      uploadFile: async (file: File) => {
        try {
          const formData = new FormData();
          formData.append('file', file);
          const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
          if (!res.ok) return null;
          const data = await res.json();
          return data.file_path || null;
        } catch {
          return null;
        }
      },
    }),
    {
      name: 'cholera-agent-storage',
      partialize: (s) => ({
        messages: s.messages,
        thoughts: s.thoughts,
        provider: s.provider,
        model: s.model,
      }),
    }
  )
);
```

Make sure the existing `uploadFile` action body that was previously in the creator is **removed** (it now appears once, above the persist config). Do not define `uploadFile` twice.

- [ ] **Step 4: Build `context` and include it in the POST body**

In `sendMessage`, replace the `try { const res = await fetch(`${API_BASE}/chat`, { ... body: JSON.stringify({ message: text, provider, model, history }), });` block with one that builds context first:

```ts
    // Build dashboard context from appStore (C1).
    const app = useAppStore.getState();
    const dr = app.filters?.dateRange;
    const context = {
      lga_id: app.selectedLGAId ?? undefined,
      lga_name: app.selectedLGA?.name ?? undefined,
      date_range:
        dr?.startDate
          ? { start: dr.startDate, end: dr.endDate ?? dr.startDate }
          : undefined,
      active_alerts: undefined,
      current_view: typeof window !== 'undefined' ? window.location.pathname : undefined,
    };

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, provider, model, history, context }),
      });
```

`JSON.stringify` drops `undefined` values, so omitted context fields are not sent. The rest of `sendMessage` (the `!res.ok` handling, reader loop) stays — but the reader loop is edited in Step 5.

- [ ] **Step 5: Handle `ERROR:` lines in the stream reader**

In the `sendMessage` reader loop, add an `ERROR:` branch. In the `for (const line of lines) {` block, after the `UI_SPEC:` branch (before the closing of the `for`), add:

```ts
          } else if (line.startsWith('ERROR:')) {
            try {
              const content = JSON.parse(line.slice('ERROR:'.length));
              get().setLastAssistantError();
              appendToLastAssistant(`\n⚠️ ${content}`);
            } catch (err) {
              console.error('Error parsing ERROR JSON:', err, line);
            }
          }
```

Do the same in the flush-tail block (the `if (buffer) { ... }` block after the loop): add an `else if (line.startsWith('ERROR:'))` branch mirroring the above. Also rename the three `console.error('Error parsing ... JSON:', err, line)` calls' unused `err` variables to `_err` if lint flags them as unused — only if `npm run lint` fails on them (it currently passes with the existing ones, so no change is expected).

- [ ] **Step 6: Typecheck + build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: PASS. Fix any unused-variable or type errors (the most likely is a duplicate `uploadFile` if Step 3 was not applied carefully — ensure it appears exactly once).

- [ ] **Step 7: Manual verification**

With backend (port 8000, no `AGENT_API_KEY` set) and frontend (port 5173) running, open http://localhost:5173/ and confirm:
- Refresh the page mid-conversation: prior `messages` and `thoughts` reappear (localStorage round-trip — C6).
- Select an LGA on the map, then ask the copilot "what's the risk here?": the agent's response references the selected LGA (context injected — C1). Verify in the browser DevTools Network tab that the `/api/agent/chat` request body includes a `context` object with `lga_name` and `current_view`.
- Click "Clear chat": messages/thoughts disappear and survive a refresh (storage cleared — C6).
- Reload with the dev backend stopped (or force a stream error): an `ERROR:` event renders an inline `⚠️` error state on the assistant bubble (C4).
- The provider/model selectors initialize to the server's `default_provider`/`default_model` on first load (C9); choosing a different provider sticks across reload only if `userOverrodeProvider` was set (it is, via `setProvider`).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/store/agentStore.ts
git commit -m "feat(frontend): persist chat, build context, handle ERROR, init provider (C1/C4/C6/C9)"
```

---

### Task 10: Contextual entry points + inline error UI (C3, C4 frontend)

**Files:**
- Modify: `frontend/src/components/Agent/AgentSidebar.tsx` (consume `pendingPrompt`; render error state on `MessageBubble`)
- Modify: `frontend/src/components/Dashboard/ActiveAlertsRail.tsx`, `FloodEventsRail.tsx`, `DashboardKpiRow.tsx`, and the `RiskChoropleth` component — add "Ask copilot about this" buttons
- Gate: `cd frontend && npm run build && npm run lint` + manual verification
- **Dependency:** This task requires the Section-1 (Dashboard Refactor) rail/KPI/choropleth components to exist. If they do not, this task is blocked; Tasks 1–9 still ship independently.

**Interfaces:**
- Consumes: `useAgentStore` actions `prefillPrompt` (Task 9) and state `pendingPrompt`.
- Produces: `MessageBubble` accepts an `error?: boolean` prop and renders a red error banner. `AgentSidebar` consumes `pendingPrompt` into the input. Each dashboard rail/KPI gains an "Ask copilot" button calling `prefillPrompt(...)`.

- [ ] **Step 1: Render the inline error state on `MessageBubble`**

In `frontend/src/components/Agent/AgentSidebar.tsx`, extend the `MessageBubble` signature (line 189) to accept `error`:

```tsx
function MessageBubble({
  role,
  content,
  timestamp,
  isStreaming,
  error,
}: {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  error?: boolean;
}) {
```

Then, in the assistant branch of `MessageBubble` (the `return ( ... )` after the `if (role === 'user')` block), add an error banner at the top of the bubble when `error` is true. Insert just inside the assistant bubble's outer `<div>`:

```tsx
      {error && (
        <div className="mb-2 rounded-lg border border-red-300/50 bg-red-50 px-3 py-2 text-[12px] text-red-700">
          ⚠️ This response encountered an error. Try sending your message again.
        </div>
      )}
```

If the assistant bubble's className does not already adapt on error, add `error ? 'border-red-300/60' : ''` to its border classes (only if a border class exists to extend — otherwise leave styling as-is; the banner alone is sufficient).

- [ ] **Step 2: Pass `error` from the message list**

In the `messages.map` block (around line 716), pass the new prop:

```tsx
          messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              role={msg.role}
              content={msg.content}
              timestamp={msg.timestamp}
              isStreaming={msg.role === 'assistant' && msg.content === '' && isStreaming}
              error={msg.error}
            />
          ))
```

- [ ] **Step 3: Consume `pendingPrompt` in the input**

In `AgentSidebar`, pull `pendingPrompt` and `clearPendingPrompt` from the store (add to the destructuring near line 375 where `sendMessage` etc. are pulled), then add an effect that pushes a prefill into the input. Place near the existing `useEffect(() => { if (sidebarOpen) inputRef.current?.focus(); }, [sidebarOpen])`:

```tsx
  useEffect(() => {
    if (pendingPrompt) {
      setInput(pendingPrompt);
      clearPendingPrompt();
      inputRef.current?.focus();
    }
  }, [pendingPrompt, clearPendingPrompt]);
```

- [ ] **Step 4: Add "Ask copilot about this" buttons to the dashboard rails**

This step adds a small button to each of the four Section-1 dashboard components. In each file, import the store and add a button in the component's header area. The reusable button + handler pattern (adapt the prompt text per component):

```tsx
import { useAgentStore } from '../../store/agentStore';

// inside the component:
const prefillPrompt = useAgentStore((s) => s.prefillPrompt);
```

`ActiveAlertsRail.tsx` — in the header, next to the title:
```tsx
<button
  onClick={() => prefillPrompt('Explain the active alerts shown on the dashboard. Which LGAs are most affected and why?')}
  className="text-[11px] text-primary hover:underline"
>
  Ask copilot
</button>
```

`FloodEventsRail.tsx`:
```tsx
<button
  onClick={() => prefillPrompt('Summarise the recent flood events shown on the dashboard and their overlap with high-risk LGAs.')}
  className="text-[11px] text-primary hover:underline"
>
  Ask copilot
</button>
```

`DashboardKpiRow.tsx` — render one button beneath the KPI row that references the current LGA context:
```tsx
<button
  onClick={() => {
    const s = useAgentStore.getState();
    const app = useAppStore.getState();
    const lga = app.selectedLGA?.name;
    prefillPrompt(lga ? `Explain the dashboard KPIs for ${lga}.` : 'Explain the dashboard KPIs and what each one measures.');
  }}
  className="text-[11px] text-primary hover:underline"
>
  Ask copilot about these KPIs
</button>
```
(Add `import { useAppStore } from '../../store/appStore';` to `DashboardKpiRow.tsx` if not present.)

`RiskChoropleth` (the map component) — add a button that appears when an LGA is selected:
```tsx
<button
  onClick={() => {
    const app = useAppStore.getState();
    const lga = app.selectedLGA?.name;
    if (lga) prefillPrompt(`Give me the latest risk breakdown for ${lga} and what's driving it.`);
  }}
  className="text-[11px] text-primary hover:underline disabled:opacity-40"
  disabled={!useAppStore.getState().selectedLGA}
>
  Ask copilot about this LGA
</button>
```

The exact insertion point in each Section-1 component is next to its existing header/title element. If a component does not yet have a header slot, place the button at the top-right of its container `<div>`.

- [ ] **Step 5: Typecheck + build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: PASS. If `ActiveAlertsRail.tsx` / `FloodEventsRail.tsx` / `DashboardKpiRow.tsx` / the choropleth component do not exist yet (Section 1 not merged), this step fails with a module-not-found error — that is the expected signal that this task is blocked on Section 1. Do not stub the components; wait for Section 1.

- [ ] **Step 6: Manual verification**

With both servers running, open http://localhost:5173/ and confirm:
- Clicking "Ask copilot" on the alerts rail opens the agent sidebar (`sidebarOpen: true`) with the pre-filled prompt in the input, focused.
- The same for the flood-events rail, the KPI row button, and the map button (the map button is disabled until an LGA is selected).
- Pressing Enter sends the pre-filled message and the response references the relevant panel context (context injected in Task 9).
- An errored assistant message shows the red `⚠️` banner.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Agent/AgentSidebar.tsx frontend/src/components/Dashboard/
git commit -m "feat(frontend): contextual copilot entry points + inline error UI (C3/C4)"
```

---

## Self-Review (completed)

- **Spec coverage:** C1 (context injection) → Tasks 2 (backend) + 9 (frontend context build). C2 (typed tools) → Tasks 3 (service) + 4 (wiring + query_db cap). C3 (contextual entry points) → Task 10. C4 (streaming ERROR event) → Task 5 (backend) + 9 (frontend parse) + 10 (UI). C5 (DSML hardening) → Task 6. C6 (persistence) → Task 9 (localStorage + clearChat); server-side store is an explicit non-goal (spec line 229-230). C7 (auth + rate limiting) → Task 8. C8 (upload path sanitization) → Task 7. C9 (provider config consolidation) → Task 1 (backend Settings + providers/status + agent defaults) + 9 (frontend init from providers/status). All nine spec items covered.
- **Deviation documented:** C7 spec says "Apply the app's auth dependency." No backend auth exists (frontend `authStore` is client-side only). Task 8 adds a router-scoped `X-Agent-Key` gate env-gated by `AGENT_API_KEY` (open in dev) instead. This is the minimal real auth that fits the codebase and is called out in Global Constraints + Task 8. C6 spec mentions "Send full tool-call turns in history" — the frontend store never retained tool-call turns (tool execution is server-side), so full tool-call history would require a server-side store, which is an explicit non-goal. Task 9 instead persists client messages/thoughts and preserves prior non-empty turns in `history` (the existing behavior), which is the in-scope improvement; the server-side retention is noted as out of scope.
- **Placeholder scan:** No TBD/TODO. Two intentional "verify the exact insertion point" notes (Task 10 Step 4 rail button placement; Task 7 Step 6 possible `test_agent_data_geocoding` fixture adjustment) point the engineer at concrete locations with explicit fallbacks — these are verification steps, not placeholders.
- **Type consistency:** `AgentContext` fields (Task 2 backend) match the `context` object built in Task 9 (`lga_id`, `lga_name`, `date_range`, `active_alerts`, `current_view`). `provider_status()` return shape (Task 1: adds `default_provider`/`default_model`) matches what `fetchKeysStatus` reads in Task 9. `ChatMessage.error` (Task 9) is read by `MessageBubble` (Task 10). `prefillPrompt`/`clearPendingPrompt`/`pendingPrompt` (Task 9 store) are consumed in Task 10. `_dispatch_tool` signature (Task 4) is used by the `_chat_raw` rewrite (Task 5). `StreamingDSMLFilter.warnings` (Task 6) is drained in `chat()`. The `ERROR` event type name is consistent across Task 5 (backend yields `"error"`) and Task 9 (frontend matches `ERROR:`).
- **Protocol consistency:** The newline protocol gains exactly one new event type `ERROR:<json>\n`, produced by the router's existing `else: yield f"{token_type.upper()}:{json.dumps(token)}\n"` branch (no router format change needed beyond passing the event through, which `chat()` already does).
