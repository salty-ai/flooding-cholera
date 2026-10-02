# Cholera Manuscript — Real-Data Rewrite Change Log (V5)

Date: 2026-08-18
Branch: feat/publication-alignment
Base document: `CHOLERA PAPER_Finalization.docx` (Head of Division original), NOT the trimmed V4.

## Why this rewrite happened

A forensic comparison found that the interim "V4" publication-ready docx had **both**
stripped the HoD original's scholarship **and** inflated its claims:

| Element | HoD Original | V4 (rejected) | This V5 (real data) |
|---|---|---|---|
| Pilot figures | 148 / 2 / 18 LGAs | 74 / 0 deaths | **74 / 4 / 4 LGAs** (from real line-list) |
| Correlation | "signal, not causation" | r=0.68–0.82, p<0.001 (fabricated) | exploratory signal, no r/p claimed |
| Risk weights | literature-informed MCDA | "PCA-calibrated" (false) | fixed heuristic MCDA (honest) |
| References | ~59–67 | 8 | 59 preserved |
| National panel | 55,584 obs (method described) | 55,584 (provenance dropped) | real NCDC state-level series |

## Root-cause data finding

- `backend/data/cholera_real/nigeria_cholera_2020_2025.csv` (55,585 rows) is a **generated**
  gapless 766×72 panel with non-NCDC labels ("Zero Reporting Baseline" etc.). No scraper
  exists in the repo (no pdfplumber/BeautifulSoup/NCDC download code). It violates the
  no-synthetic-data rule and is NOT cited as real in V5.
- The Cross River line-list (`Copy of Cholera Data for CRS 2021.xlsx`) IS real:
  74 culture-referenced cases, 4 deaths (CFR 5.4%), 4 LGAs (Yakurr 53, Biase 10,
  Calabar Municipal 6, Bakassi 5), epi weeks 6–46.

## Real data compiled (new artifacts)

- `backend/data/cholera_real/ncdc_national_annual_2021_2025.csv` — official NCDC annual
  burden with per-row source citations (2021: 111,062 cases / 3,604 deaths, verified against
  NCDC SitRep Epi Wk 52 2021).
- `backend/data/cholera_real/crossriver_2021_pilot_linelist_agg.csv` — pilot aggregate
  derived directly from the real line-list.

## Manuscript (V5) framing = hybrid (2)+(3)

- (2) Real NCDC national figures at STATE level (their true resolution); 774-LGA framed as
  design objective, realized only where line-list data exist.
- (3) Platform/methods honesty: heuristic MCDA (not PCA); decision-support signal (not
  forecast); 46,146 "source records" (not "validated"); NCDC/SORMAS live sync + multi-LLM
  = roadmap, not evidenced production.

## Open item for Yaks
- Pilot numbers default to the real 74/4/4. If a fuller Cross River export (the HoD's
  148/18-LGA source) exists, send it and the pilot table swaps trivially.

## Outputs
- `/root/CHOLERA_PAPER_V5_RealData.docx` + `.pdf` (16 pages, 59 refs)
- Builder: `/root/build_cholera_paper.py`
