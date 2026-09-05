"""TASK A (final v2) — paired flood-exposure / real-case series, with trailing
exposure windows suitable for lag correlation.

v2 changes vs v1: adds per-observation trailing-window exposure metrics
(4-week, 8-week, 12-week, and calendar-month trailing windows ending at the
observation's epi week), so the paired series supports lag analysis at
multiple offsets without further computation. Core verification gate
(table5 reproduction) unchanged and re-run.
"""
import calendar
import json
from datetime import date, timedelta

import duckdb
import pandas as pd
from shapely import wkb as shp_wkb
from shapely.geometry import shape

OUT = "/root/cholera_hod_tasks"
DATASET = "/root/flooding-cholera-gee/backend/data/cholera_real/final_state_cholera_dataset_v2.csv"
TABLE5 = "/root/cholera_paper_data/table5_flood_exposure.csv"

con = duckdb.connect()
con.execute("INSTALL spatial; LOAD spatial;")
con.execute("SET threads TO 4; SET memory_limit='3.5GB'; SET max_temp_directory_size='40GB'")

# ── 1. GRID3 pilot units ──────────────────────────────────────────────────
gj = json.load(open("/root/flooding-cholera-gee/backend/data/boundaries/nigeria_lgas_774.geojson"))
GRID3 = {
    "Yakurr": ["Yakurr"],
    "Biase": ["Biase"],
    "Calabar Municipal": ["Calabar-Municipal"],
    "Bakassi": ["Bakassi"],
}
con.execute("CREATE TABLE grid3_pilot (pilot_lga VARCHAR, adm2 VARCHAR, area_sqkm DOUBLE, geom_hex TEXT)")
for pilot, units in GRID3.items():
    for f in gj["features"]:
        p = f["properties"]
        if p.get("adm1_name") == "Cross River" and p.get("adm2_name") in units:
            con.execute(
                "INSERT INTO grid3_pilot VALUES (?,?,?,?)",
                [pilot, p["adm2_name"], p["area_sqkm"], shp_wkb.dumps(shape(f["geometry"])).hex()],
            )

# ── 2. Archive join (bbox-overlap prefilter + exact intersects) ────────────
print("[1/4] Joining archive to pilot LGAs (GRID3 Admin-2) ...")
con.execute("""
CREATE OR REPLACE TABLE event_lga_join AS
SELECT f.uuid, l.pilot_lga,
       strptime(f.start_date, '%Y-%m-%d') AS start_d,
       strptime(f.end_date, '%Y-%m-%d') AS end_d,
       f.area_km2 AS event_area_km2,
       st_intersection(st_geomfromwkb(f.geometry), st_geomfromwkb(unhex(l.geom_hex))) AS igeom,
       st_area_spheroid(st_intersection(st_geomfromwkb(f.geometry), st_geomfromwkb(unhex(l.geom_hex)))) / 1e6 AS intersect_km2
FROM read_parquet('groundsource_plain.parquet') AS f
CROSS JOIN grid3_pilot AS l
WHERE st_xmin(st_geomfromwkb(f.geometry)) <= 9.7
  AND st_xmax(st_geomfromwkb(f.geometry)) >= 7.8
  AND st_ymin(st_geomfromwkb(f.geometry)) <= 7.1
  AND st_ymax(st_geomfromwkb(f.geometry)) >= 4.2
  AND st_intersects(st_geomfromwkb(f.geometry), st_geomfromwkb(unhex(l.geom_hex)))
""")
n_pairs = con.execute("SELECT count(*) FROM event_lga_join").fetchone()[0]
print(f"      (event, LGA) pairs: {n_pairs}")

