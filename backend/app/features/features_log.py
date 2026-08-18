"""Persists ClaimFeatures/WindowFeatures as data/features/claim_features.csv
and data/features/window_features.csv. Each write overwrites the prior
file (mirroring Phase 3's quality_results_log.py precedent), so re-running
POST /features/compute on an unmodified batch produces an identical
persisted file.
"""

import json
from pathlib import Path

import pandas as pd

from app.data_engineering.paths import features_dir
from app.features.schemas import ClaimFeatures, WindowFeatures

CLAIM_FEATURES_FILENAME = "claim_features.csv"
WINDOW_FEATURES_FILENAME = "window_features.csv"


def _claim_path(out_dir: Path | None = None) -> Path:
    return (out_dir or features_dir()) / CLAIM_FEATURES_FILENAME


def _window_path(out_dir: Path | None = None) -> Path:
    return (out_dir or features_dir()) / WINDOW_FEATURES_FILENAME


def write_claim_features(rows: list[ClaimFeatures], out_dir: Path | None = None) -> Path:
    out_dir = out_dir or features_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _claim_path(out_dir)

    records = [json.loads(row.model_dump_json()) for row in rows]
    for record in records:
        record["encoded_categoricals"] = json.dumps(record["encoded_categoricals"])
    pd.DataFrame(records).to_csv(path, index=False)
    return path


def read_claim_features(out_dir: Path | None = None) -> list[ClaimFeatures]:
    path = _claim_path(out_dir)
    if not path.exists():
        return []
    df = pd.read_csv(path, dtype={"claim_id": str})
    rows = []
    for record in df.to_dict(orient="records"):
        record = {k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in record.items()}
        record["encoded_categoricals"] = json.loads(record["encoded_categoricals"])
        rows.append(ClaimFeatures.model_validate(record))
    return rows


def write_window_features(rows: list[WindowFeatures], out_dir: Path | None = None) -> Path:
    out_dir = out_dir or features_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _window_path(out_dir)

    records = [json.loads(row.model_dump_json()) for row in rows]
    for record in records:
        record["amount_stats"] = json.dumps(record["amount_stats"])
        record["amount_deviation"] = json.dumps(record["amount_deviation"])
    pd.DataFrame(records).to_csv(path, index=False)
    return path


def read_window_features(out_dir: Path | None = None) -> list[WindowFeatures]:
    path = _window_path(out_dir)
    if not path.exists():
        return []
    df = pd.read_csv(path, dtype={"window_id": str})
    rows = []
    for record in df.to_dict(orient="records"):
        record["amount_stats"] = json.loads(record["amount_stats"])
        record["amount_deviation"] = json.loads(record["amount_deviation"])
        record["anomaly_count"] = None if pd.isna(record["anomaly_count"]) else int(record["anomaly_count"])
        rows.append(WindowFeatures.model_validate(record))
    return rows


def update_window_anomaly_count(window_id: str, anomaly_count: int, out_dir: Path | None = None) -> WindowFeatures:
    rows = read_window_features(out_dir)
    for i, row in enumerate(rows):
        if row.window_id == window_id:
            updated = row.model_copy(update={"anomaly_count": anomaly_count})
            rows[i] = updated
            write_window_features(rows, out_dir)
            return updated
    raise KeyError(f"No WindowFeatures row found for window_id={window_id!r}")
