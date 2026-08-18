"""CLM_ID claim-grain uniqueness check (FR-002).

This dataset is at claim-*line* grain, so CLM_ID legitimately repeats
across a claim's line items -- the expectation isn't row-level uniqueness,
it's that the count of *distinct* CLM_ID values matches Phase 1's measured
unique-claim count for this batch.
"""

from datetime import datetime
from uuid import uuid4

from great_expectations import ExpectationSuite
from great_expectations.expectations import ExpectColumnUniqueValueCountToBeBetween

from app.quality.schemas import Band, ExpectationCheckResult, ExpectationType

EXPECTATION_TYPE_NAME = "expect_column_unique_value_count_to_be_between"
CLM_ID_COLUMN = "CLM_ID"
WARNING_DRIFT_PCT = 5.0


def add_to_suite(suite: ExpectationSuite, expected_unique_claim_count: int) -> None:
    suite.add_expectation(
        ExpectColumnUniqueValueCountToBeBetween(
            column=CLM_ID_COLUMN,
            min_value=expected_unique_claim_count,
            max_value=expected_unique_claim_count,
        )
    )


def extract_results(
    validation_result,
    expected_unique_claim_count: int,
    run_id: str,
    evaluated_at: datetime,
) -> list[ExpectationCheckResult]:
    records: list[ExpectationCheckResult] = []
    for result in validation_result["results"]:
        if result["expectation_config"]["type"] != EXPECTATION_TYPE_NAME:
            continue
        observed = int(result["result"]["observed_value"])
        diff = abs(observed - expected_unique_claim_count)
        pct_diff = (diff / expected_unique_claim_count * 100) if expected_unique_claim_count else 0.0
        if diff == 0:
            band = Band.PASS
        elif pct_diff <= WARNING_DRIFT_PCT:
            band = Band.WARNING
        else:
            band = Band.CRITICAL
        records.append(
            ExpectationCheckResult(
                check_id=str(uuid4()),
                suite_name=validation_result["suite_name"],
                column_name=CLM_ID_COLUMN,
                expectation_type=ExpectationType.UNIQUENESS,
                computed_rate_or_count=float(observed),
                band=band,
                threshold_used={
                    "expected_unique_claim_count": expected_unique_claim_count,
                    "warning_drift_pct": WARNING_DRIFT_PCT,
                },
                run_id=run_id,
                evaluated_at=evaluated_at,
            )
        )
    return records
