"""Persists the QualityIssueRecord audit trail as data/reports/quality_issues.json.

Each write overwrites the prior file rather than appending -- required for
idempotency (FR-009): re-running cleaning on unmodified input must produce
an identical trail, not an accumulating one.
"""

import json
from pathlib import Path

from app.data_engineering.paths import reports_dir
from app.data_engineering.schemas import CleaningRunSummary, QualityIssueRecord

QUALITY_ISSUES_FILENAME = "quality_issues.json"
CLEANING_RUN_SUMMARY_FILENAME = "cleaning_run_summary.json"


def write_quality_issues(
    records: list[QualityIssueRecord], out_dir: Path | None = None
) -> Path:
    out_dir = out_dir or reports_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / QUALITY_ISSUES_FILENAME
    payload = "[\n" + ",\n".join(r.model_dump_json() for r in records) + "\n]" if records else "[]"
    path.write_text(payload, encoding="utf-8")
    return path


def read_quality_issues(out_dir: Path | None = None) -> list[QualityIssueRecord] | None:
    out_dir = out_dir or reports_dir()
    path = out_dir / QUALITY_ISSUES_FILENAME
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [QualityIssueRecord.model_validate(item) for item in raw]


def write_cleaning_run_summary(summary: CleaningRunSummary, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or reports_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / CLEANING_RUN_SUMMARY_FILENAME
    path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return path


def read_cleaning_run_summary(out_dir: Path | None = None) -> CleaningRunSummary | None:
    out_dir = out_dir or reports_dir()
    path = out_dir / CLEANING_RUN_SUMMARY_FILENAME
    if not path.exists():
        return None
    return CleaningRunSummary.model_validate_json(path.read_text(encoding="utf-8"))
