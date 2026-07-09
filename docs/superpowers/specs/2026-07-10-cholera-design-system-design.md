# Cholera Surveillance — Design System & Dashboard Redesign

**Date:** 2026-07-10
**Status:** Draft (pending user review)
**Approach:** A — `design-md` source of truth + `frontend-design` showcase, built in Open Design and ported back to the React/Tailwind frontend.

## 1. Overview & Goals

The Cholera Environmental Surveillance System (React 18 + TS + Vite + Tailwind v3 + Recharts + Leaflet) has no formal design system. A small Tailwind palette exists, but components are full of hardcoded hex values (`#e6e8eb`, `#111518`), generic grays (`text-gray-500`), and **inconsistent risk colors** — the map legend uses `bg-red-500/yellow-400/green-500` while the token scale defines `#ef4444/#eab308/#22c55e`.

This spec defines a clinical, authoritative design system (in the vein of WHO / Our World in Data dashboards) and uses it to redesign the main dashboard screen as the showcase, then ports the tokens and components back into the real frontend.

**Goals**
- Establish a single source of truth (`DESIGN.md` + token definitions) for color, typography, spacing, elevation, and component rules.
- Preserve the meaningful risk semantics (`low / medium / high / unknown`) while improving consistency and accessibility.
- Redesign the dashboard + app shell into one cohesive, polished, trustworthy screen.
- Port tokens and primitives into the actual `frontend/` codebase, replacing hardcoded hex.

**Non-goals (out of scope)**
- Redesigning other screens (LGA detail, Cases, Upload, Compare, Analytics, Auth, Agent). The design system applies app-wide via tokens, but only the dashboard is redesigned.
- Dark mode.
- Backend changes.
- Replacing Recharts or Leaflet.
- A complete component library for every UI surface — only the primitives the dashboard needs, plus app-wide tokens.

## 2. Scope

**In scope (redesign showcase):** app shell (header + sidebar), `DateRangeSelector`, `DashboardKpiRow` (5 KPIs), `ChoroplethMap` panel + legend, `ActiveAlertsRail`, `FloodEventsRail`, `CorrelationChart`, `RiskBreakdownChart`.

**Dashboard data shape (preserved from real app):** `DashboardSummary` → `total_cases`, `active_alerts_count`, `alert_level` (green/yellow/red → Low/Medium/High), `lgas_high_risk`, `avg_rainfall_7day`, `flood_events_count`, `max_data_date`. The Open Design showcase uses mock data matching this shape.

## 3. Design System Foundation (tokens)

A token block that maps 1:1 to `tailwind.config.js`. Clinical & authoritative: light, neutral, restrained color; strong type hierarchy; subtle borders over shadows.

### Color
- **Surfaces:** `canvas #f6f7f9` (app bg), `surface #ffffff` (cards), `surface-muted #f0f2f5` (insets / table stripes).
- **Ink (text scale):** `ink-900 #0f1419` (primary), `ink-700 #3b4250`, `ink-500 #6b7280` (secondary), `ink-400 #9aa1ac` (labels/tertiary).
- **Border:** `border-default #e6e8eb`, `border-strong #d0d4da`.
- **Primary (trust accent):** keep blue, expand to a scale — `primary-600 #1392ec` default, with `primary-50…900` steps for hover/active/tints.
- **Risk (semantic, preserved):** `risk-low #16a34a`, `risk-medium #d97706`, `risk-high #dc2626`, `risk-unknown #6b7280` — each with a matching `-tint` (≈8% bg) and `-fg` (accessible text-on-tint). Slightly deepened from current for contrast/authority; semantics unchanged.
- **Data-series accents:** `alert #ea580c` (alerts), `flood #0284c7` (flood/water), `env #0bda5b` (environmental), `rain #6366f1` (rainfall) — used in charts, rails, map.
- **Chart categorical palette:** a 6-color accessible set for multi-series charts, distinct from risk.

### Typography
- **Inter** for all UI; **JetBrains Mono** reserved for numerics (KPI values, stats, timestamps) with `tabular-nums` — gives data-dashboard authority and aligned columns.
- Scale: `xs 12 / sm 13 / base 14 / lg 16 / xl 20 / 2xl 24 / 3xl 30` px. Headings 600/700; stat values 500.

### Spacing / radius / elevation
- 4px base grid (keep Tailwind default). Standards: card padding `p-5`, section gap `gap-6`.
- Radius: `card 12px` (`rounded-xl`), `control 8px` (`rounded-lg`), `pill 999px`.
- Elevation: prefer 1px border; shadows only for floating elements — `shadow-card` (subtle), `shadow-popover` (menus/tooltip).

## 4. Component Library

