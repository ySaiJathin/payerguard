"""Filesystem layout for the demo feature.

Everything the demo owns lives under `data/demo/synthetic/` so it never
collides with `data/cleaned/`, `data/reports/` or the pre-existing
`data/demo/batch_XX_*.csv` date-slices of the real extract.
"""

from pathlib import Path

from app.data_engineering.paths import find_data_dir

COLUMN_PROFILE_FILENAME = "column_profile.json"
MANIFEST_FILENAME = "manifest.json"
PIPELINE_RUNS_FILENAME = "pipeline_runs.json"
RISK_MODEL_FILENAME = "demo_risk_xgboost.pkl"


def demo_dir() -> Path:
    path = find_data_dir() / "demo" / "synthetic"
    path.mkdir(parents=True, exist_ok=True)
    return path


def uploads_dir() -> Path:
    path = demo_dir() / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def column_profile_path() -> Path:
    return demo_dir() / COLUMN_PROFILE_FILENAME


def manifest_path() -> Path:
    return demo_dir() / MANIFEST_FILENAME


def pipeline_runs_path() -> Path:
    return demo_dir() / PIPELINE_RUNS_FILENAME


def batch_csv_path(batch_id: str) -> Path:
    return demo_dir() / f"{batch_id}.csv"


def ground_truth_path(batch_id: str) -> Path:
    return demo_dir() / f"{batch_id}_ground_truth.csv"


def risk_model_path() -> Path:
    from app.data_engineering.paths import models_dir

    path = models_dir() / "risk"
    path.mkdir(parents=True, exist_ok=True)
    return path / RISK_MODEL_FILENAME
