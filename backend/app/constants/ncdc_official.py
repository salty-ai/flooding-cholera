"""Official NCDC year-end national cholera totals (primary source figures).

These are the headline national numbers as published by NCDC in its year-end
Cholera Situation Report. They are NOT derived from
`final_state_cholera_dataset_v2.csv` and must never be conflated with the
dataset-derived sum of per-state year-end snapshots: our extraction covers
84 of 93 published situation reports, and the last report we could parse for a
given year is often earlier than epi-week 52, so the dataset sum is a lower
bound on the official total.

Add a year here ONLY with a verifiable citation to the primary source. A year
with no entry is reported by the API as `official_cases: null`, which the UI
renders as "not stated" rather than zero.
"""
from typing import Any, Dict, Optional

#: Landing page for the NCDC cholera situation-report archive.
NCDC_SITREP_ARCHIVE_URL = "https://ncdc.gov.ng/diseases/sitreps"

#: One-line provenance statement for the verified national (state) tier.
NATIONAL_TIER_EVIDENCE_LABEL = (
    "Verified state-level NCDC situation-report extraction (84/93 reports, "
    "2021-2025). Cumulative year-to-date snapshots - not LGA-resolved, not "
    "summed across weeks."
)

#: year -> official NCDC year-end figures.
OFFICIAL_YEAR_END: Dict[int, Dict[str, Any]] = {
    2021: {
        "cases": 111062,
        "deaths": 3604,
        "epi_week": 52,
        "citation": "NCDC Cholera Situation Report, epi-week 52, 2021",
        "source_url": NCDC_SITREP_ARCHIVE_URL,
    },
}


def official_year_end(year: int) -> Optional[Dict[str, Any]]:
    """Official NCDC year-end figures for `year`, or None if not published here.

    The returned dict carries a derived `cfr` (percent, 2dp) so the UI never has
    to compute it from two separately-sourced numbers.
    """
    entry = OFFICIAL_YEAR_END.get(year)
    if entry is None:
        return None
    cases = entry["cases"]
    deaths = entry["deaths"]
    return {
        **entry,
        "cfr": round(deaths / cases * 100, 2) if cases else None,
    }
