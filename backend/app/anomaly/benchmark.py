"""Anomaly detection benchmark and production model (Phase 7).

Orchestrates the full comparison (spec FR-001-FR-003, FR-009, FR-012):
loads Phase 6's shared train/validation/test split and selected numeric
feature matrix, fits IQR/HBOS/Isolation Forest/LOF on train only,
calibrates a threshold for each on validation only, injects synthetic
anomalies into validation/test copies (never train -- FR-005), scores test
exactly once, computes precision/recall/F1/FPR/latency/execution-time and a
per-injection-type breakdown against the injected ground truth, empirically
selects a production model, and persists both the fitted models and the
full result set.
"""

import pickle
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix

from app.anomaly.data_loading import AnomalyInputUnavailableError, load_benchmark_inputs
from app.anomaly.hbos import HBOSDetector
from app.anomaly.injection_harness import InjectedAnomalyInstance, inject_all
from app.anomaly.isolation_forest import IsolationForestDetector
from app.anomaly.iqr import IQRDetector
from app.anomaly.lof import LOFDetector
from app.anomaly.model_selection import select_production_model
from app.anomaly.schemas import (
    BenchmarkResult,
    BenchmarkRunResult,
    InjectionTypeMetrics,
    MeasurementContext,
    ModelType,
)
from app.data_engineering.paths import models_dir, reports_dir
from app.features.selection.schemas import TemporalSplit
from app.features.selection.temporal_split import CLAIM_DATE_COLUMN, assign_split, read_temporal_split

BENCHMARK_RESULTS_FILENAME = "anomaly_benchmark_results.json"
CALIBRATION_PERCENTILE = 95.0
# Fixed so injected-anomaly placement is reproducible across runs on
# unmodified data (not required by spec, but consistent with the rest of
# the pipeline's determinism-first stance -- constitution Principle III).
INJECTION_SEED = 20260818

_DETECTOR_FACTORIES = {
    ModelType.iqr: IQRDetector,
    ModelType.hbos: HBOSDetector,
    ModelType.isolation_forest: IsolationForestDetector,
    ModelType.lof: LOFDetector,
}


def _measurement_context() -> MeasurementContext:
    return MeasurementContext(
        hardware=f"{platform.system()} {platform.machine()} ({platform.processor() or 'unknown'})",
        python_version=sys.version.split()[0],
        run_timestamp=datetime.now(timezone.utc),
    )


def _split_matrix(matrix: pd.DataFrame, split: TemporalSplit) -> dict[str, pd.DataFrame]:
    labels = matrix[CLAIM_DATE_COLUMN].apply(lambda d: assign_split(d, split))
    return {name: matrix.loc[labels == name] for name in ("train", "validation", "test")}


def _metrics_from_confusion(y_true: pd.Series, y_pred: np.ndarray) -> tuple[float, float, float, float]:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=["normal", "anomaly"]).ravel()
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return precision, recall, f1, fpr


def _per_injection_type_breakdown(
    ground_truth: pd.Series, predictions: pd.Series, instances: list[InjectedAnomalyInstance]
) -> dict[str, InjectionTypeMetrics]:
    normal_rows = set(ground_truth.index[ground_truth == "normal"])
    rows_by_type: dict[str, set[str]] = {}
    for instance in instances:
        rows_by_type.setdefault(instance.injection_type.value, set()).update(instance.affected_rows)

    breakdown: dict[str, InjectionTypeMetrics] = {}
    for injection_type, rows in rows_by_type.items():
        subset = [r for r in (rows | normal_rows) if r in ground_truth.index]
        precision, recall, f1, _fpr = _metrics_from_confusion(
            ground_truth.loc[subset], predictions.loc[subset].to_numpy()
        )
        breakdown[injection_type] = InjectionTypeMetrics(precision=precision, recall=recall, f1=f1)
    return breakdown


def _results_path(out_dir: Path | None = None) -> Path:
    return (out_dir or reports_dir()) / BENCHMARK_RESULTS_FILENAME


