"""Where uploaded raw claims files land: `data/raw/uploads/`.

Reuses `data_engineering.paths.find_data_dir` rather than re-deriving the
repo's `data/` location a second way.
"""

from pathlib import Path

from app.data_engineering.paths import find_data_dir


def uploads_dir() -> Path:
    return find_data_dir() / "raw" / "uploads"


def batch_upload_path(batch_id: str) -> Path:
    """Each accepted upload's raw bytes get their own subfolder, keyed by
    `batch_id` -- durable, uniquely-identified storage independent of
    whatever happens to the shared "current cleaned batch" state
    downstream phases operate on (spec 017 data-model.md; see
    `pipeline_runner`'s module docstring for why downstream state is not
    similarly batch-scoped)."""
    return uploads_dir() / batch_id / "raw.csv"
