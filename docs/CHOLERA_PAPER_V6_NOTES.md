# Cholera Manuscript V6 Notes

Date: 2026-08-19  
Branch: `feat/publication-alignment`

## Artifacts
- `docs/CHOLERA_PAPER_V6_Revised.docx` / `.pdf` — revised manuscript after evidence audit
- `docs/paper_figures/build_cholera_paper_v6.py` — builder used for V6
- `docs/CHOLERA_EVIDENCE_AUDIT_V4.md` — evidence audit that drove claim downgrades
- `docs/CHOLERA_PAPER_V5_RealData.docx` / `.pdf` — prior real-data baseline (kept)
- `docs/publication_evidence_report.json` — inventory/claim-status snapshot

## Framing retained from V5
- Hybrid national (NCDC state-level official figures) + Cross River sentinel pilot
- Correlation = exploratory decision-support signal (not validated forecast)
- Risk weights = fixed heuristic MCDA (not PCA-calibrated)
- 774-LGA national architecture is design scope; pilot does not validate the nation

## Code alignment on this branch (uncommitted work now included)
- FMOH facilities model/API + Facilities UI (paginated, filtered)
- NEMA flood impact fields on flood events + summary endpoint
- Mobile/responsive layout and chart wording aligned to exploratory language
- Old `docs/paper/*.png` screenshots removed in favour of `docs/paper_figures/`

## Known follow-ups (do not block laptop continue)
- Alembic migration still missing for new `HealthFacility` / `FloodEvent` columns
- `backend/data/cholera_real/nigeria_cholera_2020_2025.csv` remains a generated gapless panel — do not cite as NCDC line-list
- Full FMOH JSON (~25MB) intentionally not committed; CSV retained under `backend/data/external_real/`
- Groundsource parquet is gitignored (local-only)