# ── 3. Verification gate vs table5 ─────────────────────────────────────────
print("\n[2/4] Verification gate vs table5_flood_exposure.csv ...")
ver = con.execute("""
SELECT pilot_lga,
       count(*) AS events_2000_2026,
       count(DISTINCT year(start_d)) AS years_with_flooding,
       round(st_area_spheroid(st_union_agg(igeom)) / 1e6, 2) AS union_area_km2
FROM event_lga_join GROUP BY 1 ORDER BY 1
""").df()
print(ver.to_string(index=False))
t5 = pd.read_csv(TABLE5)
t5 = t5[t5["Sentinel LGA"] != "TOTAL"].set_index("Sentinel LGA")
ok_events = all(
    int(ver.loc[ver.pilot_lga == lga, "events_2000_2026"].iloc[0]) == int(t5.loc[lga, "Flood events 2000–2026"])
    for lga in GRID3
)
ok_years = all(
    int(ver.loc[ver.pilot_lga == lga, "years_with_flooding"].iloc[0]) == int(t5.loc[lga, "Years with flooding"])
    for lga in GRID3
)
assert ok_events and ok_years, "verification gate FAILED — do not ship"
print(f"      event counts match table5: {ok_events} | years match: {ok_years}")

# ── 4. Paired series with trailing windows ────────────────────────────────
print("\n[3/4] Building paired series with trailing exposure windows ...")
df = pd.read_csv(DATASET)
cr = df[df["State"].str.strip().str.lower() == "cross river"].copy()
assert len(cr) == 46
cr["month_num"] = cr["Month"].map(lambda m: list(calendar.month_name).index(m))
cr = cr.sort_values(["Year", "Epi_Week"]).reset_index(drop=True)
cr["prev_epi_week"] = cr.groupby("Year")["Epi_Week"].shift(1)
cr["state_cases_new_since_prev_obs"] = cr.groupby("Year")["Suspected_Cases"].diff()
cr["obs_gap_weeks"] = cr["Epi_Week"] - cr["prev_epi_week"]

LGA_CASES_2021 = {"Yakurr": 53, "Biase": 10, "Calabar Municipal": 6, "Bakassi": 5}

def window_metrics(lga: str, w_start: date, w_end: date):
    """Events overlapping [w_start, w_end]: count + union clipped km2."""
    r = con.execute("""
        SELECT count(*), round(coalesce(st_area_spheroid(st_union_agg(igeom))/1e6, 0), 4)
        FROM event_lga_join
        WHERE pilot_lga = ? AND start_d <= ? AND end_d >= ?
    """, [lga, w_end, w_start]).fetchone()
    return int(r[0]), float(r[1])

