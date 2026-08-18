"""Resolves the shared `data/` directory regardless of process cwd.

The backend is invoked with different working directories in different
contexts (docker-compose mounts the repo's `data/` to `/app/data` with cwd
`/app`; local dev may run from `backend/` or from the repo root), so paths
are resolved by walking up from this file to find a `data/` sibling rather
than assuming a fixed cwd.
"""

from pathlib import Path


def find_data_dir() -> Path:
    for candidate in Path(__file__).resolve().parents:
        data_dir = candidate / "data"
        if data_dir.is_dir():
            return data_dir
    raise FileNotFoundError(
        "Could not locate a 'data' directory by walking up from "
        f"{__file__} -- expected repo layout with a data/ folder."
    )


def raw_inpatient_csv() -> Path:
    return find_data_dir() / "raw" / "inpatient.csv"


def reports_dir() -> Path:
    return find_data_dir() / "reports"


def sampled_dir() -> Path:
    return find_data_dir() / "sampled"


def cleaned_dir() -> Path:
    return find_data_dir() / "cleaned"


def features_dir() -> Path:
    return find_data_dir() / "features"


def models_dir() -> Path:
    return find_data_dir() / "models"
