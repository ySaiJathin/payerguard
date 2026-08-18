from datetime import datetime, timezone

import pytest

from app.baseline.schemas import (
    BaselineSnapshot,
    DataHealthBaseline,
    LengthOfStayBaseline,
    Percentiles,
    SourceDateRange,
    VolumeBaseline,
    VolumeWindow,
)
from app.features.window_level.deviation_features import (
    WindowDefinitionMismatchError,
    compute_deviation_features,
)

_PERCENTILES = Percentiles(p25=0, p50=0, p75=0, p95=0, p99=0)


def _baseline_with_weekly_windows() -> BaselineSnapshot:
    return BaselineSnapshot(
        snapshot_id="snap-1",
        source_file="src.csv",
        source_row_count=10,
        source_date_range=SourceDateRange(min_date="2026-01-01", max_date="2026-01-07"),
        volume_baseline=VolumeBaseline(
            window_definition="weekly",
            windows=[VolumeWindow(window_id="2026-W00", start="2026-01-01", end="2026-01-07", claim_count=10)],
        ),
        amount_baselines=[],
        data_health_baseline=DataHealthBaseline(
            historical_missing_rate_by_column={}, historical_duplicate_rate=0.0, categorical_distributions={}
        ),
        length_of_stay_baseline=LengthOfStayBaseline(
            mean=5.0, median=5.0, percentiles=_PERCENTILES, claims_included=10, claims_excluded_missing_dates=0
        ),
        computed_at=datetime.now(timezone.utc),
    )


def test_mismatched_window_definition_raises_instead_of_silently_computing():
    aggregates = [{"window_id": "2026-01-01", "claim_count": 14, "amount_stats": {}}]
    with pytest.raises(WindowDefinitionMismatchError):
        compute_deviation_features(aggregates, _baseline_with_weekly_windows(), "daily")
