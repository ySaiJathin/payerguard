"""Persists BaselineSnapshot as data/reports/baseline_snapshot.json.

Unlike Phase 3's quality_results_log.py (which overwrites on every run),
each computed snapshot is appended to a history list so /baseline/history
can list prior provenance records across repeated POST /baseline/compute
calls (FR-008's recompute-without-code-changes requirement) -- the most
recent entry is what GET /baseline returns.
"""

import json
from pathlib import Path

from app.baseline.schemas import BaselineSnapshot, BaselineSnapshotSummary
from app.data_engineering.paths import reports_dir

BASELINE_SNAPSHOT_FILENAME = "baseline_snapshot.json"


def _path(out_dir: Path | None = None) -> Path:
    return (out_dir or reports_dir()) / BASELINE_SNAPSHOT_FILENAME


def _read_history(out_dir: Path | None = None) -> list[dict]:
    path = _path(out_dir)
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw["snapshots"]


def write_baseline_snapshot(snapshot: BaselineSnapshot, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or reports_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _path(out_dir)

    history = _read_history(out_dir)
    history.append(json.loads(snapshot.model_dump_json()))

    path.write_text(json.dumps({"snapshots": history}, indent=2), encoding="utf-8")
    return path


def read_latest_baseline_snapshot(out_dir: Path | None = None) -> BaselineSnapshot | None:
    history = _read_history(out_dir)
    if not history:
        return None
    return BaselineSnapshot.model_validate(history[-1])


def read_baseline_history(out_dir: Path | None = None) -> list[BaselineSnapshotSummary]:
    history = _read_history(out_dir)
    return [
        BaselineSnapshotSummary(
            snapshot_id=entry["snapshot_id"],
            source_file=entry["source_file"],
            source_row_count=entry["source_row_count"],
            computed_at=entry["computed_at"],
        )
        for entry in history
    ]
