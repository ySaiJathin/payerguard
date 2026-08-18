"""Amount non-negativity (FR-003) and categorical/diagnosis code-set
membership (FR-006).

The "known code set" (FR-006's "Phase 2's observed-value-set definition")
is supplied by the caller, computed against the raw reference file rather
than the batch under validation itself -- if it were computed from the
same batch being checked, every value would trivially belong to its own
observed set and nothing could ever be flagged. `suite_builder.py` sources
it via `app.data_engineering.invalid_value_detection.build_reference_stats`
against `data/raw/inpatient.csv`, reusing Phase 2's exact methodology.
"""

from datetime import datetime
from uuid import uuid4

from great_expectations import ExpectationSuite
from great_expectations.expectations import ExpectColumnValuesToBeBetween, ExpectColumnValuesToBeInSet

from app.quality.bands import classify_unexpected_pct
from app.quality.gx_result_utils import extract_unexpected_pct
from app.quality.schemas import ExpectationCheckResult, ExpectationType

AMOUNT_EXPECTATION_TYPE_NAME = "expect_column_values_to_be_between"
CODE_SET_EXPECTATION_TYPE_NAME = "expect_column_values_to_be_in_set"


def add_amount_validity(suite: ExpectationSuite, columns: list[str]) -> None:
    for column in columns:
        suite.add_expectation(ExpectColumnValuesToBeBetween(column=column, min_value=0))


def add_code_set_validity(suite: ExpectationSuite, column_value_sets: dict[str, list[str]]) -> None:
    for column, value_set in column_value_sets.items():
        suite.add_expectation(ExpectColumnValuesToBeInSet(column=column, value_set=value_set))


def extract_amount_results(validation_result, run_id: str, evaluated_at: datetime) -> list[ExpectationCheckResult]:
    records: list[ExpectationCheckResult] = []
    for result in validation_result["results"]:
        if result["expectation_config"]["type"] != AMOUNT_EXPECTATION_TYPE_NAME:
            continue
        column = result["expectation_config"]["kwargs"]["column"]
        unexpected_pct = extract_unexpected_pct(result["result"])
        records.append(
            ExpectationCheckResult(
                check_id=str(uuid4()),
                suite_name=validation_result["suite_name"],
                column_name=column,
                expectation_type=ExpectationType.VALIDITY,
                computed_rate_or_count=unexpected_pct,
                band=classify_unexpected_pct(unexpected_pct),
                threshold_used={"rule": "value >= 0", "warning_gt_pct": 0, "critical_gt_pct": 1},
                run_id=run_id,
                evaluated_at=evaluated_at,
            )
        )
    return records


def extract_code_set_results(validation_result, run_id: str, evaluated_at: datetime) -> list[ExpectationCheckResult]:
    records: list[ExpectationCheckResult] = []
    for result in validation_result["results"]:
        if result["expectation_config"]["type"] != CODE_SET_EXPECTATION_TYPE_NAME:
            continue
        column = result["expectation_config"]["kwargs"]["column"]
        unexpected_pct = extract_unexpected_pct(result["result"])
        records.append(
            ExpectationCheckResult(
                check_id=str(uuid4()),
                suite_name=validation_result["suite_name"],
                column_name=column,
                expectation_type=ExpectationType.CODE_SET,
                computed_rate_or_count=unexpected_pct,
                band=classify_unexpected_pct(unexpected_pct),
                threshold_used={"rule": "value in observed set", "warning_gt_pct": 0, "critical_gt_pct": 1},
                run_id=run_id,
                evaluated_at=evaluated_at,
            )
        )
    return records
