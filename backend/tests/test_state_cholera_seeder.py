"""The verified-dataset seeder loads the real CSV shipped with the backend."""
import csv

from app.models import StateCholeraRecord
from app.seed_state_cholera import DEFAULT_CSV, epi_week_start, seed_state_cholera


def test_default_csv_path_points_at_the_shipped_dataset():
    # Regression: this used to resolve one directory too high (repo root), so
    # the seeder raised FileNotFoundError on its first real invocation.
    assert DEFAULT_CSV.is_file(), f"seeder default CSV missing: {DEFAULT_CSV}"
    assert DEFAULT_CSV.name == "final_state_cholera_dataset_v2.csv"


def test_seeder_loads_every_row_with_flags_intact(db_session):
    with open(DEFAULT_CSV, encoding="utf-8") as fh:
        expected = list(csv.DictReader(fh))

    result = seed_state_cholera(db=db_session)
    assert result["inserted"] == len(expected)
    assert db_session.query(StateCholeraRecord).count() == len(expected)

    quarantined = sum(1 for r in expected if r["monotonic_ok"].strip().lower() == "false")
    assert (
        db_session.query(StateCholeraRecord)
        .filter(StateCholeraRecord.monotonic_ok.is_(False))
        .count()
        == quarantined
    )


def test_report_date_is_the_monday_of_the_epi_week():
    monday = epi_week_start(2021, 47)
    assert monday.isoweekday() == 1
    assert monday.isocalendar()[:2] == (2021, 47)
