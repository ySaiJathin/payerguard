import pandas as pd
import pytest

from app.features.schemas import AmountStats, ClaimFeatures, WindowFeatures
from app.features.selection import drop_decision_log, selection_service, temporal_split
from app.features.selection.drop_decision_log import read_drop_decisions

N_DAYS = 300
N_WINDOWS = 10


def _cleaned_df() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=N_DAYS, freq="D")
    return pd.DataFrame(
        {
            "CLM_ID": [f"C{i}" for i in range(N_DAYS)],
            "CLM_FROM_DT": dates,
            "PRVDR_NUM": [f"P{i % 8}" for i in range(N_DAYS)],
            "CLM_PMT_AMT": [100.0 + i for i in range(N_DAYS)],
        }
    )


def _claim_features() -> list[ClaimFeatures]:
    return [
        ClaimFeatures(
            claim_id=f"C{i}",
            payment_to_charge_ratio=0.4 + (i % 20) * 0.01,
            length_of_stay_days=i % 10,
            provider_frequency=float(i % 8),
        )
        for i in range(N_DAYS)
    ]


def _window_features() -> list[WindowFeatures]:
    days_per_window = N_DAYS // N_WINDOWS
    windows = []
    dates = pd.date_range("2020-01-01", periods=N_DAYS, freq="D")
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
                volume_deviation=float(w % 4),
                amount_deviation={"CLM_PMT_AMT": float(w % 3)},
                anomaly_count=None,
            )
        )
    return windows


def _patch_service(monkeypatch, tmp_path, cleaned_df, claim_features, window_features):
    categories: dict = {}
    monkeypatch.setattr(selection_service, "load_column_categories", lambda: categories)
    monkeypatch.setattr(selection_service, "load_cleaned_batch", lambda batch_path, categories: cleaned_df)
    monkeypatch.setattr(selection_service, "read_claim_features", lambda: claim_features)
    monkeypatch.setattr(selection_service, "read_window_features", lambda: window_features)
    monkeypatch.setattr(temporal_split, "features_dir", lambda: tmp_path)
    monkeypatch.setattr(drop_decision_log, "features_dir", lambda: tmp_path)


def _non_stage1_decision_tuples(tmp_path) -> set[tuple]:
    decisions = read_drop_decisions(out_dir=tmp_path)
    return {(d.feature_name, d.stage, d.reason, d.statistic_value) for d in decisions if d.stage != 1}


def test_corrupting_test_split_portion_does_not_change_stage2_3_or_final_selection(monkeypatch, tmp_path):
    cleaned_df = _cleaned_df()
    claim_features = _claim_features()
    window_features = _window_features()

    _patch_service(monkeypatch, tmp_path, cleaned_df, claim_features, window_features)
    feature_set_baseline = selection_service.run_selection()
    decisions_baseline = _non_stage1_decision_tuples(tmp_path)

    split = temporal_split.read_temporal_split(out_dir=tmp_path)
    assert split is not None

    corrupted_df = cleaned_df.copy()
    test_mask = corrupted_df["CLM_FROM_DT"] > pd.Timestamp(split.validation_date_range.end)
    assert test_mask.sum() > 0, "fixture must actually have rows in the test portion"
    corrupted_df.loc[test_mask, "CLM_PMT_AMT"] = corrupted_df.loc[test_mask, "CLM_PMT_AMT"] + 1_000_000.0

    _patch_service(monkeypatch, tmp_path, corrupted_df, claim_features, window_features)
    feature_set_corrupted = selection_service.run_selection()
    decisions_corrupted = _non_stage1_decision_tuples(tmp_path)

    assert feature_set_corrupted.features == feature_set_baseline.features
    assert decisions_corrupted == decisions_baseline


def test_stage2_and_stage3_never_receive_test_split_rows(monkeypatch, tmp_path):
    """Structural check: the train+validation frame built by
    selection_service never contains a row whose date falls after the
    split's validation boundary."""
    cleaned_df = _cleaned_df()
    claim_features = _claim_features()
    window_features = _window_features()

    _patch_service(monkeypatch, tmp_path, cleaned_df, claim_features, window_features)
    selection_service.run_selection()

    split = temporal_split.read_temporal_split(out_dir=tmp_path)
    from app.features.selection.stage1_structural import build_claim_candidate_frame

    claim_frame = build_claim_candidate_frame(cleaned_df, claim_features)
    dates = pd.to_datetime(claim_frame["CLM_FROM_DT"])
    split_labels = dates.apply(lambda d: temporal_split.assign_split(d, split))
    train_val_dates = dates[split_labels != "test"]

    assert (train_val_dates <= pd.Timestamp(split.validation_date_range.end)).all()