def write_benchmark_run_result(run_result: BenchmarkRunResult, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or reports_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _results_path(out_dir)
    path.write_text(run_result.model_dump_json(indent=2), encoding="utf-8")
    return path


def read_benchmark_run_result(out_dir: Path | None = None) -> BenchmarkRunResult | None:
    path = _results_path(out_dir)
    if not path.exists():
        return None
    return BenchmarkRunResult.model_validate_json(path.read_text(encoding="utf-8"))


def run_benchmark(
    matrix: pd.DataFrame | None = None,
    split: TemporalSplit | None = None,
    out_dir: Path | None = None,
    model_out_dir: Path | None = None,
) -> BenchmarkRunResult:
    """Runs the full benchmark end to end and persists both the fitted
    model artifacts (`model_out_dir`, default `data/models/anomaly/`) and
    the result set (`out_dir`, default `data/reports/`). `matrix`/`split`
    are injectable for tests; production callers (the router) omit both and
    let `data_loading`/`read_temporal_split` supply them.
    """
    if matrix is None:
        matrix = load_benchmark_inputs()
    if split is None:
        split = read_temporal_split()
        if split is None:
            raise AnomalyInputUnavailableError("No TemporalSplit computed yet -- run POST /features/split first.")

    feature_columns = [c for c in matrix.columns if c != CLAIM_DATE_COLUMN]
    splits = _split_matrix(matrix, split)
    train_df = splits["train"][feature_columns]
    validation_df = splits["validation"][feature_columns]
    test_df = splits["test"][feature_columns]

    train_medians = train_df.median()
    train_df = train_df.fillna(train_medians)
    validation_df = validation_df.fillna(train_medians)
    test_df = test_df.fillna(train_medians)

    train_bounds = {col: (float(train_df[col].min()), float(train_df[col].max())) for col in feature_columns}
    train_std = {col: float(train_df[col].std()) for col in feature_columns}

    rng = np.random.default_rng(INJECTION_SEED)
    validation_injected, _validation_truth, _validation_instances = inject_all(
        validation_df, feature_columns, "validation", rng, train_bounds, train_std
    )
    test_injected, test_truth, test_instances = inject_all(
        test_df, feature_columns, "test", rng, train_bounds, train_std
    )

    measurement_context = _measurement_context()
    model_out_dir = model_out_dir or models_dir()
    model_out_dir.mkdir(parents=True, exist_ok=True)

    results: list[BenchmarkResult] = []
    for model_type, factory in _DETECTOR_FACTORIES.items():
        start = time.perf_counter()
        detector = factory()
        detector.fit(train_df)

        validation_scores = detector.score(validation_injected[feature_columns])
        threshold = float(np.percentile(validation_scores, CALIBRATION_PERCENTILE))

        score_start = time.perf_counter()
        test_scores = detector.score(test_injected[feature_columns])
        score_end = time.perf_counter()

        predictions = pd.Series(
            np.where(test_scores > threshold, "anomaly", "normal"), index=test_injected.index
        )

        precision, recall, f1, fpr = _metrics_from_confusion(test_truth, predictions.to_numpy())
        breakdown = _per_injection_type_breakdown(test_truth, predictions, test_instances)

        n_test = max(len(test_injected), 1)
        detection_latency_ms = (score_end - score_start) / n_test * 1000.0
        execution_time_s = time.perf_counter() - start

        artifact_path = model_out_dir / f"{model_type.value}.pkl"
        with artifact_path.open("wb") as f:
            pickle.dump(
                {
                    "model_type": model_type.value,
                    "model": detector,
                    "feature_columns": feature_columns,
                    "calibrated_thresholds": {f"p{int(CALIBRATION_PERCENTILE)}": threshold},
                    "parameters": detector.parameters,
                    "train_medians": train_medians.to_dict(),
                },
                f,
            )

        results.append(
            BenchmarkResult(
                model_type=model_type,
                precision=precision,
                recall=recall,
                f1=f1,
                fpr=fpr,
                detection_latency_ms=detection_latency_ms,
                execution_time_s=execution_time_s,
                measurement_context=measurement_context,
                per_injection_type_breakdown=breakdown,
            )
        )

    selection = select_production_model(results)
    run_result = BenchmarkRunResult(benchmark_results=results, production_model_selection=selection)
    write_benchmark_run_result(run_result, out_dir)
    return run_result
