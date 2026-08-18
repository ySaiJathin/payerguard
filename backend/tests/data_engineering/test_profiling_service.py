from pathlib import Path

import pandas as pd
import pytest

from app.data_engineering.profiling_service import ProfilingError, generate_profiling_report

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "inpatient_sample.csv"
FIXTURE_COLUMN_COUNT = 9  # backend/tests/fixtures/inpatient_sample.csv has 9 columns


def test_file_level_stats_match_fixture():
    report = generate_profiling_report(FIXTURE, expected_column_count=FIXTURE_COLUMN_COUNT)

    assert report.total_rows == 6
    assert report.total_columns == 9
    assert report.unique_claim_count == 5
    assert report.unique_beneficiary_count == 5
    assert report.duplicate_row_count == 0
    assert report.lines_per_claim_mean == pytest.approx(1.2)
    assert report.lines_per_claim_median == pytest.approx(1.0)
    assert len(report.columns) == report.total_columns


def test_missing_column_reported_as_100_percent_missing():
    report = generate_profiling_report(FIXTURE, expected_column_count=FIXTURE_COLUMN_COUNT)
    ot_physn_upin = next(c for c in report.columns if c.column_name == "OT_PHYSN_UPIN")

    assert ot_physn_upin.missing_count == 6
    assert ot_physn_upin.missing_pct == pytest.approx(100.0)
    assert ot_physn_upin.cardinality == 0


def test_numeric_column_gets_distribution_stats():
    report = generate_profiling_report(FIXTURE, expected_column_count=FIXTURE_COLUMN_COUNT)
    amt = next(c for c in report.columns if c.column_name == "CLM_PMT_AMT")

    assert amt.numeric_stats is not None
    assert amt.numeric_stats.min == pytest.approx(300.00)
    assert amt.numeric_stats.max == pytest.approx(1200.50)
    assert amt.categorical_top_values is None


def test_categorical_column_gets_top_value_frequencies():
    report = generate_profiling_report(FIXTURE, expected_column_count=FIXTURE_COLUMN_COUNT)
    admsn_type = next(c for c in report.columns if c.column_name == "CLM_IP_ADMSN_TYPE_CD")

    assert admsn_type.categorical_top_values is not None
    assert admsn_type.numeric_stats is None
    values = {v.value for v in admsn_type.categorical_top_values}
    assert values == {"1", "2", "3"}


def test_date_column_reports_format_and_min_max_without_reformatting():
    report = generate_profiling_report(FIXTURE, expected_column_count=FIXTURE_COLUMN_COUNT)
    from_dt = next(c for c in report.columns if c.column_name == "CLM_FROM_DT")

    assert from_dt.date_format_observed == "DD-Mon-YYYY"
    # Chronologically earliest/latest, not lexicographically -- and reported
    # as the original raw string, not a reformatted/parsed value.
    assert from_dt.date_min == "01-Apr-2015"
    assert from_dt.date_max == "22-Feb-2022"


def test_wrong_column_count_fails_fast(tmp_path):
    bad_file = tmp_path / "comma_delimited.csv"
    bad_file.write_text("BENE_ID,CLM_ID\n1,2\n", encoding="utf-8")

    with pytest.raises(ProfilingError):
        generate_profiling_report(bad_file)


def test_missing_source_file_fails_fast(tmp_path):
    missing = tmp_path / "does_not_exist.csv"

    with pytest.raises(ProfilingError):
        generate_profiling_report(missing)


def test_full_duplicate_row_is_detected(tmp_path):
    duped = tmp_path / "duped.csv"
    original = pd.read_csv(FIXTURE, sep="|")
    duped_df = pd.concat([original, original.iloc[[0]]], ignore_index=True)
    duped_df.to_csv(duped, sep="|", index=False)

    report = generate_profiling_report(duped, expected_column_count=FIXTURE_COLUMN_COUNT)
    assert report.duplicate_row_count == 1
