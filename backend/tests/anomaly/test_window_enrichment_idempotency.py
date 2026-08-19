import numpy as np
import pandas as pd

from app.anomaly import window_enrichment
from app.anomaly.benchmark import run_benchmark
from app.features.schemas import WindowFeatures
from app.features.selection.temporal_split import compute_temporal_split

N_DAYS = 300
N_WINDOWS = 10
DAYS_PER_WINDOW = N_DAYS // N_WINDOWS


def _matrix() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=N_DAYS, freq="D")
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "CLM_FROM_DT": dates,
            "amount_col": rng.normal(100, 10, N_DAYS),
            "feature_b": rng.normal(0, 1, N_DAYS),
            "feature_c": rng.normal(5, 2, N_DAYS),
            "feature_d": rng.normal(-3, 1, N_DAYS),
        },
        index=[f"C{i}" for i in range(N_DAYS)],
    )
    df.index.name = "CLM_ID"
    return df


def _windows(dates: pd.Series) -> list[WindowFeatures]:
    windows = []
    for w in range(N_WINDOWS):
        start = dates.iloc[w * DAYS_PER_WINDOW]
        end = dates.iloc[min((w + 1) * DAYS_PER_WINDOW - 1, N_DAYS - 1)]
        windows.append(
            WindowFeatures(
                window_id=f"W{w}",
                start=start.date(),
                end=end.date(),
                claim_count=DAYS_PER_WINDOW,
                missing_pct=0.0,
                duplicate_pct=0.0,
                invalid_status_pct=0.0,
                volume_deviation=0.0,
                anomaly_count=None,
            )
        )
    return windows


def _claim_window_map(matrix_index, windows: list[WindowFeatures]) -> dict[str, str]:
    mapping = {}
    for i, claim_id in enumerate(matrix_index):
        w = min(i // DAYS_PER_WINDOW, N_WINDOWS - 1)
        mapping[claim_id] = windows[w].window_id
    return mapping


def _patch(monkeypatch, run_result, claim_window_map, store):
    monkeypatch.setattr(window_enrichment, "read_benchmark_run_result", lambda: run_result)
    monkeypatch.setattr(window_enrichment, "load_claim_window_map", lambda: claim_window_map)
    monkeypatch.setattr(window_enrichment, "read_window_features", lambda: store)

    def _update_many(counts: dict[str, int]):
        by_id = {w.window_id: i for i, w in enumerate(store)}
        unknown = set(counts) - set(by_id)
        if unknown:
            raise KeyError(sorted(unknown))
        for window_id, anomaly_count in counts.items():
            i = by_id[window_id]
            store[i] = store[i].model_copy(update={"anomaly_count": anomaly_count})
        return len(counts)

    monkeypatch.setattr(window_enrichment, "update_window_anomaly_counts", _update_many)


def test_enrichment_fills_every_window_and_is_idempotent(monkeypatch, tmp_path):
    matrix = _matrix()
    split = compute_temporal_split(matrix["CLM_FROM_DT"])
    model_out_dir = tmp_path / "models"
    run_result = run_benchmark(matrix=matrix, split=split, out_dir=tmp_path / "reports", model_out_dir=model_out_dir)

    windows = _windows(matrix["CLM_FROM_DT"])
    claim_window_map = _claim_window_map(matrix.index, windows)
    store = list(windows)
    _patch(monkeypatch, run_result, claim_window_map, store)

    result_1 = window_enrichment.enrich_windows(matrix=matrix, model_out_dir=model_out_dir)
    counts_1 = [w.anomaly_count for w in store]

    assert result_1.windows_enriched == N_WINDOWS
    assert all(c is not None for c in counts_1)
    assert result_1.model_used == run_result.production_model_selection.selected_model.value

    result_2 = window_enrichment.enrich_windows(matrix=matrix, model_out_dir=model_out_dir)
    counts_2 = [w.anomaly_count for w in store]

    assert counts_1 == counts_2
    assert result_1.model_used == result_2.model_used
