from datetime import datetime, timezone

import pandas as pd
import pytest

from app.baseline.data_health_baseline import compute_data_health_baseline
from app.quality.schemas import Band, ExpectationCheckResult, ExpectationType

NOW = datetime(2026, 8, 18, tzinfo=timezone.utc)


def _check(expectation_type, column_name, rate, check_id):
    return ExpectationCheckResult(
        check_id=check_id,
        suite_name="test_suite",
        column_name=column_name,
        expectation_type=expectation_type,
        computed_rate_or_count=rate,
        band=Band.PASS,
        threshold_used={},
        run_id="run-1",
        evaluated_at=NOW,
    )


def test_duplicate_rate_sourced_exactly_from_quality_results():
    df = pd.DataFrame({"PTNT_DSCHRG_STUS_CD": ["1", "1", "1"]})
    check_results = [
        _check(ExpectationType.DUPLICATE_RATE, None, 3.5, "c1"),
    ]
    health = compute_data_health_baseline(df, check_results)
    assert health.historical_duplicate_rate == pytest.approx(3.5)


def test_missing_rate_by_column_sourced_from_completeness_checks():
    df = pd.DataFrame({"PTNT_DSCHRG_STUS_CD": ["1", "1"]})
    check_results = [
        _check(ExpectationType.COMPLETENESS, "CLM_PMT_AMT", 1.2, "c1"),
        _check(ExpectationType.COMPLETENESS, "PTNT_DSCHRG_STUS_CD", 0.0, "c2"),
    ]
    health = compute_data_health_baseline(df, check_results)
    assert health.historical_missing_rate_by_column == {"CLM_PMT_AMT": 1.2, "PTNT_DSCHRG_STUS_CD": 0.0}


def test_status_distribution_reflects_real_value_counts():
    df = pd.DataFrame({"PTNT_DSCHRG_STUS_CD": ["1", "1", "1", "20"]})
    health = compute_data_health_baseline(df, check_results=[])
    assert health.categorical_distributions["PTNT_DSCHRG_STUS_CD"] == {"1": 3, "20": 1}


def test_no_duplicate_check_defaults_to_zero_not_omitted():
    df = pd.DataFrame({"PTNT_DSCHRG_STUS_CD": ["1"]})
    health = compute_data_health_baseline(df, check_results=[])
    assert health.historical_duplicate_rate == 0.0
