"""Persists a versioned history of risk model benchmark runs as
data/reports/risk_benchmark_results.json (spec FR-009; research.md).

Unlike Phase 3/7/8's overwrite-on-each-run logs, each run is *appended* to
a history list -- mirroring Phase 4's `snapshot_log.py` precedent -- so
re-running the benchmark after new historical data is loaded produces
a new, distinguishable, versioned entry rather than erasing the prior
one. Runs are keyed by `(risk_dataset_version, split_id)`.
"""

import json
from pathlib import Path

from app.data_engineering.paths import reports_dir
from app.risk.benchmark.schemas import RiskBenchmarkRunResult

RESULTS_FILENAME = "risk_benchmark_results.json"


def _path(out_dir: Path | None = None) -> Path:
    return (out_dir or reports_dir()) / RESULTS_FILENAME


def _read_history(out_dir: Path | None = None) -> list[dict]:
    path = _path(out_dir)
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw["runs"]


def append_run_result(
    run_result: RiskBenchmarkRunResult, risk_dataset_version: str, split_id: str, out_dir: Path | None = None
) -> Path:
    out_dir = out_dir or reports_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _path(out_dir)

    history = _read_history(out_dir)
    history.append(
        {
            "risk_dataset_version": risk_dataset_version,
            "split_id": split_id,
            "run_result": json.loads(run_result.model_dump_json()),
        }
    )
    path.write_text(json.dumps({"runs": history}, indent=2), encoding="utf-8")
    return path


def read_latest_run_result(out_dir: Path | None = None) -> RiskBenchmarkRunResult | None:
    history = _read_history(out_dir)
    if not history:
        return None
    return RiskBenchmarkRunResult.model_validate(history[-1]["run_result"])


def read_run_result_by_version(risk_dataset_version: str, out_dir: Path | None = None) -> RiskBenchmarkRunResult | None:
    history = _read_history(out_dir)
    matches = [entry for entry in history if entry["risk_dataset_version"] == risk_dataset_version]
    if not matches:
        return None
    return RiskBenchmarkRunResult.model_validate(matches[-1]["run_result"])
