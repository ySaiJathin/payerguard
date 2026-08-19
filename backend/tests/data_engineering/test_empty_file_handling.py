"""Data category / "empty files" (spec 015 FR-001, closing a gap found
while building docs/testing/phase15_coverage_map.md).

MVP_CONTEXT.md Phase 15 names "empty files" among the Data-category
scenarios. Building the coverage map surfaced that no existing test
actually covered one: Phase 1 covers a *missing* file
(`test_profiling_service.py::test_missing_source_file_fails_fast`) and a
wrong-shaped one (`test_wrong_column_count_fails_fast`), and Phase 3
covers empty *check results*
(`tests/quality/test_scoring_service.py::test_empty_check_results_raises_config_error`)
-- but an empty or header-only *source file* went untested.

The two empty cases behave differently, and both behaviours are pinned
here as the documented contract rather than left to chance:

- A **zero-byte file** has no header row to parse, so it cannot satisfy
  the column-count and required-column checks. It fails fast with
  `ProfilingError`, consistent with how every other structurally invalid
  input is handled.
- A **header-only file** is structurally valid -- correct delimiter,
  correct columns, zero data rows -- so it is accepted and profiles to
  `total_rows == 0`. This is deliberately *not* an error: a batch with no
  claims is a legitimate (if unusual) input, and rejecting it would force
  callers to special-case a valid state. Constitution Principle II also
  applies: zero rows must report as zero, never as a fabricated or
  defaulted count.
"""

import pytest

from app.data_engineering.profiling_service import (
    ProfilingError,
    generate_profiling_report,
    load_source_csv,
)

HEADER = (
    "BENE_ID|CLM_ID|CLM_FROM_DT|CLM_THRU_DT|CLM_PMT_AMT|"
    "CLM_IP_ADMSN_TYPE_CD|PRNCPAL_DGNS_CD|OT_PHYSN_UPIN|CLM_LINE_NUM"
)
COLUMN_COUNT = 9


def test_zero_byte_file_fails_fast(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")

    with pytest.raises(ProfilingError):
        load_source_csv(empty, expected_column_count=COLUMN_COUNT)


def test_zero_byte_file_fails_fast_through_the_report_entry_point(tmp_path):
    """The same guarantee at the public entry point callers actually use
    -- a fail-fast that only holds on the internal loader would leave the
    real path exposed."""
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")

    with pytest.raises(ProfilingError):
        generate_profiling_report(empty, expected_column_count=COLUMN_COUNT)


def test_whitespace_only_file_fails_fast(tmp_path):
    """A file containing only blank lines has no parseable header either
    -- it must not be mistaken for a valid empty batch."""
    blank = tmp_path / "blank.csv"
    blank.write_text("\n\n\n", encoding="utf-8")

    with pytest.raises(ProfilingError):
        load_source_csv(blank, expected_column_count=COLUMN_COUNT)


def test_header_only_file_is_accepted_with_zero_rows(tmp_path):
    """A structurally valid batch that simply contains no claims."""
    header_only = tmp_path / "header_only.csv"
    header_only.write_text(HEADER + "\n", encoding="utf-8")

    df = load_source_csv(header_only, expected_column_count=COLUMN_COUNT)

    assert len(df) == 0
    assert list(df.columns) == HEADER.split("|")


def test_header_only_file_profiles_to_zero_rows_not_a_fabricated_count(tmp_path):
    """Constitution Principle II: an empty batch reports genuine zeros,
    never a defaulted or invented figure."""
    header_only = tmp_path / "header_only.csv"
    header_only.write_text(HEADER + "\n", encoding="utf-8")

    report = generate_profiling_report(header_only, expected_column_count=COLUMN_COUNT)

    assert report.total_rows == 0
    assert report.duplicate_row_count == 0
    # Every column still appears in the report -- an empty batch must not
    # silently drop columns from the profile (Phase 1 SC-002).
    assert len(report.columns) == COLUMN_COUNT


def test_header_only_file_with_wrong_columns_still_fails_fast(tmp_path):
    """Being empty must not exempt a file from the schema check -- an
    empty batch with the wrong shape is still a broken input."""
    wrong = tmp_path / "wrong_header.csv"
    wrong.write_text("BENE_ID|CLM_ID\n", encoding="utf-8")

    with pytest.raises(ProfilingError):
        load_source_csv(wrong, expected_column_count=COLUMN_COUNT)
