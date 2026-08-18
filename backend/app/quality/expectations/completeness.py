"""Per-column completeness checks (FR-007), calibrated per column.

Great Expectations only supplies the raw `unexpected_percent` (the real,
computed MissingRate for that column); the PASS/WARNING/CRITICAL band is
always derived here from that rate plus whichever threshold applies
(calibrated override or the universal MVP_CONTEXT.md 3.1 bands) -- never
assigned independently (constitution Principle II, FR-013).
"""

from datetime import datetime
from uuid import uuid4

from great_expectations import ExpectationSuite
from great_expectations.expectations import ExpectColumnValuesToNotBeNull

from app.quality.bands import classify_missing_rate
from app.quality.gx_result_utils import extract_unexpected_pct
from app.quality.schemas import Band, CompletenessCalibrationEntry, ExpectationCheckResult, ExpectationType

EXPECTATION_TYPE_NAME = "expect_column_values_to_not_be_null"
CALIBRATED_WARNING_MULTIPLIER = 1.5


def add_to_suite(suite: ExpectationSuite, columns: list[str]) -> None:
    for column in columns:
        suite.add_expectation(ExpectColumnValuesToNotBeNull(column=column))


def _classify(missing_pct: float, entry: CompletenessCalibrationEntry | None) -> tuple[Band, dict]:
    if entry is None:
        return classify_missing_rate(missing_pct), {
            "calibrated": False,
            "pass_lt": 2,
            "warning_lt": 5,
            "unit": "pct",
        }
    threshold_used = {
        "calibrated": True,
        "expected_max_missing_pct": entry.expected_max_missing_pct,
        "source_note": entry.source_note,
    }
    if missing_pct <= entry.expected_max_missing_pct:
        return Band.PASS, threshold_used
    if missing_pct <= entry.expected_max_missing_pct * CALIBRATED_WARNING_MULTIPLIER:
        return Band.WARNING, threshold_used
    return Band.CRITICAL, threshold_used


def extract_results(
    validation_result,
    calibration: dict[str, CompletenessCalibrationEntry],
    run_id: str,
    evaluated_at: datetime,
) -> list[ExpectationCheckResult]:
    records: list[ExpectationCheckResult] = []
    for result in validation_result["results"]:
        if result["expectation_config"]["type"] != EXPECTATION_TYPE_NAME:
            continue
        column = result["expectation_config"]["kwargs"]["column"]
        missing_pct = extract_unexpected_pct(result["result"])
        band, threshold_used = _classify(missing_pct, calibration.get(column))
        records.append(
            ExpectationCheckResult(
                check_id=str(uuid4()),
                suite_name=validation_result["suite_name"],
                column_name=column,
                expectation_type=ExpectationType.COMPLETENESS,
                computed_rate_or_count=missing_pct,
                band=band,
                threshold_used=threshold_used,
                run_id=run_id,
                evaluated_at=evaluated_at,
            )
        )
    return records
