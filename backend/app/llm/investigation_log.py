"""Persists `LLMInvestigation`/`InvestigationFailure` records as an
append-only history to data/reports/llm_investigations.json (spec FR-006,
SC-005) -- mirrors Phase 4's `snapshot_log.py` / Phase 9's
`benchmark_log.py` append pattern (not Phase 3/7/8's overwrite pattern),
since every investigation attempt, successful or not, must be preserved
across an incident's full re-investigation history, never overwritten.
"""

import json
from pathlib import Path

from app.data_engineering.paths import reports_dir
from app.llm.schemas import InvestigationFailure, LLMInvestigation

INVESTIGATIONS_FILENAME = "llm_investigations.json"


def _path(out_dir: Path | None = None) -> Path:
    return (out_dir or reports_dir()) / INVESTIGATIONS_FILENAME


def _read_all(out_dir: Path | None = None) -> dict:
    path = _path(out_dir)
    if not path.exists():
        return {"investigations": [], "failures": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_all(data: dict, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or reports_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _path(out_dir)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def append_investigation(investigation: LLMInvestigation, out_dir: Path | None = None) -> Path:
    data = _read_all(out_dir)
    data["investigations"].append(json.loads(investigation.model_dump_json()))
    return _write_all(data, out_dir)


def append_failure(failure: InvestigationFailure, out_dir: Path | None = None) -> Path:
    data = _read_all(out_dir)
    data["failures"].append(json.loads(failure.model_dump_json()))
    return _write_all(data, out_dir)


def read_investigation_history(
    incident_id: str, out_dir: Path | None = None
) -> tuple[list[LLMInvestigation], list[InvestigationFailure]]:
    data = _read_all(out_dir)
    investigations = [
        LLMInvestigation.model_validate(entry)
        for entry in data["investigations"]
        if entry["incident_id"] == incident_id
    ]
    failures = [
        InvestigationFailure.model_validate(entry)
        for entry in data["failures"]
        if entry["incident_id"] == incident_id
    ]
    # Sort key includes the append-order index alongside the timestamp:
    # `generated_at`/`occurred_at` alone aren't a reliable tiebreaker since
    # the host clock's resolution can be coarse enough for two investigations
    # of the same incident, generated moments apart, to share an identical
    # timestamp -- a plain `sort(reverse=True)` is stable and would then
    # leave the tied pair in their original (oldest-first) append order
    # instead of the newest-first order this function promises.
    investigations = [i for _, i in sorted(enumerate(investigations), key=lambda pair: (pair[1].generated_at, pair[0]), reverse=True)]
    failures = [f for _, f in sorted(enumerate(failures), key=lambda pair: (pair[1].occurred_at, pair[0]), reverse=True)]
    return investigations, failures
