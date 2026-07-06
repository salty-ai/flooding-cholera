# backend/tests/test_correlation_service.py
from app.services.correlation_service import cross_correlate

def test_cross_correlate_perfect_lag1():
    # flood at month m, cases at month m+1 -> perfect correlation at lag 1
    flood = {(2024, m): 0.0 for m in range(1, 13)}
    cases = {(2024, m): 0.0 for m in range(1, 13)}
    # flood in months 2,4,6,8; cases one month later
    for m in (2, 4, 6, 8):
        flood[(2024, m)] = 10.0
        if m + 1 <= 12:
            cases[(2024, m + 1)] = 10.0
    results = cross_correlate(flood, cases, lags=(0, 1, 2))
    by_lag = {r["lag"]: r for r in results}
    assert by_lag[1]["pearson_r"] > 0.9
    assert by_lag[1]["n"] >= 6
    assert not by_lag[1]["insufficient_data"]

def test_cross_correlate_insufficient_data():
    flood = {(2024, 1): 1.0, (2024, 2): 0.0}
    cases = {(2024, 1): 0.0, (2024, 2): 1.0}
    results = cross_correlate(flood, cases, lags=(0,))
    assert results[0]["insufficient_data"] is True
