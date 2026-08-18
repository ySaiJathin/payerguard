"""Composite quality score (FR-010) and file-level MissingRate/DuplicateRate
checks (FR-009), computed with the exact formulas in MVP_CONTEXT.md 3.1.

`compute_composite_score` is a pure function of its inputs -- no hidden
state, no I/O -- so the composite score is always exactly recomputable from
a persisted `ExpectationCheckResult` list (spec SC-001).
"""

import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import great_expectations as gx
import pandas as pd

from app.data_engineering.cleaning_service import CLEANED_OUTPUT_FILENAME
from app.data_engineering.dtype_conversion import load_column_categories
from app.data_engineering.invalid_value_detection import build_reference_stats
from app.data_engineering.paths import cleaned_dir, raw_inpatient_csv
from app.data_engineering.profiling_service import load_source_csv
from app.data_engineering.report_writer import read_profiling_report
from app.quality.bands import classify_duplicate_rate, classify_missing_rate
from app.quality.completeness_calibration import build_calibration_table
from app.quality.data_loader import QualityInputUnavailableError, load_cleaned_batch
from app.quality.expectations.freshness import evaluate_freshness
from app.quality.expectations.range_checks import bounds_with_slack
from app.quality.quality_results_log import write_quality_results
from app.quality.schemas import Band, ExpectationCheckResult, ExpectationType, QualityScoreResult
from app.quality.suite_builder import SuiteRun, build_suites

__all__ = [
    "QualityScoreConfigError",
    "QualityInputUnavailableError",
    "compute_file_level_checks",
    "compute_composite_score",
    "run_category_suites",
    "run_validation",
]

FILE_LEVEL_SUITE_NAME = "file_level_suite"

_BAND_SCORE = {Band.PASS: 100.0, Band.WARNING: 50.0, Band.CRITICAL: 0.0}


class QualityScoreConfigError(ValueError):
    """Raised when a weight configuration doesn't form a valid probability
    distribution over the expectation types actually present (Edge Cases)."""


def compute_file_level_checks(
    df: pd.DataFrame,
    run_id: str,
    evaluated_at: datetime | None = None,
) -> list[ExpectationCheckResult]:
    """MissingRate = (missing cells / total cells) x 100 across the whole
    batch; DuplicateRate = (duplicate rows / total rows) x 100 on the
    cleaned batch itself (expected 0 -- Phase 2 already excludes exact
    duplicates, but this re-derives it rather than assuming so)."""
    evaluated_at = evaluated_at or datetime.now(timezone.utc)

    total_cells = df.shape[0] * df.shape[1]
    missing_cells = int(df.isna().sum().sum())
    missing_rate_pct = (missing_cells / total_cells * 100) if total_cells else 0.0

    total_rows = len(df)
    duplicate_rows = int(df.duplicated(keep="first").sum())
    duplicate_rate_pct = (duplicate_rows / total_rows * 100) if total_rows else 0.0

    return [
        ExpectationCheckResult(
            check_id=str(uuid4()),
            suite_name=FILE_LEVEL_SUITE_NAME,
            column_name=None,
            expectation_type=ExpectationType.MISSING_RATE,
            computed_rate_or_count=missing_rate_pct,
            band=classify_missing_rate(missing_rate_pct),
            threshold_used={"pass_lt": 2, "warning_lt": 5, "unit": "pct"},
            run_id=run_id,
            evaluated_at=evaluated_at,
        ),
        ExpectationCheckResult(
            check_id=str(uuid4()),
            suite_name=FILE_LEVEL_SUITE_NAME,
            column_name=None,
            expectation_type=ExpectationType.DUPLICATE_RATE,
            computed_rate_or_count=duplicate_rate_pct,
            band=classify_duplicate_rate(duplicate_rate_pct),
            threshold_used={"pass_eq": 0, "warning_lte": 1, "unit": "pct"},
            run_id=run_id,
            evaluated_at=evaluated_at,
        ),
    ]


