# Cholera Manuscript V7 Notes

Date: 2026-08-21  
Branch: `feat/publication-alignment`  
PR: https://github.com/salty-ai/flooding-cholera/pull/1

## Why V7
User feedback on V6 figures:
1. Diagrams and app screenshots were not clear enough
2. No image of the AI Surveillance Copilot
3. Alerts page screenshot had no alert rows

## What changed
### Screenshots (Playwright, 1920×1080 @ 3× = 5760×3240)
- Regenerated dashboard, map, facilities, reports, satellite, analytics
- **Alerts** re-seeded with 8 active multi-severity rows (Kano, Yakurr, Yenegoa, Lagos, Biase, Zuru, Maiduguri, Calabar notice) then recaptured
- **AI Surveillance Copilot** sidebar open on national dashboard (`app_surveillance_copilot.png` / `app_copilot_open.png`)
- **Agent Explorer** dedicated page (`app_agent_explorer.png`)
- Capture script: `docs/paper_figures/capture_publication_v7.py`
- Alert seed script: `docs/paper_figures/seed_paper_alerts.py`

### Diagrams / charts
- SVG diagrams re-rasterized at **4×** (`gen_diagrams.py`)
- Charts at **450 dpi** (`gen_charts.py`)
- Flat monochrome journal style retained

### Manuscript
- `docs/CHOLERA_PAPER_V7_Revised.docx` + `.pdf`
- Builder: `docs/paper_figures/build_cholera_paper_v7.py`
- 14 embedded figures
- Framing: **Cross River sentinel pilot first → national 774-LGA hub**; national epi from **NCDC SitRep compilations** (state-level). No fabricated national LGA panel. Title unchanged (National Framework and Cross River Sentinel Pilot).

### Figure map (V7)
1. Architecture diagram  
2. Data pipeline diagram  
3. Pilot flood exposure panels  
4. National dashboard  
5. National map  
6. Cross River pilot cases/deaths chart  
7. FMOH facilities browser  
8. National NCDC burden chart  
9. Exploratory lag signal  
10. Alerts with data  
11. AI Surveillance Copilot (open)  
12. Agent Explorer page  
13. Copilot schema benchmark  
14. Roadmap diagram  

## Honest limits retained
- Correlation = exploratory decision-support only  
- Risk = heuristic MCDA  
- Facilities count = inventory presence  
- Pilot ≠ national validation  
- Copilot benchmark failure mode (schema hallucination without tool grounding) retained  

## Not done / follow-ups
- Alembic migration for FMOH/NEMA model columns still outstanding  
- README still Cross-River-centric  
- Agent Explorer live generation can 422 if UI provider defaults to unavailable Deepseek; capture forced Vertex for copilot shots  
- Some Agent Explorer generated-dashboard captures remain lighter than ideal if live UI_SPEC stream fails; dedicated page + pilot aggregate still shown  
