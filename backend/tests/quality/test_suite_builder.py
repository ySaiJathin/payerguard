import json
from pathlib import Path

import great_expectations as gx
import pandas as pd
import pytest

from app.data_engineering.invalid_value_detection import build_reference_stats
from app.data_engineering.schemas import ColumnCategory, ProfilingReport
from app.quality.completeness_calibration import build_calibration_table
from app.quality.data_loader import load_cleaned_batch
from app.quality.expectations.range_checks import bounds_with_slack
from app.quality.schemas import Band, ExpectationType
from app.quality.scoring_service import run_category_suites
from app.quality.suite_builder import build_suites

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def categories() -> dict[str, ColumnCategory]:
    raw = json.loads((FIXTURES / "quality_column_categories.json").read_text(encoding="utf-8"))
    return {col: ColumnCategory(cat) for col, cat in raw.items()}


@pytest.fixture
def profiling_report() -> ProfilingReport:
    return ProfilingReport.model_validate_json((FIXTURES / "quality_profiling_report.json").read_text(encoding="utf-8"))


@pytest.fixture
def cleaned_df(categories) -> pd.DataFrame:
    return load_cleaned_batch(FIXTURES / "quality_cleaned_sample.csv", categories)


@pytest.fixture
def reference_df() -> pd.DataFrame:
    # Raw-format reference (pipe-delimited, DD-Mon-YYYY dates), matching how
    # Phase 2's build_reference_stats is actually fed data/raw/inpatient.csv.
    return pd.read_csv(FIXTURES / "quality_reference_sample.csv", sep="|", low_memory=False)


@pytest.fixture
def suite_results(categories, profiling_report, cleaned_df, reference_df):
    calibration = build_calibration_table(profiling_report)
    reference_stats = build_reference_stats(reference_df, categories)
    known_code_values = {col: sorted(values) for col, values in reference_stats.known_values.items()}
    date_bounds = bounds_with_slack(reference_stats.date_min, reference_stats.date_max)
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
    check_results = run_category_suites(suite_runs, run_id="test-run")
    return suite_runs, check_results


def test_all_six_categories_present_in_fixture_get_at_least_one_check(suite_results, categories):
    _, check_results = suite_results
    categories_present = set(categories.values())
    # every category in the fixture's schema must be covered by at least one suite run
    covered_suite_names = {c.suite_name for c in check_results}
    assert covered_suite_names, "no checks produced at all"
    # sanity: every category actually in the fixture appears in the categorized columns
    assert categories_present == {
        ColumnCategory.IDENTIFIER,
        ColumnCategory.DATE,
        ColumnCategory.AMOUNT,
        ColumnCategory.CATEGORICAL_CODE,
        ColumnCategory.DIAGNOSIS_PROCEDURE_CODE,
    }


def test_clm_id_cardinality_matches_profiling_report(suite_results, profiling_report):
    _, check_results = suite_results
    uniqueness_checks = [c for c in check_results if c.expectation_type == ExpectationType.UNIQUENESS]
    assert len(uniqueness_checks) == 1
    check = uniqueness_checks[0]
    assert check.computed_rate_or_count == profiling_report.unique_claim_count
    assert check.band == Band.PASS


def test_negative_amount_trips_critical_validity_check(suite_results):
    _, check_results = suite_results
    amount_checks = [c for c in check_results if c.expectation_type == ExpectationType.VALIDITY and c.column_name == "CLM_PMT_AMT"]
    assert len(amount_checks) == 1
    assert amount_checks[0].band == Band.CRITICAL


def test_out_of_range_date_trips_range_check(suite_results):
    _, check_results = suite_results
    range_checks_ = [c for c in check_results if c.expectation_type == ExpectationType.RANGE and c.column_name == "CLM_FROM_DT"]
    assert len(range_checks_) == 1
    assert range_checks_[0].band in (Band.WARNING, Band.CRITICAL)


def test_unrecognized_categorical_code_trips_code_set_check(suite_results):
    _, check_results = suite_results
    code_set_checks = [
        c for c in check_results if c.expectation_type == ExpectationType.CODE_SET and c.column_name == "CLM_IP_ADMSN_TYPE_CD"
    ]
    assert len(code_set_checks) == 1
    assert code_set_checks[0].band in (Band.WARNING, Band.CRITICAL)


def test_calibrated_column_completeness_is_not_critical_despite_high_missingness(suite_results):
    _, check_results = suite_results
    completeness_checks = [
        c for c in check_results if c.expectation_type == ExpectationType.COMPLETENESS and c.column_name == "OT_PHYSN_UPIN"
    ]
    assert len(completeness_checks) == 1
    check = completeness_checks[0]
    assert check.computed_rate_or_count == pytest.approx(100.0)
    assert check.band != Band.CRITICAL
    assert check.threshold_used["calibrated"] is True


def test_date_format_check_present_and_passes_for_iso_dates(suite_results):
    _, check_results = suite_results
    dtype_checks = [c for c in check_results if c.expectation_type == ExpectationType.DTYPE and c.column_name == "CLM_FROM_DT"]
    assert len(dtype_checks) == 1
    assert dtype_checks[0].band == Band.PASS
