from datetime import datetime, timezone

import pandas as pd
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
from app.data_engineering.invalid_value_detection import ReferenceStats
from app.data_engineering.schemas import ColumnCategory
from app.features import features_log
from app.features.window_feature_service import compute_window_features

CATEGORIES = {
    "CLM_FROM_DT": ColumnCategory.DATE,
    "CLM_PMT_AMT": ColumnCategory.AMOUNT,
    "PTNT_DSCHRG_STUS_CD": ColumnCategory.CATEGORICAL_CODE,
}
_PERCENTILES = Percentiles(p25=0, p50=0, p75=0, p95=0, p99=0)


def _reference_stats() -> ReferenceStats:
    return ReferenceStats(date_min=None, date_max=None, known_values={"PTNT_DSCHRG_STUS_CD": {"01"}})


def _baseline() -> BaselineSnapshot:
    return BaselineSnapshot(
        snapshot_id="snap-1",
        source_file="src.csv",
        source_row_count=2,
        source_date_range=SourceDateRange(min_date="2026-01-01", max_date="2026-01-01"),
        volume_baseline=VolumeBaseline(
            window_definition="daily",
            windows=[VolumeWindow(window_id="2026-01-01", start="2026-01-01", end="2026-01-01", claim_count=2)],
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
            mean=5.0, median=5.0, percentiles=_PERCENTILES, claims_included=2, claims_excluded_missing_dates=0
        ),
        computed_at=datetime.now(timezone.utc),
    )


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "CLM_FROM_DT": ["2026-01-01", "2026-01-01"],
            "CLM_PMT_AMT": [100.0, 200.0],
            "PTNT_DSCHRG_STUS_CD": ["01", "01"],
        }
    )


def test_every_window_feature_row_has_null_not_zero_anomaly_count():
    rows = compute_window_features(_df(), CATEGORIES, _reference_stats(), _baseline(), "daily")

    assert len(rows) == 1
    assert all(r.anomaly_count is None for r in rows)


def test_anomaly_count_only_settable_via_dedicated_enrichment_path(tmp_path):
    rows = compute_window_features(_df(), CATEGORIES, _reference_stats(), _baseline(), "daily")
    features_log.write_window_features(rows, out_dir=tmp_path)

    persisted = features_log.read_window_features(out_dir=tmp_path)
    assert persisted[0].anomaly_count is None

    updated = features_log.update_window_anomaly_count("2026-01-01", 3, out_dir=tmp_path)
    assert updated.anomaly_count == 3
    assert updated.claim_count == persisted[0].claim_count
    assert updated.volume_deviation == persisted[0].volume_deviation

    reread = features_log.read_window_features(out_dir=tmp_path)
    assert reread[0].anomaly_count == 3


def test_update_unknown_window_id_raises(tmp_path):
    rows = compute_window_features(_df(), CATEGORIES, _reference_stats(), _baseline(), "daily")
    features_log.write_window_features(rows, out_dir=tmp_path)

    with pytest.raises(KeyError):
        features_log.update_window_anomaly_count("does-not-exist", 1, out_dir=tmp_path)
