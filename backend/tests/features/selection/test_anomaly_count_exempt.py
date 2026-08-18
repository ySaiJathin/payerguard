import pandas as pd

from app.features.schemas import AmountStats, ClaimFeatures, WindowFeatures
from app.features.selection import drop_decision_log, selection_service, temporal_split
from app.features.selection.drop_decision_log import read_drop_decisions, read_selected_feature_set

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
    """All-null `anomaly_count` across every window -- the pre-Phase-7
    state this exemption exists for (spec FR-008, SC-005)."""
    days_per_window = N_DAYS // N_WINDOWS
    dates = pd.date_range("2020-01-01", periods=N_DAYS, freq="D")
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
                volume_deviation=float(w % 4),
                amount_deviation={"CLM_PMT_AMT": float(w % 3)},
                anomaly_count=None,
            )
        )
    return windows


def test_anomaly_count_absent_from_every_stage_drop_list(monkeypatch, tmp_path):
    cleaned_df = _cleaned_df()
    claim_features = _claim_features()
    window_features = _window_features()
    assert all(wf.anomaly_count is None for wf in window_features)

    categories: dict = {}
    monkeypatch.setattr(selection_service, "load_column_categories", lambda: categories)
    monkeypatch.setattr(selection_service, "load_cleaned_batch", lambda batch_path, categories: cleaned_df)
    monkeypatch.setattr(selection_service, "read_claim_features", lambda: claim_features)
    monkeypatch.setattr(selection_service, "read_window_features", lambda: window_features)
    monkeypatch.setattr(temporal_split, "features_dir", lambda: tmp_path)
    monkeypatch.setattr(drop_decision_log, "features_dir", lambda: tmp_path)

    feature_set = selection_service.run_selection()

    all_decisions = read_drop_decisions(out_dir=tmp_path)
    dropped_names = {d.feature_name for d in all_decisions}
    assert "anomaly_count" not in dropped_names

    persisted = read_selected_feature_set(out_dir=tmp_path)
    assert persisted is not None
    assert "anomaly_count" in feature_set.features
    assert "anomaly_count" in persisted.features
