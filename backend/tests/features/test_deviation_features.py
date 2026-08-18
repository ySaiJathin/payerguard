from datetime import datetime, timezone

import pytest

from app.baseline.schemas import (
    AmountBaseline,
    BaselineSnapshot,
    DataHealthBaseline,
    LengthOfStayBaseline,
    Percentiles,
    SourceDateRange,
    VolumeBaseline,
    VolumeWindow,
)
from app.features.window_level.deviation_features import compute_deviation_features

_PERCENTILES = Percentiles(p25=0, p50=0, p75=0, p95=0, p99=0)


def _baseline(window_definition: str = "daily") -> BaselineSnapshot:
    return BaselineSnapshot(
        snapshot_id="snap-1",
        source_file="src.csv",
        source_row_count=10,
        source_date_range=SourceDateRange(min_date="2026-01-01", max_date="2026-01-02"),
        volume_baseline=VolumeBaseline(
            window_definition=window_definition,
            windows=[
                VolumeWindow(window_id="2026-01-01", start="2026-01-01", end="2026-01-01", claim_count=10),
            ],
        ),
        amount_baselines=[
            AmountBaseline(
                column_name="CLM_PMT_AMT", mean=100.0, median=100.0, std=10.0, min=0.0, max=200.0, percentiles=_PERCENTILES
            )
        ],
        data_health_baseline=DataHealthBaseline(
            historical_missing_rate_by_column={}, historical_duplicate_rate=0.0, categorical_distributions={}
        ),
        length_of_stay_baseline=LengthOfStayBaseline(
            mean=5.0, median=5.0, percentiles=_PERCENTILES, claims_included=10, claims_excluded_missing_dates=0
        ),
        computed_at=datetime.now(timezone.utc),
    )


def test_deviation_recomputable_by_hand_from_baseline_and_window():
    aggregates = [
        {"window_id": "2026-01-01", "claim_count": 14, "amount_stats": {"CLM_PMT_AMT": {"mean": 130.0, "median": 130.0, "std": 5.0}}}
    ]
    deviations = compute_deviation_features(aggregates, _baseline(), "daily")

    assert deviations["2026-01-01"]["volume_deviation"] == pytest.approx(14 - 10)
    assert deviations["2026-01-01"]["amount_deviation"]["CLM_PMT_AMT"] == pytest.approx(130.0 - 100.0)


def test_window_not_in_baseline_treated_as_zero_expected_count():
    aggregates = [{"window_id": "2026-02-01", "claim_count": 3, "amount_stats": {}}]
    deviations = compute_deviation_features(aggregates, _baseline(), "daily")
    assert deviations["2026-02-01"]["volume_deviation"] == pytest.approx(3)
