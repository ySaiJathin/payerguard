"""Applies the selected production anomaly model to real (non-injected)
claims per window and populates Phase 5's deferred
`WindowFeatures.anomaly_count` (spec FR-010, FR-011).

Kept structurally separate from `benchmark.py`'s evaluation pass (which
must touch injected/labeled validation/test copies) -- this module only
ever scores real claim data, reducing the risk of an injected instance
leaking into `anomaly_count` (research.md).
"""

import pickle
from pathlib import Path

import pandas as pd

from app.anomaly.benchmark import read_benchmark_run_result
from app.anomaly.data_loading import load_benchmark_inputs, load_claim_window_map
from app.anomaly.schemas import EnrichWindowsResult
from app.data_engineering.paths import models_dir
from app.features.features_log import read_window_features, update_window_anomaly_counts


class NoProductionModelSelectedError(RuntimeError):
    """Raised when `POST /anomaly/enrich-windows` is called before a
    benchmark run has produced a `ProductionModelSelection` (contracts/api.md's
    409 response)."""


def _load_selected_artifact(model_out_dir: Path | None = None) -> dict:
    run_result = read_benchmark_run_result()
    if run_result is None:
        raise NoProductionModelSelectedError(
            "No ProductionModelSelection exists yet -- run POST /anomaly/benchmark first."
        )

    model_type = run_result.production_model_selection.selected_model
    artifact_path = (model_out_dir or models_dir()) / f"{model_type.value}.pkl"
    if not artifact_path.exists():
        raise NoProductionModelSelectedError(
            f"Selected model artifact not found at {artifact_path} -- run POST /anomaly/benchmark again."
        )
    with artifact_path.open("rb") as f:
        return pickle.load(f)


def enrich_windows(matrix: pd.DataFrame | None = None, model_out_dir: Path | None = None) -> EnrichWindowsResult:
    artifact = _load_selected_artifact(model_out_dir)
    detector = artifact["model"]
    feature_columns: list[str] = artifact["feature_columns"]
    threshold = next(iter(artifact["calibrated_thresholds"].values()))
    train_medians = artifact["train_medians"]

    if matrix is None:
        matrix = load_benchmark_inputs()
    claim_window_map = load_claim_window_map()

    real_matrix = matrix[feature_columns].fillna(pd.Series(train_medians))
    scores = detector.score(real_matrix)
    flagged = pd.Series(scores > threshold, index=real_matrix.index)

    # Invert the claim -> window map once. Scanning all 58k entries per
    # window (2,928 of them) meant ~170M comparisons per run; grouping first
    # makes it a single pass. Only claims that were actually scored are
    # counted, so a claim missing from the feature matrix is excluded here
    # rather than silently counted as "not anomalous".
    scored_claims = set(flagged.index)
    claims_by_window: dict[str, list[str]] = {}
    for claim_id, window_id in claim_window_map.items():
        if claim_id in scored_claims:
            claims_by_window.setdefault(window_id, []).append(claim_id)

    counts = {
        window.window_id: int(flagged.loc[claims_by_window[window.window_id]].sum())
        if window.window_id in claims_by_window
        else 0
        for window in read_window_features()
    }

    # One write for the whole pass. Calling the single-window updater in a
    # loop rewrote the entire features file per window, which is both
    # quadratic and -- because each rewrite truncates before writing -- a
    # window in which an interrupted run corrupts the file.
    windows_enriched = update_window_anomaly_counts(counts)

    return EnrichWindowsResult(windows_enriched=windows_enriched, model_used=artifact["model_type"])
