"""Scores one new window with the Phase 9-selected production risk model
(spec 017-batch-file-ingestion research.md, Pre-Implementation Finding 3).

Phase 9 (`risk.benchmark`) selects and persists the winning model but
exposes no function that scores a *new* row with it -- only
`app.demo.risk_model.predict_risk` does that, and it is demo-scoped
(a fitted `XGBRegressor` over synthetic data, not the real persisted
production classifier). This module is `risk`'s own equivalent for real
ingested data, owned here rather than in `ingestion` per constitution
Principle VI.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from app.data_engineering.paths import models_dir
from app.risk.benchmark.benchmark_log import read_latest_run_result


class NoProductionRiskModelError(RuntimeError):
    """Raised when no risk benchmark run has been persisted yet (Phase 9
    hasn't run) -- a window cannot be honestly scored without a real,
    empirically-selected model to score it with (constitution Principle I,
    II)."""


def _load_selected_artifact(model_out_dir: Path | None = None) -> dict:
    run_result = read_latest_run_result()
    if run_result is None:
        raise NoProductionRiskModelError(
            "No risk model benchmark run found -- run POST /risk/benchmark (Phase 9) first."
        )
    selected = run_result.production_model_selection.selected_model
    model_out_dir = model_out_dir or (models_dir() / "risk")
    artifact_path = model_out_dir / f"{selected.value}.pkl"
    if not artifact_path.exists():
        raise NoProductionRiskModelError(
            f"Phase 9 selected {selected.value!r} but its artifact is missing at {artifact_path} -- "
            "re-run POST /risk/benchmark."
        )
    with artifact_path.open("rb") as f:
        return pickle.load(f)  # noqa: S301 -- trusted, project-generated artifact, matching anomaly's identical pattern


def score_window(row: dict, model_out_dir: Path | None = None) -> float:
    """Returns a risk score in [0, 100] for one window, `row` shaped like
    one of `risk.dataset.row_assembly.assemble_rows`'s dicts (minus
    `window_id`/`window_start`/`window_end`, which are identifiers, not
    features).

    Builds the model's input using its own persisted `feature_columns`
    (never guessed or re-derived) so the column order used at inference
    always matches what the model was actually trained on.
    """
    artifact = _load_selected_artifact(model_out_dir)
    model = artifact["model"]
    feature_columns: list[str] = artifact["feature_columns"]

    X = pd.DataFrame([{col: row.get(col, 0.0) for col in feature_columns}], columns=feature_columns)
    proba = float(model.predict_proba(X)[0, 1])
    return float(np.clip(proba * 100.0, 0.0, 100.0))
