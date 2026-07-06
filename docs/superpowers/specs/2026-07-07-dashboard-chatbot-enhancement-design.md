# Dashboard Refactor + Chatbot Enhancement — Design

**Date:** 2026-07-07
**Branch:** `feat/groundsource-cholera-integration` (PR #6)
**Status:** Approved, ready for implementation plan

## Problem

The frontend dashboard shows stale and fake data, and the new Groundsource+Cholera
integration (flood events, alerts, v2.0 risk components, correlation analytics) is not
surfaced. Separately, the agent copilot is weakly integrated: it has real tools but
receives no dashboard context, accesses data only via raw SQL, has fragile streaming
and no persistence, and its endpoints are unauthenticated.

### Root causes (dashboard)
- "Case Rate vs. Precipitation" chart uses `Math.random()` — calls no API
  (`frontend/src/hooks/useDashboardLogic.ts:46-55`).
- Satellite-feed and top-risk chart have hardcoded mock fallbacks
  (`useDashboardLogic.ts:11-15, 76-82`).
- KPI "Confirmed Cases" = `SUM(new_cases) WHERE report_date >= today-30d`
  (`backend/app/routers/lgas.py:168`); real cholera CSV ends 2025-12, today is 2026-07,
  so the window is empty → KPI shows 0.
- Hardcoded `|| 18` LGA fallback (`DashboardView.tsx:376`, `ReportsView.tsx:75`);
  DB now has 774 nationwide LGAs.
- `last_updated = date.today()` always (`lgas.py:217`), regardless of data recency.
- Alert Level / Active Outbreaks KPIs are derived from risk-level counts; the alert
  engine is ignored (no call to `/api/alerts`).
- `RiskScore` TS type (`types/index.ts:53-68`) omits v2.0 fields; risk-scores endpoint
  (`analytics.py:112-170`) does not return `flood_event_score`, `recent_flood_events`,
  `vulnerability_score`, `algorithm_version`.
- No flood-events router exists; flood events are computed into risk scores but never
  exposed.

### Gaps (chatbot)
- `ChatRequest` (`agent.py:19-23`) carries only `message/provider/model/history` — no
  dashboard context (selected LGA, date range, active alerts).
- Data access is raw SQL only (`query_db`, `agent_service.py:211-224`); no typed domain
  tools; only guard is a `^SELECT` regex (`:178`).
- `StreamingDSMLFilter` (`:82-175`) only strips DSML; hardcoded end-tags; 1000-char
  buffer cap silently drops content; minimal boundary tests.
- No terminal streaming error event; frontend silently `console.error`s parse failures
  (`agentStore.ts:322,329,349`).
- No persistence — refresh loses chat; `history` drops tool-call turns (`:274-276`).
- `/api/agent/*` has no auth or rate limiting; upload path is unsanitized (`agent.py:115`).
- Provider/model defaults hardcoded in three places (`agent.py:21-22`,
  `agent_service.py:196-197`, `agentStore.ts:202-203`).

## Goals

- Dashboard: show **real, date-aware** data (latest-available period), surface the four
  new integration data sources, remove all mock/random data.
- Chatbot: make the agent **context-aware** and give it **typed domain tools**, harden
  streaming/DSML, persist conversations, and secure the endpoints.

## Non-goals

- Backfilling or synthesizing 2026 case data. The dashboard becomes date-aware and
  defaults to the latest-available real period.
- Redesigning routes other than the main dashboard (`/`).
- Replacing the agent's LLM provider or adding new providers.

## Section 1 — Dashboard refactor + redesign

### Architecture

Layout A (approved): KPI row on top; choropleth map dominant upper-left with a right
rail (alerts, flood events); two charts across the bottom. A date-range selector sits
above the KPI row and drives every panel. The agent copilot sidebar remains mounted
globally.

```
┌─────────────────────────────────────────────────────────┐
│  DateRangeSelector  (latest-available 30d default)       │
├─────────────────────────────────────────────────────────┤
│  [Cases] [Active alerts] [Alert lvl] [Rainfall] [Floods] │
├──────────────────────────────────┬──────────────────────┤
│                                  │  🚨 Active alerts     │
│      Risk choropleth map         │     (top 5)           │
│   + flood-event overlay toggle   ├──────────────────────┤
│                                  │  🌊 Recent floods     │
│                                  │     (top 5)           │
├─────────────────┬────────────────┴──────────────────────┤
│  Correlation    │  Top-LGA v2.0 risk breakdown          │
│  (flood↔cholera) │  (case + flood + flood_event score)   │
└─────────────────┴───────────────────────────────────────┘
```

### Backend changes

**B1. `/api/lgas/dashboard` refactor** (`backend/app/routers/lgas.py:160-218`)
- Accept optional `start_date` / `end_date` query params (ISO dates).
- Default window = **latest-available**: compute `max_report_date = max(CaseReport.report_date)`;
  window = `[max_report_date - 30d, max_report_date]`.
- `total_cases` / `total_deaths` summed over the selected window.
- Replace derived alert counts with real data: `active_alerts_count` and `alert_level`
  from the alert service (`/api/alerts/stats/summary` logic).
- Add `flood_events_count` (flood_events overlapping the window).
- `last_updated` = real max data date (`max_report_date`, or EnvironmentalData max if
  no cases), not `date.today()`.
- `total_lgas` already returns the real count (774); frontend fallback removed.

**B2. `/api/analytics/risk-scores` extend** (`backend/app/routers/analytics.py:112-170`)
- Return `flood_event_score`, `recent_flood_events`, `vulnerability_score`,
  `algorithm_version` per LGA alongside existing fields.

**B3. New `/api/flood-events` router** (`backend/app/routers/flood_events.py`)
- `GET /api/flood-events` — list recent flood events.
- Query params: `lga_id` (optional), `start_date`/`end_date` (optional), `limit`
  (default 50, max 200).
- Returns: `uuid`, `lga_id`, `lga_name`, `start_date`, `end_date`, `duration_days`,
  `area_km2`, `created_at`.
- Register the router in `app/main.py`.

**B4. Wire existing endpoints** — `/api/analytics/correlation` and
`/api/alerts/stats/summary` are already implemented; the frontend will consume them
directly.

### Frontend changes

**F1. Date-range context**
- New `DateRangeSelector` component (presets: 30d, 90d, 12m, custom date pickers).
- Selected range held in a small shared store (or React context); passed as query params
  to `useDashboard`, `useRiskScores`, and the new flood-events/correlation hooks.
- The dashboard endpoint returns `applied_window: {start, end}` and `max_data_date`
  alongside the summary; `DateRangeSelector` initializes to `applied_window` on first
  load. No client-side latest-available computation.

**F2. `DashboardView` rebuild** (`frontend/src/components/Dashboard/DashboardView.tsx`)
- New/extracted components:
  - `DashboardKpiRow` — 5 KPIs from `useDashboard` (real data).
  - `RiskChoropleth` — existing `ChoroplethMap` + a flood-event polygon overlay toggle.
  - `ActiveAlertsRail` — top-5 active alerts (clickable → `/alerts`).
  - `FloodEventsRail` — top-5 recent flood events (area, duration).
  - `CorrelationChart` — real `/api/analytics/correlation` data.
  - `RiskBreakdownChart` — stacked components per top-LGA (case_score, flood_score,
    flood_event_score) from extended `useRiskScores`.

**F3. Remove all mock data**
- Delete mock fallbacks in `useDashboardLogic.ts:11-15` (satellite feed),
  `:46-55` (random chart), `:76-82` (random risk). Replace `useChartDataLogic` with
  real correlation/weekly data.
- Remove `|| 18` fallbacks in `DashboardView.tsx:376` and `ReportsView.tsx:75`.
- `TrendsReport` in `ReportsView.tsx:618-669` is out of scope (reports route) but
  flagged for a follow-up.

**F4. Type + hook updates**
- Extend `RiskScore` in `frontend/src/types/index.ts:53-68` with `flood_event_score`,
  `recent_flood_events`, `vulnerability_score`, `algorithm_version`.
- `useDashboard` and `useRiskScores` accept the date range as params.

### Error handling
- Backend: endpoints return 422 for bad date params; latest-available default never
  throws on empty DB (returns zeros with `last_updated: null`).
- Frontend: React Query error states render an inline "data unavailable" message per
  panel, never a blank panel.

### Testing
- Backend:
  - `/api/lgas/dashboard` with explicit dates and with latest-available default.
  - `/api/analytics/risk-scores` returns v2.0 fields.
  - `/api/flood-events` filtering and pagination.
- Frontend:
  - `DashboardKpiRow` renders real values; `DateRangeSelector` updates queries.
  - No component depends on mock fallbacks.

---

## Section 2 — Chatbot enhancement

### Architecture

The agent stays a LiteLLM-backed streamer (`SurveillanceAgent`) with the
newline-delimited `THOUGHT/TEXT/UI_SPEC` protocol. We add a `context` field, typed
domain tools, an `ERROR` event, persistence, and endpoint security — without changing
the streaming transport.

### Core integration

**C1. Context injection**
- Extend `ChatRequest` (`backend/app/routers/agent.py:19-23`) with
  `context: { lga_id?, lga_name?, date_range?, active_alerts?, current_view? }`.
- `agentStore.sendMessage` (`frontend/src/store/agentStore.ts:274-283`) builds `context`
  from the dashboard date-range store, the currently selected LGA (if any), a shallow
  active-alerts summary, and the current route.
- Backend injects `context` into the system prompt at the start of `_chat_raw`
  (`agent_service.py:620-624`) as a structured "Current dashboard context" block.

**C2. Typed domain tools** (`agent_service.py`)
- Add four tools (OpenAI function schema in `_tools_schema`, dispatched in `_chat_raw`):
  - `get_lga_risk(lga_id_or_name)` → latest v2.0 RiskScore + components.
  - `get_active_alerts(lga_id?, severity?, limit?)` → active alerts (capped).
  - `get_flood_events(lga_id?, date_range?, limit?)` → recent flood events.
  - `get_cholera_cases(lga_id?, date_range?, limit?)` → aggregated cases.
- Each calls a dedicated service function (reuses queries from B1/B3 and the alerts
  router) and returns structured JSON with row limits.
- Add a concise schema description to `SYSTEM_INSTRUCTIONS` so the agent knows the
  domain model without raw SQL.
- Keep `query_db` as a fallback tool but document that the typed tools are preferred;
  enforce a row limit on `query_db`.

**C3. Contextual entry points**
- "Ask copilot about this" buttons on: the alerts rail, the flood-events rail, each KPI
  (where meaningful), and the map (for the selected LGA).
- Clicking opens `AgentSidebar` (sets `sidebarOpen: true`) with a pre-filled prompt
  built from the panel context, e.g. *"Explain the active alerts in {LGA} for {range}."*
- A new `agentStore.prefillPrompt(text)` action supports this.

### Robustness

**C4. Streaming error handling**
- Backend: add an `ERROR` event type to the newline-delimited stream. Per-chunk
  exceptions inside `chat()` emit `ERROR: {message}` then end the stream (replacing the
  current catch-into-THOUGHT/TEXT at `agent_service.py:734-743`).
- Frontend: `agentStore` handles `ERROR:` by marking the assistant message as errored
  and rendering an inline error state (replaces silent `console.error` at
  `:322,329,349`).

**C5. DSML filter hardening** (`StreamingDSMLFilter`, `agent_service.py:82-175`)
- Robust partial-tag handling across chunks (buffer underrun/overrun).
- Accept more end-tag variants; no silent 1000-char drop (emit a `THOUGHT` warning
  instead).
- Add boundary tests: split tags at every position, nested tags, unknown tags.

**C6. Conversation persistence**
- Persist `messages` and `thoughts` to `localStorage` in `agentStore` (load on init,
  save on change); `clearChat` clears storage.
- Send full tool-call turns in `history` (currently dropped at `:274-276`) so multi-turn
  tool conversations retain context.
- Server-side conversation store is a non-goal for this pass; client persistence is
  sufficient.

### Security

**C7. Auth + rate limiting on `/api/agent/*`**
- Apply the app's auth dependency and rate-limit middleware (config `RATE_LIMIT_*`) to
  the agent router. Use a stricter limit for `/api/agent/chat` (LLM spend) than general
  endpoints.

**C8. Upload path sanitization** (`agent.py:113-152`)
- Sanitize `filename` with a `secure_filename`-style helper (strip path components,
  reject `..`).
- Validate that the `file_path` query param in `/api/agent/data` resolves inside
  `UPLOAD_DIR` (resolve + prefix check).

**C9. Provider config consolidation**
- Add `agent_default_provider` / `agent_default_model` to `Settings` (`config.py`) as
  the single source of truth.
- `ChatRequest` defaults and `SurveillanceAgent.__init__` defaults read from `Settings`.
- The existing `GET /api/agent/providers/status` response is extended to also return
  `default_provider` and `default_model` from `Settings`; the zustand store initializes
  its `provider`/`model` from that response instead of a hardcoded default. This removes
  all three hardcoded copies.

### Testing
- Backend:
  - Each typed tool returns expected JSON (mocked service functions).
  - Context injection appears in the system prompt.
  - `StreamingDSMLFilter` boundary cases.
  - `ERROR` event emitted on per-chunk exception.
  - Auth dependency rejects unauthenticated requests; rate limit throttles.
  - Path sanitization rejects traversal.
- Frontend:
  - `sendMessage` builds `context` from dashboard state.
  - `ERROR:` renders an inline error state.
  - `localStorage` round-trip survives a simulated refresh.
  - `prefillPrompt` opens the sidebar with the given text.

---

## Risks

- **Latest-available window UX:** users may expect "today". Mitigation: the date
  selector shows a "Data through: {max date}" badge so the recency is explicit.
- **Typed tools vs. raw SQL:** the agent may still prefer SQL. Mitigation: system prompt
  steers to typed tools; `query_db` remains as fallback with a row cap.
- **Rate limiting the agent:** could block legitimate heavy use. Mitigation: tune
  limits per-endpoint; surface 429 cleanly in the UI.

## Out of scope / follow-ups

- `TrendsReport` hardcoded mock (`ReportsView.tsx:618-669`).
- Server-side conversation store / multi-device sync.
- Replacing or adding LLM providers.
- Re-evaluating the custom newline protocol vs. real SSE — kept as-is.
