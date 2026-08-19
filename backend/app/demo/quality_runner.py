"""Great Expectations validation of an arbitrary batch (demo Task 2a).

Phase 3's `run_validation()` is hardwired to `data/cleaned/inpatient_cleaned.csv`.
The demo needs the *same* suites run against whichever batch is currently
active, so this module reuses Phase 3's own suite builder, extractors,
file-level checks, freshness check and composite-score formula -- none of
that logic is reimplemented here -- and only swaps out where the DataFrame
comes from.

Coverage is therefore identical to the production suite: completeness, code
set, range, dtype (date-format), validity, uniqueness, missing rate,
duplicate rate and freshness. Every band and the composite 0-100 score come
from real GX validation results; the run id and timestamp are minted per
run and persisted through Phase 3's own `quality_results_log`, which keeps
the dashboard's "one run retained as a snapshot" behaviour intact.
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import great_expectations as gx
import pandas as pd

from app.data_engineering.dtype_conversion import load_column_categories
from app.demo.column_profile import load_column_profile
from app.demo.generator import CLAIM_FROM_COLUMN
from app.quality.completeness_calibration import build_calibration_table
from app.quality.expectations.freshness import evaluate_freshness
from app.quality.expectations.range_checks import bounds_with_slack
from app.quality.quality_results_log import write_quality_results
from app.quality.schemas import Band, ExpectationCheckResult, QualityScoreResult
from app.quality.scoring_service import (
    compute_composite_score,
    compute_file_level_checks,
    run_category_suites,
)
from app.quality.suite_builder import build_suites
from app.data_engineering.report_writer import read_profiling_report

BAND_ORDER = [Band.PASS, Band.WARNING, Band.CRITICAL]


def _known_code_values(profile: dict) -> dict[str, list[str]]:
    """The reference code universe, learned once from the real cleaned
    extract (`column_profile.py`) rather than from the batch under test --
    a batch cannot define the code set it is being validated against."""
    return {
        entry["name"]: sorted(entry["pool"]["values"])
        for entry in profile["columns"]
        if entry.get("pool", {}).get("values")
    }


def band_counts(check_results: list[ExpectationCheckResult]) -> dict[str, int]:
    counts = {band.value: 0 for band in BAND_ORDER}
    for check in check_results:
        counts[check.band.value] += 1
    return counts


def band_counts_by_type(check_results: list[ExpectationCheckResult]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for check in check_results:
        bucket = out.setdefault(check.expectation_type.value, {b.value: 0 for b in BAND_ORDER})
        bucket[check.band.value] += 1
    return out


def validate_batch(
    df: pd.DataFrame,
    batch_path: Path,
    expected_unique_claim_count: int | None = None,
    persist: bool = True,
) -> tuple[QualityScoreResult, list[ExpectationCheckResult]]:
    """Runs the full expectation suite against `df` and returns the real
    composite score plus every contributing check result."""
    categories = load_column_categories()
    profile = load_column_profile()

    profiling_report = read_profiling_report()
    calibration = build_calibration_table(profiling_report) if profiling_report is not None else {}

    dates = pd.to_datetime(df[CLAIM_FROM_COLUMN], errors="coerce")
    date_bounds = bounds_with_slack(
        dates.min().date() if dates.notna().any() else None,
        dates.max().date() if dates.notna().any() else None,
    )

    if expected_unique_claim_count is None:
        expected_unique_claim_count = int(df["CLM_ID"].nunique())

    context = gx.get_context(mode="ephemeral")
    suite_runs = build_suites(
        context,
        df,
        categories,
        calibration,
        _known_code_values(profile),
        expected_unique_claim_count=expected_unique_claim_count,
        reference_date_bounds=date_bounds,
    )

    run_id = str(uuid4())
    evaluated_at = datetime.now(timezone.utc)

    check_results = run_category_suites(suite_runs, run_id, evaluated_at)
    check_results += compute_file_level_checks(df, run_id, evaluated_at)
    check_results.append(evaluate_freshness(batch_path, run_id, evaluated_at=evaluated_at))

    score_result = compute_composite_score(
        check_results,
        weights=None,
        run_id=run_id,
        batch_source=str(batch_path),
        generated_at=evaluated_at,
    )

    if persist:
        write_quality_results(score_result, check_results)

    return score_result, check_results
