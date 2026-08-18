from datetime import date, datetime, timezone

import pandas as pd
import pytest

from app.anomaly import data_loading
from app.features.schemas import AmountStats, ClaimFeatures, WindowFeatures
from app.features.selection.schemas import DateRange, SelectedFeatureSet, TemporalSplit

N_DAYS = 60
N_WINDOWS = 6


def _cleaned_df() -> pd.DataFrame:
    dates = pd.date_range("2021-01-01", periods=N_DAYS, freq="D")
    return pd.DataFrame(
        {
            "CLM_ID": [f"C{i}" for i in range(N_DAYS)],
            "CLM_FROM_DT": dates,
            "PRVDR_NUM": [f"P{i % 5}" for i in range(N_DAYS)],
            "CLM_PMT_AMT": [100.0 + i for i in range(N_DAYS)],
        }
    )


def _claim_features() -> list[ClaimFeatures]:
    return [
        ClaimFeatures(
            claim_id=f"C{i}",
            payment_to_charge_ratio=0.4 + (i % 20) * 0.01,
            length_of_stay_days=i % 10,
            provider_frequency=float(i % 5),
        )
        for i in range(N_DAYS)
    ]


def _window_features() -> list[WindowFeatures]:
    days_per_window = N_DAYS // N_WINDOWS
    dates = pd.date_range("2021-01-01", periods=N_DAYS, freq="D")
    windows = []
    for w in range(N_WINDOWS):
        start = dates[w * days_per_window]
        end = dates[min((w + 1) * days_per_window - 1, N_DAYS - 1)]
        windows.append(
            WindowFeatures(
                window_id=f"W{w}",
                start=start.date(),
                end=end.date(),
                claim_count=days_per_window,
                amount_stats={"CLM_PMT_AMT": AmountStats(mean=100.0 + w, median=95.0, std=10.0)},
                missing_pct=0.0,
                duplicate_pct=0.0,
                invalid_status_pct=0.0,
                volume_deviation=float(w % 3),
                amount_deviation={"CLM_PMT_AMT": float(w % 2)},
                anomaly_count=None,
            )
        )
    return windows


def _split() -> TemporalSplit:
    return TemporalSplit(
        split_id="split-1",
        train_date_range=DateRange(start=date(2021, 1, 1), end=date(2021, 2, 10)),
        validation_date_range=DateRange(start=date(2021, 2, 11), end=date(2021, 2, 20)),
        test_date_range=DateRange(start=date(2021, 2, 21), end=date(2021, 3, 2)),
        train_count=50,
        validation_count=5,
        test_count=5,
        computed_at=datetime.now(timezone.utc),
    )


def _feature_set(features: list[str]) -> SelectedFeatureSet:
    return SelectedFeatureSet(
        version_id="fs-1",
        features=features,
        split_id="split-1",
        target_used_for_stage3="provisional_deviation_magnitude",
        stage1_drop_count=0,
        stage2_drop_count=0,
        stage3_drop_count=0,
        generated_at=datetime.now(timezone.utc),
    )


def _patch(monkeypatch, cleaned_df, claim_features, window_features, split, feature_set):
    monkeypatch.setattr(data_loading, "load_column_categories", lambda: {})
    monkeypatch.setattr(data_loading, "load_cleaned_batch", lambda batch_path, categories: cleaned_df)
    monkeypatch.setattr(data_loading, "read_claim_features", lambda: claim_features)
    monkeypatch.setattr(data_loading, "read_window_features", lambda: window_features)
    monkeypatch.setattr(data_loading, "read_temporal_split", lambda: split)
    monkeypatch.setattr(data_loading, "read_selected_feature_set", lambda: feature_set)


def test_matrix_columns_are_exactly_the_numeric_subset_of_selected_features(monkeypatch):
    cleaned_df = _cleaned_df()
    claim_features = _claim_features()
    window_features = _window_features()
    split = _split()
    # PRVDR_NUM is non-numeric (string) and must be excluded even though it's
    # in the selected feature list; the rest are numeric and must survive.
    feature_set = _feature_set(
        ["CLM_PMT_AMT", "payment_to_charge_ratio", "provider_frequency", "PRVDR_NUM", "claim_count"]
    )
    _patch(monkeypatch, cleaned_df, claim_features, window_features, split, feature_set)

    matrix = data_loading.load_benchmark_inputs()

    expected_numeric = {"CLM_PMT_AMT", "payment_to_charge_ratio", "provider_frequency", "claim_count"}
    assert set(matrix.columns) - {data_loading.CLAIM_DATE_COLUMN} == expected_numeric
    assert matrix.index.name == data_loading.CLAIM_ID_COLUMN
    assert len(matrix) == N_DAYS


def test_raises_when_temporal_split_missing(monkeypatch):
    cleaned_df = _cleaned_df()
    claim_features = _claim_features()
    window_features = _window_features()
    feature_set = _feature_set(["CLM_PMT_AMT"])
    _patch(monkeypatch, cleaned_df, claim_features, window_features, None, feature_set)

    with pytest.raises(data_loading.AnomalyInputUnavailableError):
        data_loading.load_benchmark_inputs()


def test_raises_when_selected_feature_set_missing(monkeypatch):
    cleaned_df = _cleaned_df()
    claim_features = _claim_features()
    window_features = _window_features()
    split = _split()
    _patch(monkeypatch, cleaned_df, claim_features, window_features, split, None)

    with pytest.raises(data_loading.AnomalyInputUnavailableError):
        data_loading.load_benchmark_inputs()