rows = []
for _, obs in cr.iterrows():
    ws = date.fromisocalendar(int(obs.Year), int(obs.Epi_Week), 1)
    we = ws + timedelta(days=6)
    month_end = (date(int(obs.Year), int(obs.month_num), 1)
                 + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    for lga in sorted(GRID3):
        n0, a0 = window_metrics(lga, ws, we)                       # epi week itself
        n4, a4 = window_metrics(lga, we - timedelta(days=27), we)  # trailing 4 weeks
        n8, a8 = window_metrics(lga, we - timedelta(days=55), we)  # trailing 8 weeks
        n12, a12 = window_metrics(lga, we - timedelta(days=83), we)  # trailing 12 weeks
        nm, am = window_metrics(lga, date(int(obs.Year), int(obs.month_num), 1), month_end)  # obs month
        c = con.execute("""
            SELECT count(*), round(coalesce(st_area_spheroid(st_union_agg(igeom))/1e6, 0), 4)
            FROM event_lga_join WHERE pilot_lga = ? AND start_d <= ?
        """, [lga, we]).fetchone()
        rows.append({
            "state": "Cross River",
            "year": int(obs.Year),
            "epi_week": int(obs.Epi_Week),
            "week_start_date": ws.isoformat(),
            "week_end_date": we.isoformat(),
            "month": obs.Month,
            "lga": lga,
            # lag-0 exposure metrics
            "flood_events_in_epi_week": n0,
            "flood_union_km2_in_epi_week": a0,
            "flood_events_trailing_4wk": n4,
            "flood_union_km2_trailing_4wk": a4,
            "flood_events_trailing_8wk": n8,
            "flood_union_km2_trailing_8wk": a8,
            "flood_events_trailing_12wk": n12,
            "flood_union_km2_trailing_12wk": a12,
            "flood_events_in_month": nm,
            "flood_union_km2_in_month": am,
            "flood_events_cum_to_date": int(c[0]),
            "flood_union_km2_cum_to_date": float(c[1]),
            # real case data (verified NCDC SitRep series)
            "state_suspected_cases_cum": float(obs.Suspected_Cases),
            "state_deaths_cum": float(obs.Deaths),
            "state_cfr_pct": float(obs.CFR),
            "state_cases_new_since_prev_obs": obs.state_cases_new_since_prev_obs,
            "prev_epi_week": obs.prev_epi_week,
            "obs_gap_weeks": obs.obs_gap_weeks,
            # sentinel-tier per-LGA cases (2021 line-list only)
            "lga_cases_2021_pilot": LGA_CASES_2021[lga],
            # provenance
            "dataset_layout": obs.Layout,
            "dataset_confidence": obs.Confidence,
            "dataset_extraction_method": obs.Extraction_Method,
            "dataset_source_url": obs.Source_URL,
            "monotonic_ok": obs.monotonic_ok,
        })
paired = pd.DataFrame(rows).sort_values(["year", "epi_week", "lga"]).reset_index(drop=True)
assert len(paired) == 184, len(paired)
paired.to_csv(f"{OUT}/paired_series_crossriver_2021_2024.csv", index=False)
print(f"      wrote paired_series_crossriver_2021_2024.csv ({len(paired)} rows, {len(paired.columns)} cols)")

# quick coverage stats for the report
for col in ["flood_events_in_epi_week", "flood_events_trailing_4wk", "flood_events_trailing_8wk",
            "flood_events_trailing_12wk", "flood_events_in_month"]:
    print(f"      rows with {col} > 0: {(paired[col] > 0).sum()}/184, total events counted: {paired[col].sum()}")

# ── 5. Raw events table ────────────────────────────────────────────────────
ev = con.execute("""
    SELECT uuid, pilot_lga AS lga, CAST(start_d AS DATE) AS start_date,
           CAST(end_d AS DATE) AS end_date, event_area_km2,
           round(intersect_km2, 6) AS intersect_area_km2
    FROM event_lga_join ORDER BY pilot_lga, start_d
""").df()
ev.to_csv(f"{OUT}/flood_events_pilot_lgas_2000_2026.csv", index=False)
print(f"      wrote flood_events_pilot_lgas_2000_2026.csv ({len(ev)} rows)")

# ── 6. Verification report ────────────────────────────────────────────────
print("\n[4/4] Writing verification report ...")
rep = []
rep.append("TASK A VERIFICATION REPORT — flood-exposure / real-case paired series (v2)")
rep.append("Generated: " + pd.Timestamp.now("UTC").isoformat())
rep.append("")
rep.append("WHAT THE HOD ASKED FOR")
rep.append("  Re-run the flood-exposure correlation inputs against the REAL multi-year")
rep.append("  Cross River case data (final_state_cholera_dataset_v2.csv), for the 4 pilot")
rep.append("  LGAs, across every date Cross River appears (2021-2024), and deliver the")
rep.append("  paired series (date, flood exposure metric, real case count) as raw CSV.")
rep.append("")
rep.append("INPUTS (all verified artifacts)")
rep.append("  Cases: final_state_cholera_dataset_v2.csv — 46 Cross River observations,")
rep.append("    2021 wk24-47, 2022 wk30-52, 2023 wk9-52, 2024 wk8-39. STATE-level")
rep.append("    CUMULATIVE suspected cases/deaths from NCDC Cholera SitReps (84/93 parsed,")
rep.append("    arithmetic CFR integrity gate, source PDF URL per row, monotonic_ok flags).")
rep.append("    NO 2025 Cross River rows exist in the verified dataset (NCDC sitreps after")
rep.append("    2024 wk39 stopped reporting Cross River in the parsed set).")
rep.append("  Flood: Groundsource 2026 archive (Zenodo 18647054), 2,646,302 dated polygons")
rep.append("    2000-2026 (WKB/WGS84). Re-encoded to plain parquet because DuckDB 1.5.5's")
rep.append("    GeoParquet reader rejects the file's geo metadata (geometry preserved byte-exact).")
rep.append("  Boundaries: GRID3 Admin-2 (nigeria_lgas_774.geojson) — the same source as the")
rep.append("    paper's Table 4/5. NOTE: backend/data/cross_river_lgas.geojson is a DIFFERENT")
rep.append("    boundary file; it yields 248 join pairs and WRONG Biase counts vs table5.")
rep.append("    GRID3 is the table5-consistent source and is used here.")
rep.append("")
rep.append("METHOD")
rep.append("  Spatial join: exact ST_Intersects(flood polygon, LGA polygon) after bbox")
rep.append("  overlap prefilter. Areas: geodesic spheroid km2 of the clipped intersection.")
rep.append("  Reporting period: ISO epi week (Mon-Sun) of each SitRep observation.")
rep.append("  Exposure metrics per (observation x LGA):")
rep.append("    - events + union km2 overlapping the epi week itself (lag-0 week)")
rep.append("    - trailing 4/8/12-week windows ending at the epi week (lag scan)")
rep.append("    - events + union km2 in the observation's calendar month")
rep.append("    - cumulative events + union km2 from archive start to the epi week")
rep.append("")
rep.append("VERIFICATION GATE vs table5_flood_exposure.csv (all-time 2000-2026)")
rep.append(ver.to_string(index=False))
rep.append(f"\n  event counts match table5: {ok_events}")
rep.append(f"  years-with-flooding match:  {ok_years}")
rep.append(f"  (event, LGA) pairs: {n_pairs}  <- the paper's '191 distinct flood events over the pilot footprint'")
for lga in GRID3:
    mine = float(ver.loc[ver.pilot_lga == lga, "union_area_km2"].iloc[0])
    ref = float(str(t5.loc[lga, "Union flooded area (km²)"]).replace(",", ""))
    rep.append(f"  union area {lga}: computed {mine} vs table5 {ref} (diff {abs(mine-ref)/ref*100:.2f}%)")
rep.append("")
rep.append("KEY SUBSTANTIVE FINDINGS OF THE RE-RUN (stated plainly, for the paper's honesty)")
rep.append("  1. ZERO flood events were recorded by the archive in the 4 pilot LGAs during")
rep.append("     2021 — the year of the sentinel outbreak. The paper's Table 4/5 'pre-outbreak")
rep.append("     events 2011-2020' framing remains the only exposure context for 2021.")
rep.append("  2. Pilot-LGA flood events during the verified case window are sparse and real:")
rep.append("     2020: 3 events (pre-series), 2022: 14, 2023: 2, 2024: 4. Biase and Calabar")
rep.append("     Municipal carry nearly all of the exposure; Yakurr has 1 event (2024-12);")
rep.append("     Bakassi has none after 2000s records.")
rep.append("  3. Case counts are STATE-level cumulative; per-LGA cases exist only for the")
rep.append("     2021 sentinel line-list (column provided). Any correlation therefore pairs")
rep.append("     state-level case increments with LGA-level exposure — a limitation to")
rep.append("     disclose, consistent with the paper's two-tier evidence discipline.")
rep.append("  4. The trailing 4/8/12-week windows exist so lag correlation can be run at")
rep.append("     several offsets; no statistics were computed here (HOD's lane).")
rep.append("")
rep.append("OUTPUTS")
rep.append("  paired_series_crossriver_2021_2024.csv — 184 rows (46 obs x 4 LGAs), 31 cols:")
rep.append("    keys: year, epi_week, week_start/end, month, lga")
rep.append("    exposure: 12 flood metrics (per-window event counts + union km2, cumulative)")
rep.append("    cases: state cum suspected/deaths/CFR, new-since-prev-obs, gap weeks,")
rep.append("            2021 sentinel per-LGA cases")
rep.append("    provenance: layout, confidence, extraction method, source URL, monotonic_ok")
rep.append("  flood_events_pilot_lgas_2000_2026.csv — 191 (event x LGA) rows: uuid, dates,")
rep.append("    archive area, clipped intersection km2. Full re-derivation source.")
rep.append("  a_build_paired_series_v2.py — this script (exact reproduction, deterministic).")
rep.append("")
rep.append("REPRODUCTION")
rep.append("  python3 a_build_paired_series_v2.py   (needs: duckdb+spatial, shapely, pandas;")
rep.append("  input parquet at /root/cholera_hod_tasks/groundsource_plain.parquet)")
with open(f"{OUT}/task_a_verification_report.txt", "w") as f:
    f.write("\n".join(rep))
print("      wrote task_a_verification_report.txt")
print("\nDONE.")
