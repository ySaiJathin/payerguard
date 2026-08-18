"""Date range/format (FR-004, FR-005) and utilization/duration range
(FR-005) checks.

Great Expectations' `expect_column_values_to_be_between` requires the
column values and bounds to be the same Python type -- comparing raw ISO
strings against string bounds raises a `MetricResolutionError` rather than
computing a result (confirmed during implementation). Date-range checks
therefore run against a `pd.to_datetime`-parsed copy of the column with
`pd.Timestamp` bounds; the ISO string format itself is checked separately
via regex on the original string column.

Bounds come from the *reference* file's observed min/max (FR-005: "the
plausible range established in Phase 2"), not the batch under validation
itself -- a self-derived bound would make an out-of-range value in that
very batch trivially satisfy its own bound and could never be caught.
"""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pandas as pd
from great_expectations import ExpectationSuite
from great_expectations.expectations import ExpectColumnValuesToBeBetween, ExpectColumnValuesToMatchRegex

from app.quality.bands import classify_unexpected_pct
from app.quality.gx_result_utils import extract_unexpected_pct
from app.quality.schemas import ExpectationCheckResult, ExpectationType

BETWEEN_EXPECTATION_TYPE_NAME = "expect_column_values_to_be_between"
REGEX_EXPECTATION_TYPE_NAME = "expect_column_values_to_match_regex"
ISO_DATE_REGEX = r"^\d{4}-\d{2}-\d{2}$"
DATE_RANGE_SLACK_DAYS = 365  # mirrors Phase 2's invalid_value_detection.py slack window


def bounds_with_slack(
    reference_date_min: date | None, reference_date_max: date | None, slack_days: int = DATE_RANGE_SLACK_DAYS
) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    if reference_date_min is None or reference_date_max is None:
        return None
    slack = timedelta(days=slack_days)
    return pd.Timestamp(reference_date_min - slack), pd.Timestamp(reference_date_max + slack)


def add_date_range(suite: ExpectationSuite, column: str, min_ts: pd.Timestamp, max_ts: pd.Timestamp) -> None:
    suite.add_expectation(ExpectColumnValuesToBeBetween(column=column, min_value=min_ts, max_value=max_ts))


def add_date_format(suite: ExpectationSuite, column: str) -> None:
    suite.add_expectation(ExpectColumnValuesToMatchRegex(column=column, regex=ISO_DATE_REGEX))


def add_utilization_range(suite: ExpectationSuite, column: str, max_value: float) -> None:
    suite.add_expectation(ExpectColumnValuesToBeBetween(column=column, min_value=0, max_value=max_value))


def extract_range_results(validation_result, run_id: str, evaluated_at: datetime) -> list[ExpectationCheckResult]:
    records: list[ExpectationCheckResult] = []
    for result in validation_result["results"]:
        if result["expectation_config"]["type"] != BETWEEN_EXPECTATION_TYPE_NAME:
            continue
        column = result["expectation_config"]["kwargs"]["column"]
        unexpected_pct = extract_unexpected_pct(result["result"])
        records.append(
            ExpectationCheckResult(
                check_id=str(uuid4()),
                suite_name=validation_result["suite_name"],
                column_name=column,
                expectation_type=ExpectationType.RANGE,
                computed_rate_or_count=unexpected_pct,
                band=classify_unexpected_pct(unexpected_pct),
                threshold_used={
                    "rule": "value within observed range + slack",
                    "warning_gt_pct": 0,
                    "critical_gt_pct": 1,
                },
                run_id=run_id,
                evaluated_at=evaluated_at,
            )
        )
    return records


def extract_format_results(validation_result, run_id: str, evaluated_at: datetime) -> list[ExpectationCheckResult]:
    records: list[ExpectationCheckResult] = []
    for result in validation_result["results"]:
        if result["expectation_config"]["type"] != REGEX_EXPECTATION_TYPE_NAME:
            continue
        column = result["expectation_config"]["kwargs"]["column"]
        unexpected_pct = extract_unexpected_pct(result["result"])
        records.append(
            ExpectationCheckResult(
                check_id=str(uuid4()),
                suite_name=validation_result["suite_name"],
                column_name=column,
                expectation_type=ExpectationType.DTYPE,
                computed_rate_or_count=unexpected_pct,
                band=classify_unexpected_pct(unexpected_pct),
                threshold_used={"rule": "matches ISO 8601 (YYYY-MM-DD)", "warning_gt_pct": 0, "critical_gt_pct": 1},
                run_id=run_id,
                evaluated_at=evaluated_at,
            )
        )
    return records
