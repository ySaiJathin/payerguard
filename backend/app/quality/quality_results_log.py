"""Persists QualityScoreResult + ExpectationCheckResult[] as
data/reports/quality_results.json, in the shape from contracts/api.md.

Each write overwrites the prior file rather than appending -- mirroring
Phase 2's quality_issue_log.py precedent -- so re-running validation on an
unmodified batch produces an identical persisted file, not an
accumulating one (spec SC-004).
"""

import json
from pathlib import Path

from app.data_engineering.paths import reports_dir
from app.quality.schemas import ExpectationCheckResult, QualityScoreResult

QUALITY_RESULTS_FILENAME = "quality_results.json"


def write_quality_results(
    score_result: QualityScoreResult,
    check_results: list[ExpectationCheckResult],
    out_dir: Path | None = None,
) -> Path:
    out_dir = out_dir or reports_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / QUALITY_RESULTS_FILENAME
    payload = {
        "quality_score_result": json.loads(score_result.model_dump_json()),
        "check_results": [json.loads(c.model_dump_json()) for c in check_results],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_quality_results(
    out_dir: Path | None = None,
) -> tuple[QualityScoreResult, list[ExpectationCheckResult]] | None:
    out_dir = out_dir or reports_dir()
    path = out_dir / QUALITY_RESULTS_FILENAME
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    score_result = QualityScoreResult.model_validate(raw["quality_score_result"])
    check_results = [ExpectationCheckResult.model_validate(item) for item in raw["check_results"]]
    return score_result, check_results


def find_check(check_id: str, out_dir: Path | None = None) -> ExpectationCheckResult | None:
    result = read_quality_results(out_dir)
    if result is None:
        return None
    _, check_results = result
    return next((c for c in check_results if c.check_id == check_id), None)
