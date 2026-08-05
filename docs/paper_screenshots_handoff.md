# Handoff: Flooding & Cholera Surveillance System Screenshots & Academic Paper Write-up

This handoff document details the task of capturing 4 high-quality screenshots and generating academic paper figure descriptions for the **Flooding & Cholera Surveillance & Early Warning System** (`flooding-cholera`).

## Context & Objectives
- **Project**: Flooding & Cholera Surveillance & Early Warning System (FastAPI + PostGIS + GeoJSON + React/Vite + Leaflet/Recharts).
- **Goal**: Generate 4 high-resolution (1920x1080 @ 2x DPI Retina scale) screenshots representing core user flows and capabilities for a research paper publication:
  1. `risk_dashboard.png`: Main Risk Dashboard & Disease Surveillance Overview (LGA map view, risk cards, flood overlays).
  2. `lga_analytics.png`: LGA Search & Spatial Analytics View (LGA search selection, epidemiological risk metrics, GEE satellite index correlation).
  3. `correlation_analytics.png`: Multi-Source Data Aggregation & Early Warning Alert (Precipitation vs. Cholera outbreak charts, water quality indicators).
  4. `agent_export_panel.png`: AI Agent Assistant & Report Export Panel (Agent Sidebar, risk recommendations, PDF/CSV export control).
- **Target Storage Location**: 
  - Save PNG screenshots and `academic_paper_figure_descriptions.md` to: `/Users/yakky/Dev/flooding-cholera/docs/paper/`

## Local Server Requirements
- **Frontend Server**: `http://localhost:5173` (run via `npm run dev` in `/Users/yakky/Dev/flooding-cholera/frontend`)
- **Backend API**: `http://localhost:8000` (run via `uvicorn app.main:app --reload` in `/Users/yakky/Dev/flooding-cholera/backend`)

## Execution Steps for Next Agent

1. **Verify Environment & Servers**:
   - Ensure `http://localhost:5173` (or active frontend dev port) and `http://localhost:8000` are running.
   - Use Playwright with Chromium (`viewport: {width: 1920, height: 1080}`, `device_scale_factor: 2`).

2. **Capture Screenshot 1 (`risk_dashboard.png`)**:
   - Navigate to `http://localhost:5173`.
   - Wait 3 seconds for Leaflet map tiles, LGA polygons, and risk metrics cards to load.
   - Capture screenshot and save to `/Users/yakky/Dev/flooding-cholera/docs/paper/risk_dashboard.png`.

3. **Capture Screenshot 2 (`lga_analytics.png`)**:
   - Focus the LGA search bar (`LGASearchBar`).
   - Search for an LGA (e.g. `"Calabar South"` or `"Kano Municipal"`).
   - Click the LGA search result to zoom into the polygon and trigger the detailed analytics sidebar/modal.
   - Wait 3 seconds for map zoom and risk score breakdown.
   - Capture screenshot and save to `/Users/yakky/Dev/flooding-cholera/docs/paper/lga_analytics.png`.

4. **Capture Screenshot 3 (`correlation_analytics.png`)**:
   - Navigate/click to the Analytics tab or Correlation Chart view.
   - Wait 3 seconds for Recharts multi-source visualization (rainfall vs cholera cases vs NDWI index).
   - Capture screenshot and save to `/Users/yakky/Dev/flooding-cholera/docs/paper/correlation_analytics.png`.

5. **Capture Screenshot 4 (`agent_export_panel.png`)**:
   - Open the AI Agent Assistant sidebar (`AgentSidebar`) or click the Export button (`ExportButton`).
   - Wait 2 seconds for agent recommendations and export options.
   - Capture screenshot and save to `/Users/yakky/Dev/flooding-cholera/docs/paper/agent_export_panel.png`.

6. **Generate Academic Documentation (`academic_paper_figure_descriptions.md`)**:
   - Write publication-ready figure captions and academic text (Sections 4.1–4.4) covering:
     - Spatial epidemiology basemap & multi-risk overlay architecture.
     - Satellite remote sensing integration (GEE, NDWI, precipitation correlation).
     - Automated LGA risk classification & postGIS spatial joins.
     - Agentic LLM decision support & surveillance export engine.
   - Save to `/Users/yakky/Dev/flooding-cholera/docs/paper/academic_paper_figure_descriptions.md`.

## Recommended Skills for Next Agent
- `chrome-devtools`: To execute browser actions and inspect elements.
- `modern-web-guidance`: Best practices for frontend layout and accessibility.
- `ml-best-practices`: Guidance on analytics and risk scoring visualizations.
