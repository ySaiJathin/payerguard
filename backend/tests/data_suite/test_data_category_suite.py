"""Consolidated Data-category suite (spec 015 FR-006, SC-005).

MVP_CONTEXT.md Phase 15's Data category names five scenarios -- missing
values, duplicates, invalid types/values/dates, missing columns, empty
files -- whose coverage is spread across Phases 1, 2, and 3's separate
test directories. This module makes "run the data-quality tests" one
discoverable command:

    pytest backend/tests/data_suite/

**This file imports test functions; it does not reimplement them.** Every
name below is the *same function object* pytest would collect from its
original module, re-exported here so it is collected under this suite too.
That is what FR-009/SC-005 require: zero duplicated test logic. A
regression in any referenced test therefore fails here as well -- this
suite cannot drift out of sync with, or silently mask, the tests it
aggregates, because there is no second copy to drift.

Consequences worth knowing:

- These tests run twice in a full-suite run (once under their home
  directory, once here). They are fast and side-effect-free -- each uses
  `tmp_path` or a read-only fixture -- so the duplication costs runtime,
  not correctness. Deduplicating via a pytest marker was considered and
  rejected: it would make the consolidated command depend on flags the
  user has to remember, defeating the discoverability this exists for.
- Adding a Data-category test to Phase 1/2/3 does not automatically
  appear here. `test_every_referenced_module_is_fully_represented` below
  guards that gap: it fails when a referenced module gains a test this
  file has not re-exported, so the omission surfaces immediately instead
  of quietly narrowing the suite.
"""

import inspect

# --- Scenario: missing values (Phase 2 SC-005) -------------------------
from tests.data_engineering import test_cleaning_service as _cleaning
from tests.data_engineering.test_cleaning_service import (
    test_amount_and_date_columns_get_correct_dtypes,
    test_audit_trail_records_date_reformatting,
    test_cleaning_run_summary_persisted_and_readable,
    test_missing_categories_raises_categories_unavailable,
    test_missing_value_gets_exactly_one_record_per_missing_cell,
    test_no_record_for_unchanged_categorical_cell,
    test_record_count_matches_changed_or_missing_cells,
    # --- Scenario: missing columns (Phase 2 schema gate) ---------------
    test_schema_mismatch_raises_schema_validation_error,
)

# --- Scenario: duplicates (Phase 1 SC-003) -----------------------------
from tests.data_engineering import test_duplicate_detection as _duplicates
from tests.data_engineering.test_duplicate_detection import (
    test_exact_duplicate_excluded_and_flagged,
    test_no_row_physically_deleted_from_source_file,
    test_real_file_has_zero_duplicates,
)

# --- Scenario: empty files (spec 015, gap closed by this feature) ------
from tests.data_engineering import test_empty_file_handling as _empty
from tests.data_engineering.test_empty_file_handling import (
    test_header_only_file_is_accepted_with_zero_rows,
    test_header_only_file_profiles_to_zero_rows_not_a_fabricated_count,
    test_header_only_file_with_wrong_columns_still_fails_fast,
    test_whitespace_only_file_fails_fast,
    test_zero_byte_file_fails_fast,
    test_zero_byte_file_fails_fast_through_the_report_entry_point,
)

# --- Scenario: invalid types/values (Phase 2 SC-006) -------------------
from tests.data_engineering import test_invalid_value_detection as _invalid
from tests.data_engineering.test_invalid_value_detection import (
    test_date_far_outside_observed_range_plus_slack_flagged,
    test_known_values_within_range_not_flagged,
    test_negative_amount_flagged_but_value_not_corrected,
    test_unrecognized_categorical_code_flagged,
)

# --- Scenario: invalid dates (Phase 2 SC-001) --------------------------
from tests.data_engineering import test_date_standardization as _dates
from tests.data_engineering.test_date_standardization import (
    test_missing_value_produces_no_change_record,
    test_unparseable_date_flagged_not_guessed,
    test_valid_date_reformatted_to_iso,
)

# --- Scenario: missing columns (Phase 1 SC-002) ------------------------
from tests.data_engineering import test_profiling_service as _profiling
from tests.data_engineering.test_profiling_service import (
    test_categorical_column_gets_top_value_frequencies,
    test_date_column_reports_format_and_min_max_without_reformatting,
    test_file_level_stats_match_fixture,
    test_full_duplicate_row_is_detected,
    test_missing_column_reported_as_100_percent_missing,
    test_missing_source_file_fails_fast,
    test_numeric_column_gets_distribution_stats,
    test_wrong_column_count_fails_fast,
)

# The modules this suite aggregates, and the scenario each one serves.
REFERENCED_MODULES = {
    "missing values": _cleaning,
    "duplicates": _duplicates,
    "invalid types/values": _invalid,
    "invalid dates": _dates,
    "missing columns": _profiling,
    "empty files": _empty,
}


def _test_names(module) -> set[str]:
    return {name for name in dir(module) if name.startswith("test_")}


def _reexported_names() -> set[str]:
    """Test functions this module re-exported, excluding its own
    meta-tests (which are defined here, not imported)."""
    own = {"test_every_referenced_module_is_fully_represented", "test_suite_reexports_rather_than_reimplements"}
    return {name for name in globals() if name.startswith("test_")} - own


def test_every_referenced_module_is_fully_represented():
    """SC-005 guard: a Data-category test added upstream must not be
    silently excluded from the consolidated command. If this fails, add
    the named test to this module's imports."""
    missing = {}
    reexported = _reexported_names()
    for scenario, module in REFERENCED_MODULES.items():
        absent = _test_names(module) - reexported
        if absent:
            missing[scenario] = sorted(absent)

    assert not missing, (
        "These Data-category tests exist upstream but are not re-exported by the consolidated "
        f"suite, so `pytest backend/tests/data_suite/` would silently skip them: {missing}"
    )


def test_suite_reexports_rather_than_reimplements():
    """SC-005 proper: proves zero duplicated test logic. Every collected
    test here must be the *identical function object* defined in its home
    module -- if someone pasted a copy of a test body into this file, its
    `__module__` would point here and this check would fail."""
    reimplemented = []
    for name in _reexported_names():
        func = globals()[name]
        if inspect.getmodule(func).__name__.startswith("tests.data_suite"):
            reimplemented.append(name)

    assert not reimplemented, (
        "These tests are defined in the consolidated suite rather than imported from their "
        f"home module -- that is duplicated logic, which FR-009 forbids: {sorted(reimplemented)}"
    )
