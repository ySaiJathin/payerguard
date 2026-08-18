"""Batch-level ingestion-recency check (FR-008).

Scoped to ingestion recency, not claims-processing turnaround, per
research.md: MVP_CONTEXT.md Section 2.4 already ruled out
`NCH_WKLY_PROC_DT` as a genuine operational timestamp (a fixed weekly
batch-cutoff date, always a Friday, carrying no claim-specific
information) -- reusing it here would reintroduce the same fabrication
problem the project already caught once for the SLA-breach label. Since
no ingestion module exists yet to record a real ingestion timestamp, this
uses the cleaned batch file's own mtime as a documented proxy.
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.quality.schemas import Band, ExpectationCheckResult, ExpectationType

FRESHNESS_SUITE_NAME = "freshness_suite"
FRESHNESS_WARNING_DAYS = 30.0
FRESHNESS_CRITICAL_DAYS = 90.0


def evaluate_freshness(
    batch_path: Path,
    run_id: str,
    now: datetime | None = None,
    evaluated_at: datetime | None = None,
    warning_days: float = FRESHNESS_WARNING_DAYS,
    critical_days: float = FRESHNESS_CRITICAL_DAYS,
) -> ExpectationCheckResult:
    now = now or datetime.now(timezone.utc)
    mtime = datetime.fromtimestamp(batch_path.stat().st_mtime, tz=timezone.utc)
    age_days = (now - mtime).total_seconds() / 86400

    if age_days > critical_days:
        band = Band.CRITICAL
    elif age_days > warning_days:
        band = Band.WARNING
    else:
        band = Band.PASS

    return ExpectationCheckResult(
        check_id=str(uuid4()),
        suite_name=FRESHNESS_SUITE_NAME,
        column_name=None,
        expectation_type=ExpectationType.FRESHNESS,
        computed_rate_or_count=age_days,
        band=band,
        threshold_used={
            "proxy": "cleaned batch file mtime (no ingestion-timestamp field exists yet)",
            "warning_gt_days": warning_days,
            "critical_gt_days": critical_days,
        },
        run_id=run_id,
        evaluated_at=evaluated_at or now,
    )
