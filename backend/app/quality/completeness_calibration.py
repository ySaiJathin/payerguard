"""Per-column completeness calibration (FR-007): columns whose real,
measured missingness already exceeds the universal MissingRate CRITICAL
band get their own calibrated ceiling instead of being flagged CRITICAL
every run for a documented, structural characteristic of the source data
(e.g. ADMTG_DGNS_CD at 72.2% missing, or the fully-null columns).

Calibration entries are derived from Phase 1's persisted profiling report
-- never hardcoded MVP_CONTEXT.md numbers, which the project has already
found go stale (see 002-cleaning-standardization's date-range handling) --
so this stays correct as the underlying data changes.
"""

from app.data_engineering.schemas import ProfilingReport
from app.quality.bands import MISSING_RATE_CRITICAL_PCT
from app.quality.schemas import CompletenessCalibrationEntry

DEFAULT_CALIBRATION_SLACK_PCT = 10.0


def build_calibration_table(
    profiling_report: ProfilingReport, slack_pct: float = DEFAULT_CALIBRATION_SLACK_PCT
) -> dict[str, CompletenessCalibrationEntry]:
    entries: dict[str, CompletenessCalibrationEntry] = {}
    for column in profiling_report.columns:
        if column.missing_pct <= MISSING_RATE_CRITICAL_PCT:
            continue
        expected_max = min(100.0, column.missing_pct + slack_pct)
        entries[column.column_name] = CompletenessCalibrationEntry(
            column_name=column.column_name,
            expected_max_missing_pct=expected_max,
            source_note=(
                f"{profiling_report.source_file}: observed {column.missing_pct:.1f}% missing "
                f"for {column.column_name} as of {profiling_report.generated_at.isoformat()} "
                f"(+{slack_pct:.0f}pp calibration slack)"
            ),
        )
    return entries