def compute_composite_score(
    check_results: list[ExpectationCheckResult],
    weights: dict[str, float] | None = None,
    *,
    run_id: str,
    batch_source: str,
    generated_at: datetime | None = None,
) -> QualityScoreResult:
    """score = sum(type_weight * type_pass_proportion) over every
    expectation_type present in check_results, where each check's PASS/
    WARNING/CRITICAL band contributes 100/50/0 to its type's average.

    `weights` defaults to equal-weighting across whichever expectation
    types are actually present. If provided explicitly, it must assign a
    non-negative weight to every type present and those weights must sum
    to 1.0 (a configuration error is raised otherwise, per Edge Cases --
    the score is never silently clamped from a broken configuration).
    """
    if not check_results:
        raise QualityScoreConfigError("Cannot compute a composite score from zero check results.")

    by_type: dict[str, list[ExpectationCheckResult]] = defaultdict(list)
    for check in check_results:
        by_type[check.expectation_type.value].append(check)
    types_present = sorted(by_type.keys())

    if weights is None:
        weights = {t: 1.0 / len(types_present) for t in types_present}
    else:
        missing_types = [t for t in types_present if t not in weights]
        if missing_types:
            raise QualityScoreConfigError(f"weights missing an entry for expectation type(s): {missing_types}")
        if any(weights[t] < 0 for t in types_present):
            raise QualityScoreConfigError("weights must be non-negative.")
        total_weight = sum(weights[t] for t in types_present)
        if not math.isclose(total_weight, 1.0, rel_tol=1e-6, abs_tol=1e-6):
            raise QualityScoreConfigError(
                f"weights for present expectation types sum to {total_weight}, expected 1.0"
            )

    score = 0.0
    for expectation_type in types_present:
        checks = by_type[expectation_type]
        avg = sum(_BAND_SCORE[c.band] for c in checks) / len(checks)
        score += weights[expectation_type] * avg
    score = max(0.0, min(100.0, score))

    return QualityScoreResult(
        run_id=run_id,
        batch_source=batch_source,
        composite_score=score,
        weights_used=weights,
        contributing_check_ids=[c.check_id for c in check_results],
        generated_at=generated_at or datetime.now(timezone.utc),
    )


def run_category_suites(
    suite_runs: list[SuiteRun],
    run_id: str,
    evaluated_at: datetime | None = None,
) -> list[ExpectationCheckResult]:
    """Executes each category's suite exactly once against its batch
    (FR-001/FR-002/FR-003/FR-005/FR-006), collecting results through
    every extractor registered for that suite run."""
    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    records: list[ExpectationCheckResult] = []
    for suite_run in suite_runs:
        validation_result = suite_run.batch.validate(suite_run.suite)
        for extractor in suite_run.extractors:
            records.extend(extractor(validation_result, run_id=run_id, evaluated_at=evaluated_at))
    return records


def run_validation(weights: dict[str, float] | None = None) -> QualityScoreResult:
    """Full orchestrator (FR-001 through FR-011): loads Phase 1/2 outputs,
    builds and executes the category suites, computes file-level
    MissingRate/DuplicateRate and freshness, folds everything into the
    composite score, and persists both the score and every contributing
    check result.

    Raises `QualityInputUnavailableError` if Phase 2's cleaned batch (or
    Phase 1's profiling report / column categories) hasn't been produced
    yet (FR-012).
    """
    categories = load_column_categories()  # raises CategoriesUnavailableError if Phase 1 hasn't run

    profiling_report = read_profiling_report()
    if profiling_report is None:
        raise QualityInputUnavailableError(
            "No profiling report found -- run POST /data-engineering/profile (Phase 1) first."
        )

    batch_path = cleaned_dir() / CLEANED_OUTPUT_FILENAME
    cleaned_df = load_cleaned_batch(batch_path, categories)  # raises QualityInputUnavailableError

    raw_df = load_source_csv(raw_inpatient_csv(), expected_column_count=None)
    reference_stats = build_reference_stats(raw_df, categories)
    known_code_values = {col: sorted(values) for col, values in reference_stats.known_values.items()}
    date_bounds = bounds_with_slack(reference_stats.date_min, reference_stats.date_max)

    calibration = build_calibration_table(profiling_report)

    context = gx.get_context(mode="ephemeral")
    suite_runs = build_suites(
        context,
        cleaned_df,
        categories,
        calibration,
        known_code_values,
        expected_unique_claim_count=profiling_report.unique_claim_count,
        reference_date_bounds=date_bounds,
    )

    run_id = str(uuid4())
    evaluated_at = datetime.now(timezone.utc)

    check_results = run_category_suites(suite_runs, run_id, evaluated_at)
    check_results += compute_file_level_checks(cleaned_df, run_id, evaluated_at)
    check_results.append(evaluate_freshness(batch_path, run_id, evaluated_at=evaluated_at))

    score_result = compute_composite_score(
        check_results, weights, run_id=run_id, batch_source=str(batch_path), generated_at=evaluated_at
    )
    write_quality_results(score_result, check_results)
    return score_result
