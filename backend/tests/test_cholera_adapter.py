"""Tests for cholera_adapter pure helpers."""
from datetime import date

from app.services.cholera_adapter import (
    month_to_date,
    parse_cholera_row,
    epi_week_of_date,
)


def test_month_to_date():
    assert month_to_date(2024, "March") == date(2024, 3, 1)
    assert month_to_date(2024, "December") == date(2024, 12, 1)


def test_parse_cholera_row():
    row = {"State": "Abia", "LGA": "Aba North", "Year": "2024", "Month": "March",
           "Suspected_Cases": "10", "Confirmed_Cases": "3", "Deaths": "0",
           "Death_Rate_Percentage": "0.00%", "Latitude": "5.45", "Longitude": "7.52",
           "Classification": "Sporadic Contagion"}
    rec = parse_cholera_row(row)
    assert rec["lga_name"] == "Aba North"
    assert rec["state"] == "Abia"
    assert rec["report_date"] == date(2024, 3, 1)
    assert rec["suspected_cases"] == 10
    assert rec["confirmed_cases"] == 3
    assert rec["deaths"] == 0
    assert rec["notes"] == "Sporadic Contagion"


def test_epi_week_of_date():
    # Hardcoded ISO-week boundary cases (verified via date.isocalendar()).
    # epi_week_of_date returns (iso_week, iso_year).

    # Year-boundary: Sun Jan 1 2023 falls in ISO week 52 of 2022.
    assert epi_week_of_date(date(2023, 1, 1)) == (52, 2022)
    # Year-boundary: Mon Dec 30 2024 falls in ISO week 1 of 2025.
    assert epi_week_of_date(date(2024, 12, 30)) == (1, 2025)
    # Normal mid-year case: Mar 1 2024 is ISO week 9 of 2024.
    assert epi_week_of_date(date(2024, 3, 1)) == (9, 2024)
