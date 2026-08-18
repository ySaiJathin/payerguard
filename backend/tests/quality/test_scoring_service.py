from datetime import datetime, timezone

import pandas as pd
import pytest

from app.quality.scoring_service import (
    QualityScoreConfigError,
    compute_composite_score,
    compute_file_level_checks,
)
from app.quality.schemas import Band, ExpectationCheckResult, ExpectationType

NOW = datetime(2026, 8, 18, tzinfo=timezone.utc)


def _check(expectation_type, band, check_id):
    return ExpectationCheckResult(
        check_id=check_id,
        suite_name="test_suite",
        column_name="COL",
        expectation_type=expectation_type,
        computed_rate_or_count=0.0,
        band=band,
        threshold_used={},
        run_id="run-1",
        evaluated_at=NOW,
    )


def test_composite_score_matches_hand_computed_weighted_proportion():
    checks = [
        _check(ExpectationType.COMPLETENESS, Band.PASS, "c1"),
        _check(ExpectationType.COMPLETENESS, Band.CRITICAL, "c2"),
        _check(ExpectationType.VALIDITY, Band.WARNING, "c3"),
    ]
    # completeness avg = (100 + 0) / 2 = 50; validity avg = 50
    # equal weights (1/2 each) -> score = 0.5*50 + 0.5*50 = 50
    result = compute_composite_score(checks, run_id="run-1", batch_source="src.csv")
    assert result.composite_score == pytest.approx(50.0)


def test_composite_score_with_explicit_weights():
    checks = [
        _check(ExpectationType.COMPLETENESS, Band.PASS, "c1"),
        _check(ExpectationType.VALIDITY, Band.CRITICAL, "c2"),
    ]
    weights = {"completeness": 0.9, "validity": 0.1}
    result = compute_composite_score(checks, weights, run_id="run-1", batch_source="src.csv")
    # 0.9*100 + 0.1*0 = 90
    assert result.composite_score == pytest.approx(90.0)
    assert result.weights_used == weights


def test_contributing_check_ids_traceable_to_input():
    checks = [
        _check(ExpectationType.COMPLETENESS, Band.PASS, "c1"),
        _check(ExpectationType.VALIDITY, Band.WARNING, "c2"),
    ]
    result = compute_composite_score(checks, run_id="run-1", batch_source="src.csv")
    assert set(result.contributing_check_ids) == {"c1", "c2"}


def test_weights_not_summing_to_one_raises_config_error():
    checks = [_check(ExpectationType.COMPLETENESS, Band.PASS, "c1")]
    with pytest.raises(QualityScoreConfigError):
        compute_composite_score(checks, {"completeness": 0.5}, run_id="run-1", batch_source="src.csv")


def test_negative_weight_raises_config_error():
    checks = [
        _check(ExpectationType.COMPLETENESS, Band.PASS, "c1"),
        _check(ExpectationType.VALIDITY, Band.PASS, "c2"),
    ]
    with pytest.raises(QualityScoreConfigError):
        compute_composite_score(
            checks, {"completeness": 1.5, "validity": -0.5}, run_id="run-1", batch_source="src.csv"
        )


def test_empty_check_results_raises_config_error():
    with pytest.raises(QualityScoreConfigError):
        compute_composite_score([], run_id="run-1", batch_source="src.csv")


def test_score_is_recomputable_bit_for_bit_from_persisted_inputs():
    checks = [
        _check(ExpectationType.COMPLETENESS, Band.WARNING, "c1"),
        _check(ExpectationType.RANGE, Band.PASS, "c2"),
        _check(ExpectationType.CODE_SET, Band.CRITICAL, "c3"),
    ]
    weights = {"completeness": 0.5, "range": 0.3, "code_set": 0.2}
    first = compute_composite_score(checks, weights, run_id="run-1", batch_source="src.csv")
    second = compute_composite_score(checks, weights, run_id="run-2", batch_source="src.csv")
    assert first.composite_score == second.composite_score


def test_file_level_checks_zero_missing_zero_duplicates():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    checks = compute_file_level_checks(df, run_id="run-1")
    by_type = {c.expectation_type: c for c in checks}
    assert by_type[ExpectationType.MISSING_RATE].computed_rate_or_count == pytest.approx(0.0)
    assert by_type[ExpectationType.MISSING_RATE].band == Band.PASS
    assert by_type[ExpectationType.DUPLICATE_RATE].computed_rate_or_count == pytest.approx(0.0)
    assert by_type[ExpectationType.DUPLICATE_RATE].band == Band.PASS


def test_file_level_missing_rate_formula():
    # 2 missing cells out of 6 total cells = 33.33%
    df = pd.DataFrame({"a": [1, None, 3], "b": [None, 5, 6]})
    checks = compute_file_level_checks(df, run_id="run-1")
    missing_check = next(c for c in checks if c.expectation_type == ExpectationType.MISSING_RATE)
    assert missing_check.computed_rate_or_count == pytest.approx(2 / 6 * 100)
    assert missing_check.band == Band.CRITICAL


def test_file_level_duplicate_rate_formula():
    df = pd.DataFrame({"a": [1, 1, 2], "b": [4, 4, 5]})
    checks = compute_file_level_checks(df, run_id="run-1")
    dup_check = next(c for c in checks if c.expectation_type == ExpectationType.DUPLICATE_RATE)
    assert dup_check.computed_rate_or_count == pytest.approx(1 / 3 * 100)
    assert dup_check.band == Band.CRITICAL
