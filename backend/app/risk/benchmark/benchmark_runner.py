"""Orchestrates the full risk model benchmark (spec FR-001-FR-004, FR-009):
fits every hyperparameter candidate for each of the 3 model types on
train-range rows only, picks the validation-PR-AUC-best candidate per
model type (tuning happens exclusively on validation-range rows -- FR-003),
evaluates that one fitted candidate on test-range rows exactly once, and
persists both the fitted model artifacts and the result set.

**Decision threshold**: classification-dependent metrics
(accuracy/precision/recall/F1/false-negative-rate) use a fixed 0.5
probability threshold on `predict_proba`, the standard default -- this
keeps every metric exactly reproducible from the model's own
`predict_proba` output (spec SC-002) without introducing an additional,
undocumented threshold-tuning step beyond the hyperparameter tuning
FR-003 already requires. ROC-AUC and PR-AUC are threshold-independent and
computed directly from the continuous probability scores.
"""

import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from app.data_engineering.paths import models_dir
from app.risk.benchmark import logistic, random_forest, xgboost_model
from app.risk.benchmark.calibration import brier_score
from app.risk.benchmark.data_loading import BenchmarkFrame
from app.risk.benchmark.schemas import RiskBenchmarkResult, RiskModelCandidate

DECISION_THRESHOLD = 0.5
MIN_TUNING_CLASS_COUNT = 2

_MODEL_MODULES = (logistic, random_forest, xgboost_model)


def _safe_roc_auc(y_true: pd.Series, y_proba: np.ndarray, warnings: list[str], model_type: str) -> float:
    if y_true.nunique() < 2:
        warnings.append(
            f"{model_type}: test split has a single label class -- ROC-AUC is undefined, reported as 0.5 "
            "(the no-discrimination reference value)."
        )
        return 0.5
    return float(roc_auc_score(y_true, y_proba))


def _safe_pr_auc(y_true: pd.Series, y_proba: np.ndarray, warnings: list[str], model_type: str) -> float:
    if y_true.sum() == 0:
        warnings.append(
            f"{model_type}: test split has zero positive labels -- PR-AUC is undefined, reported as 0.0."
        )
        return 0.0
    return float(average_precision_score(y_true, y_proba))


def _tune(module, X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series, warnings: list[str]):
    """Fits every grid candidate on train, scores each on validation PR-AUC,
    and returns (best_fitted_model, best_params). Falls back to the grid's
    first candidate, fit on train but unscored, when validation doesn't
    have enough class diversity to compute PR-AUC meaningfully."""
    if y_val.nunique() < MIN_TUNING_CLASS_COUNT:
        warnings.append(
            f"{module.MODEL_TYPE.value}: validation split has fewer than {MIN_TUNING_CLASS_COUNT} label "
            "classes -- skipping hyperparameter tuning, using the first grid candidate untuned."
        )
        params = module.HYPERPARAMETER_GRID[0]
        model = module.build_model(params)
        model.fit(X_train, y_train)
        return model, params

    best_model, best_params, best_score = None, None, -1.0
    for params in module.HYPERPARAMETER_GRID:
        model = module.build_model(params)
        model.fit(X_train, y_train)
        val_proba = model.predict_proba(X_val)[:, 1]
        score = average_precision_score(y_val, val_proba)
        if score > best_score:
            best_model, best_params, best_score = model, params, score
    return best_model, best_params


def run_benchmark(frame: BenchmarkFrame, model_out_dir: Path | None = None) -> tuple[list[RiskBenchmarkResult], str | None]:
    X_train, y_train = frame.train
    X_val, y_val = frame.validation
    X_test, y_test = frame.test

    model_out_dir = model_out_dir or (models_dir() / "risk")
    model_out_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    if len(X_val) < 5:
        warnings.append(f"validation split has only {len(X_val)} row(s) -- tuning results may be unstable.")
    if len(X_test) < 5:
        warnings.append(f"test split has only {len(X_test)} row(s) -- evaluation metrics may be unstable.")

    results: list[RiskBenchmarkResult] = []
    for module in _MODEL_MODULES:
        model, params = _tune(module, X_train, y_train, X_val, y_val, warnings)

        test_proba = model.predict_proba(X_test)[:, 1]
        test_pred = (test_proba >= DECISION_THRESHOLD).astype(int)

        recall = float(recall_score(y_test, test_pred, zero_division=0)) if len(y_test) else 0.0
        result = RiskBenchmarkResult(
            model_type=module.MODEL_TYPE,
            accuracy=float(accuracy_score(y_test, test_pred)) if len(y_test) else 0.0,
            precision=float(precision_score(y_test, test_pred, zero_division=0)) if len(y_test) else 0.0,
            recall=recall,
            f1=float(f1_score(y_test, test_pred, zero_division=0)) if len(y_test) else 0.0,
            roc_auc=_safe_roc_auc(y_test, test_proba, warnings, module.MODEL_TYPE.value),
            pr_auc=_safe_pr_auc(y_test, test_proba, warnings, module.MODEL_TYPE.value),
            calibration_brier_score=brier_score(y_test.to_numpy(), test_proba) if len(y_test) else 1.0,
            false_negative_rate=1.0 - recall,
            label_distribution_context=frame.label_distribution_context,
            risk_dataset_version=frame.risk_dataset_version,
            split_id=frame.split.split_id,
        )
        results.append(result)

        candidate = RiskModelCandidate(
            model_type=module.MODEL_TYPE,
            hyperparameters=params,
            artifact_path=str(model_out_dir / f"{module.MODEL_TYPE.value}.pkl"),
        )
        with (model_out_dir / f"{module.MODEL_TYPE.value}.pkl").open("wb") as f:
            pickle.dump(
                {
                    "model_type": module.MODEL_TYPE.value,
                    "model": model,
                    "feature_columns": list(X_train.columns),
                    "candidate": candidate.model_dump(),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                f,
            )

    data_scale_warning = " ".join(warnings) if warnings else None
    return results, data_scale_warning
