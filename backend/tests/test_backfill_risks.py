"""Unit tests for the pure month_range generator in backfill_risks."""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.backfill_risks import month_range


def test_month_range_basic():
    assert list(month_range(date(2024, 1, 1), date(2024, 3, 1))) == [
        date(2024, 1, 1),
        date(2024, 2, 1),
        date(2024, 3, 1),
    ]


def test_month_range_cross_year():
    months = list(month_range(date(2024, 12, 1), date(2025, 2, 1)))
    assert months == [date(2024, 12, 1), date(2025, 1, 1), date(2025, 2, 1)]


def test_month_range_normalizes_day():
    # Day-of-month is normalized to the 1st regardless of input day.
    assert list(month_range(date(2024, 1, 15), date(2024, 1, 31))) == [date(2024, 1, 1)]


def test_month_range_empty_when_start_after_end():
    assert list(month_range(date(2024, 3, 1), date(2024, 1, 1))) == []
