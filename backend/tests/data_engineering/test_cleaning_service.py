import json
from pathlib import Path

import pytest

from app.data_engineering.categorization import categorize
from app.data_engineering.cleaning_service import CleaningError, SchemaValidationError, run_cleaning
from app.data_engineering.dtype_conversion import CategoriesUnavailableError
from app.data_engineering.quality_issue_log import read_cleaning_run_summary, read_quality_issues
from app.data_engineering.schemas import QualityIssue

CLEAN_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "inpatient_sample.csv"
DIRTY_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "inpatient_dirty_sample.csv"
FIXTURE_COLUMNS = [
    "BENE_ID",
    "CLM_ID",
    "CLM_FROM_DT",
    "CLM_THRU_DT",
    "CLM_PMT_AMT",
    "CLM_IP_ADMSN_TYPE_CD",
    "PRNCPAL_DGNS_CD",
    "OT_PHYSN_UPIN",
    "CLM_LINE_NUM",
]


def _write_categories(tmp_path: Path) -> Path:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    categories = {col: categorize(col).value for col in FIXTURE_COLUMNS}
    (reports_dir / "column_categories.json").write_text(json.dumps(categories), encoding="utf-8")
    return reports_dir


def _run(tmp_path: Path, fixture: Path):
    categories_dir = _write_categories(tmp_path)
    return run_cleaning(
        source_path=fixture,
        categories_dir=categories_dir,
        reference_path=fixture,
        output_dir=tmp_path / "cleaned",
        reports_out_dir=categories_dir,
    )


def test_missing_categories_raises_categories_unavailable(tmp_path):
    with pytest.raises(CategoriesUnavailableError):
        run_cleaning(
            source_path=CLEAN_FIXTURE,
            categories_dir=tmp_path / "empty",
            reference_path=CLEAN_FIXTURE,
            output_dir=tmp_path / "cleaned",
            reports_out_dir=tmp_path / "reports",
        )


def test_schema_mismatch_raises_schema_validation_error(tmp_path):
    categories_dir = _write_categories(tmp_path)
    bad_file = tmp_path / "wrong_columns.csv"
    # Has the two columns load_source_csv always requires (CLM_ID/BENE_ID),
    # but not the schema this feature validates against (categories.json).
    bad_file.write_text("CLM_ID|BENE_ID|UNEXPECTED_COL\n1|2|3\n", encoding="utf-8")

    with pytest.raises(SchemaValidationError) as exc_info:
        run_cleaning(
            source_path=bad_file,
            categories_dir=categories_dir,
            reference_path=bad_file,
            output_dir=tmp_path / "cleaned",
            reports_out_dir=categories_dir,
        )
    assert exc_info.value.result.passed is False


def test_amount_and_date_columns_get_correct_dtypes(tmp_path):
    summary = _run(tmp_path, CLEAN_FIXTURE)

    import pandas as pd

    cleaned = pd.read_csv(summary.output_file)
    assert pd.api.types.is_numeric_dtype(cleaned["CLM_PMT_AMT"])
    # CSV round-tripping can't preserve a string-vs-int distinction for a
    # digit-only identifier -- what matters is the value survives intact.
    assert set(cleaned["CLM_ID"].astype(str)) == {"1001", "1002", "1003", "1004", "1005"}
    import re

    iso = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    assert cleaned["CLM_FROM_DT"].dropna().map(lambda v: bool(iso.match(str(v)))).all()


def test_audit_trail_records_date_reformatting(tmp_path):
    _run(tmp_path, CLEAN_FIXTURE)
    records = read_quality_issues(tmp_path / "reports")

    date_records = [r for r in records if r.quality_issue == QualityIssue.DATE_FORMAT_STANDARDIZED]
    assert any(r.original_value == "01-Apr-2015" and r.cleaned_value == "2015-04-01" for r in date_records)


def test_no_record_for_unchanged_categorical_cell(tmp_path):
    _run(tmp_path, CLEAN_FIXTURE)
    records = read_quality_issues(tmp_path / "reports")

    # CLM_IP_ADMSN_TYPE_CD values in the clean fixture are all valid/known and
    # never change representation -- no record should exist for that column.
    assert not [r for r in records if r.column_name == "CLM_IP_ADMSN_TYPE_CD"]


def test_missing_value_gets_exactly_one_record_per_missing_cell(tmp_path):
    summary = _run(tmp_path, CLEAN_FIXTURE)
    records = read_quality_issues(tmp_path / "reports")

    missing_records = [r for r in records if r.quality_issue == QualityIssue.MISSING_VALUE]
    # OT_PHYSN_UPIN is empty in every row of the clean fixture (6 rows).
    assert len([r for r in missing_records if r.column_name == "OT_PHYSN_UPIN"]) == summary.rows_out


def test_record_count_matches_changed_or_missing_cells(tmp_path):
    summary = _run(tmp_path, DIRTY_FIXTURE)
    records = read_quality_issues(tmp_path / "reports")

    # Every record in the trail corresponds to an actual change, a missing
    # cell, or a flagged row/value -- never an unconditional per-cell copy.
    assert len(records) == summary.quality_issue_count
    assert len(records) > 0


def test_cleaning_run_summary_persisted_and_readable(tmp_path):
    summary = _run(tmp_path, CLEAN_FIXTURE)
    reloaded = read_cleaning_run_summary(tmp_path / "reports")

    assert reloaded is not None
    assert reloaded.rows_in == summary.rows_in
    assert reloaded.output_file == summary.output_file