### Primitives (`frontend/src/components/ui/`)
- **`Button`** — variants: `primary`, `secondary`, `ghost`, `danger`; sizes `sm`, `md`.
- **`Card`** — `surface` container with optional header/footer, `border-default` + `shadow-card`.
- **`StatTile`** — KPI tile: title, value (mono, `tabular-nums`), subtitle, optional status accent (e.g. risk color) and optional delta.
- **`RiskBadge`** — risk-level chip using `risk-*-tint` bg + `risk-*-fg` text; accepts `low|medium|high|unknown`.
- **`Panel`** — titled section container (map panel, chart panels) with a header slot and optional actions.
- **`SegmentedControl`** — used for date presets and similar mutually-exclusive toggles.
- **`Skeleton`** / **`EmptyState`** — loading and empty rail states.
- **`Spinner`** — loading indicator (reuse current spinner, themed via `primary`).

### Composites (dashboard-specific, refactored to use primitives + tokens)
- `DateRangeSelector` — `SegmentedControl` presets + custom range control.
- `KpiRow` — grid of `StatTile`s; the Alert Level tile carries the `risk-*` accent.
- Map panel — `Panel` + `ChoroplethMap` + a **unified risk legend** built from `risk-*` tokens (fixes the current color mismatch).
- `ActiveAlertsRail` / `FloodEventsRail` — list items with severity accents (`alert` / `flood`).
- `CorrelationChart` / `RiskBreakdownChart` — Recharts themed with the chart palette + token colors.

## 5. Dashboard Redesign

Light, airy, trustworthy. Strong typographic hierarchy; color used sparingly and only where semantically meaningful (risk, alert, flood).

**App shell**
- Slim header: product title ("Cholera Environmental Surveillance — Cross River State"), current window indicator, refresh control, user. `surface` bg, `border-default` bottom.
- Narrow sidebar: nav icons + labels, active state in `primary`.

**Content (vertical stack, `gap-6`)**
1. **Date-range bar** — full-width `surface-muted` band holding `DateRangeSelector`.
2. **KPI row** — 5 `StatTile`s (Confirmed cases, Active alerts, Alert level, Rainfall 7d, Flood events). Mono numerics; Alert Level tile uses the risk accent.
3. **Main grid** (`xl:grid-cols-3`) — 2/3 `Panel` "Geospatial Risk Map" with unified risk legend + `ChoroplethMap`; 1/3 stacked `ActiveAlertsRail` + `FloodEventsRail`.
4. **Bottom grid** (`lg:grid-cols-2`) — `CorrelationChart` + `RiskBreakdownChart`, each in a `Panel`.

Density: `p-5` cards, `gap-6` sections, 12px radius, 1px borders, shadows only on popovers.

## 6. Open Design Deliverables

An Open Design project ("Cholera Surveillance Design System") containing:
- **`DESIGN.md`** — source of truth: tokens, type, spacing, elevation, component rules, chart palette, risk semantics, do/don'ts.
- **`tokens`** — token definitions (JSON/TS) mapping 1:1 to the Tailwind config.
- **`dashboard.tsx`** — the redesigned dashboard as React/TSX + Tailwind, using token classes, with mock data matching `DashboardSummary`.
- **Showcase pages** — a primitives showcase (buttons, cards, stat tiles, badges, panels) and the dashboard page, reachable from an entry `index.html`.

**Build mechanism (recommended):** `create_project`, then `start_run` with the `frontend-design` skill and a detailed brief encoding the clinical/authoritative direction, risk semantics, and real data shape; refine the output directly via `write_file` to enforce token fidelity.

## 7. React Port-back Plan

1. Extend `tailwind.config.js` with the full token scale (colors incl. `risk.*`/data-series, fonts, radius, shadows); replace the loose palette.
2. Add `frontend/src/components/ui/` primitives.
3. Refactor dashboard components (`DashboardView`, `DashboardKpiRow`, `DateRangeSelector`, `ActiveAlertsRail`, `FloodEventsRail`, `CorrelationChart`, `RiskBreakdownChart`, map panel) to use primitives + tokens; replace all hardcoded hex; unify the map legend to `risk-*`.
4. Theme Recharts (chart palette, axis/grid colors) and Leaflet (risk fill colors) via tokens.
5. Run the app; verify no regressions.

## 8. Verification

- **Open Design preview** renders the dashboard + primitives showcase correctly.
- **Token mapping:** every token in `DESIGN.md` has a Tailwind counterpart in `tailwind.config.js`.
- **No hardcoded hex:** `grep` of refactored dashboard components for `#[0-9a-f]{3,6}` / `text-gray-` / `bg-gray-` returns nothing (token classes only).
- **Risk color unity:** map legend, `RiskBadge`, and `StatTile` alert-level accent all derive from `risk-*` tokens.
- **Accessibility:** risk `*-fg` on `*-tint` pairs meet WCAG AA contrast (≥4.5:1 for text).
- **Runtime:** app boots, dashboard matches the Open Design showcase, charts and map render with real data.

## 9. Risks & Notes
- Recharts/Leaflet theming is done by passing token color values into chart/layer config — straightforward but must stay in sync with the token file.
- The existing `alert_level` uses `green/yellow/red` keys mapped to Low/Medium/High; the redesign keeps this mapping and renders via `risk-*` tokens.
- Port-back touches recently-rebuilt dashboard components (Layout A); changes are visual/token-only and must not alter data flow.
