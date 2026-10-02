CHOLERA PAPER — GEE COVARIATES NOW COMPUTED (REAL, LIVE EARTH ENGINE RUN)
=========================================================================
Computed 2026-08-31 on EE project project-bf60cdc9-e913-4f05-942 (registered + API enabled).
This is the file that was MISSING from V7. NDWI/NDVI/precipitation are now real.

FILE: gee_pilot_covariates_2021.csv
-----------------------------------
Per-LGA environmental covariates for the four Cross River sentinel-pilot LGAs, 2021.

Sources (all live GEE):
  - NDWI: COPERNICUS/S2_SR_HARMONIZED, (B3-B8)/(B3+B8), 20m
  - NDVI: COPERNICUS/S2_SR_HARMONIZED, (B8-B4)/(B8+B4), 20m
  - Precipitation: NASA/GPM_L3/IMERG_V07 precipitationCal (mm), summed over window
  - Geometry: GRID3 Admin-2 boundaries (same as paper)

Windows:
  - wet_*  = 2021-06-01..2021-10-31 (rains / cholera season)
  - dry_*  = 2021-01-01..2021-03-31 (dry-season baseline, for anomaly)
  - *_anomaly = wet minus dry

Cloud handling: Yakurr & Biase used cloud<40% scene filter (3 clear scenes each).
Calabar Municipal & Bakassi (coastal, persistently cloudy) used cloud<80% +
per-pixel SCL cloud/shadow masking to recover 10 usable scenes each.

HEADLINE RESULTS (wet season 2021):
  LGA                NDWI_mean  NDVI_mean  Precip_total_mm  Precip_mm/day
  Yakurr             -0.262     0.332      1,088.9          7.16
  Biase              -0.288     0.359      1,174.2          7.73
  Calabar Municipal  -0.365     0.436      1,270.8          8.36
  Bakassi            -0.432     0.540      1,379.6          9.08

Precipitation anomaly (wet-dry) ranges +996mm (Yakurr) to +1,216mm (Bakassi):
a clean coastal-inland gradient and a large wet-season signal, as expected.

NOTE ON NDWI SIGN: mean NDWI is negative across all four (vegetated/land-dominated
LGAs). ndwi_max and water_pct capture the localized open-water/flood fraction; use
those, not the areal mean, as the flood-persistence proxy. This matches the paper's
intended use of NDWI>0.3 as a water mask.

This CSV is what upgrades V7 paragraphs 70 & 150 from "implemented but not
exercised" to "computed and reported."
