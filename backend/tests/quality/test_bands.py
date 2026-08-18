import pytest

from app.quality.bands import classify_duplicate_rate, classify_missing_rate
from app.quality.schemas import Band


@pytest.mark.parametrize(
    "pct,expected",
    [
        (0.0, Band.PASS),
        (1.99, Band.PASS),
        (2.0, Band.WARNING),
        (4.99, Band.WARNING),
        (5.0, Band.WARNING),
        (5.01, Band.CRITICAL),
        (50.0, Band.CRITICAL),
    ],
)
def test_missing_rate_bands(pct, expected):
    assert classify_missing_rate(pct) == expected


@pytest.mark.parametrize(
    "pct,expected",
    [
        (0.0, Band.PASS),
        (0.01, Band.WARNING),
        (1.0, Band.WARNING),
        (1.01, Band.CRITICAL),
        (10.0, Band.CRITICAL),
    ],
)
def test_duplicate_rate_bands(pct, expected):
    assert classify_duplicate_rate(pct) == expected
