# Changelog — final_state_cholera_dataset_v2.csv

Built from `final_state_cholera_dataset.csv` (1,211 rows) + `needs_manual_review.csv` (232 rows).

## Changes
1. **Recovered 22 rows** from the manual-review "not-Layout-A / bare-CFR" bucket.
   These were held back only because the CFR carried no "%" sign; each was re-admitted
   ONLY after its first three numeric tokens reconcile as cases/deaths/CFR to within 0.15pp.
   Tagged `Confidence = reassembled`. All are 2021 wk1 / wk24 — the only pre-week-25 2021 data.
   (1 row(s) in that bucket genuinely rejected: empty/`- -`.)

2. **Added `monotonic_ok` column.** `False` on 80 rows where a within-(State,Year)
   cumulative series decreases in cases or deaths — impossible for a true cumulative total,
   so these are extraction artifacts (OCR column-scramble / digit noise) to be excluded
   from within-year trend analysis. Year-end (max-week) snapshots are unaffected.

## Result
- **Total rows: 1233** (1211 original + 22 recovered).
- **Analysis-safe rows (`monotonic_ok = True`): 1153**.
- Quarantined (`monotonic_ok = False`): 80.

## How to use
- Cross-sectional / correlation work: `df[df.monotonic_ok]`, each state at its max Epi_Week.
- Never sum rows across weeks within a state-year (cumulative — double counts).
- 2021 national year-end total: cite primary source (111,062 / 3,604), not summed rows.
