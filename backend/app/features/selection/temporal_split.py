"""Computes and persists the shared temporal 70/15/15 train/validation/test
split (spec 006 FR-001, FR-002). Phase 7's anomaly benchmark and Phase 9's
risk benchmark reuse this exact split rather than each computing an
independent one (research.md), so both evaluate against identical
chronological boundaries.
"""

import json
from datetime import date as date_type
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

import pandas as pd

from app.data_engineering.cleaning_service import CLEANED_OUTPUT_FILENAME
from app.data_engineering.dtype_conversion import CategoriesUnavailableError, load_column_categories
from app.data_engineering.paths import cleaned_dir, features_dir
from app.features.selection.schemas import DateRange, TemporalSplit
from app.quality.data_loader import QualityInputUnavailableError, load_cleaned_batch

TEMPORAL_SPLIT_FILENAME = "temporal_split.json"
CLAIM_DATE_COLUMN = "CLM_FROM_DT"

TRAIN_FRACTION = 0.70
VALIDATION_FRACTION = 0.15
MIN_STABLE_PORTION_SIZE = 30


def _split_boundary_positions(counts: pd.Series) -> tuple[int, int]:
    """Chooses unique-date boundary positions so an entire date's claims land
    in a single portion -- never splitting same-date claims across
    train/validation/test, which is what guarantees zero date-range overlap
    (spec SC-001) even when many claims share a date.
    """
    n_unique = len(counts)
    n_rows = int(counts.sum())
    cumulative = counts.cumsum()

    train_target = n_rows * TRAIN_FRACTION
    val_target = n_rows * (TRAIN_FRACTION + VALIDATION_FRACTION)

    train_end_pos = int(cumulative.searchsorted(train_target, side="left"))
    val_end_pos = int(cumulative.searchsorted(val_target, side="left"))

    train_end_pos = max(0, min(train_end_pos, n_unique - 3))
    val_end_pos = max(train_end_pos + 1, min(val_end_pos, n_unique - 2))

    return train_end_pos, val_end_pos


def compute_temporal_split(claim_dates: pd.Series) -> TemporalSplit:
    """Splits `claim_dates` chronologically -- earliest ~70% of rows to
    train, next ~15% to validation, latest ~15% to test -- with zero random
    shuffling and zero date-range overlap. Deterministic and reproducible
    for unmodified input (spec FR-001, FR-002).
    """
    dates = pd.to_datetime(pd.Series(claim_dates).dropna())
    if dates.empty:
        raise ValueError("Cannot compute a temporal split from an empty/all-null date series.")

    counts = dates.dt.normalize().value_counts().sort_index()
    unique_dates = counts.index

    if len(unique_dates) < 3:
        raise ValueError(
            f"Only {len(unique_dates)} distinct claim date(s) available -- "
            "cannot form three non-overlapping train/validation/test portions."
        )

    train_end_pos, val_end_pos = _split_boundary_positions(counts)

    train_dates = unique_dates[: train_end_pos + 1]
    validation_dates = unique_dates[train_end_pos + 1 : val_end_pos + 1]
    test_dates = unique_dates[val_end_pos + 1 :]

    train_count = int(counts.loc[train_dates].sum())
    validation_count = int(counts.loc[validation_dates].sum())
    test_count = int(counts.loc[test_dates].sum())

    warning = None
    if validation_count < MIN_STABLE_PORTION_SIZE or test_count < MIN_STABLE_PORTION_SIZE:
        warning = (
            f"validation_count={validation_count}, test_count={test_count} -- "
            f"below the minimum ({MIN_STABLE_PORTION_SIZE}) considered stable for Stage 2/3 statistics."
        )

    return TemporalSplit(
        split_id=str(uuid4()),
        train_date_range=DateRange(start=train_dates.min().date(), end=train_dates.max().date()),
        validation_date_range=DateRange(
            start=validation_dates.min().date(), end=validation_dates.max().date()
        ),
        test_date_range=DateRange(start=test_dates.min().date(), end=test_dates.max().date()),
        train_count=train_count,
        validation_count=validation_count,
        test_count=test_count,
        computed_at=datetime.now(timezone.utc),
        sample_size_warning=warning,
    )


def assign_split(when: date_type | datetime | str, split: TemporalSplit) -> Literal["train", "validation", "test"]:
    """Classifies any date (e.g. a claim's `CLM_FROM_DT` or a window's
    `start`) against `split`'s boundaries. Ranges are contiguous and
    non-overlapping by construction, so a `<=` cascade is sufficient,
    including for dates that fall in a calendar gap between two portions.
    """
    d = pd.Timestamp(when).date()
    if d <= split.train_date_range.end:
        return "train"
    if d <= split.validation_date_range.end:
        return "validation"
    return "test"


def _path(out_dir: Path | None = None) -> Path:
    return (out_dir or features_dir()) / TEMPORAL_SPLIT_FILENAME


def write_temporal_split(split: TemporalSplit, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or features_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _path(out_dir)
    path.write_text(split.model_dump_json(indent=2), encoding="utf-8")
    return path


def read_temporal_split(out_dir: Path | None = None) -> TemporalSplit | None:
    path = _path(out_dir)
    if not path.exists():
        return None
    return TemporalSplit.model_validate(json.loads(path.read_text(encoding="utf-8")))


class TemporalSplitInputUnavailableError(FileNotFoundError):
    """Raised when Phase 1's categories or Phase 2's cleaned batch aren't
    available yet (contracts/api.md's 409 response)."""


def compute_and_persist_temporal_split(batch_path: Path | None = None) -> TemporalSplit:
    """Loads Phase 2's cleaned batch, computes the split from its
    `CLM_FROM_DT` column, and persists it. Used by `POST /features/split`
    when no split has been computed yet, and reusable by Phase 6's own
    `selection_service.py` orchestrator.
    """
    try:
        categories = load_column_categories()
    except CategoriesUnavailableError as exc:
        raise TemporalSplitInputUnavailableError(str(exc)) from exc

    batch_path = batch_path or (cleaned_dir() / CLEANED_OUTPUT_FILENAME)
    try:
        cleaned_df = load_cleaned_batch(batch_path, categories)
    except QualityInputUnavailableError as exc:
        raise TemporalSplitInputUnavailableError(str(exc)) from exc

    split = compute_temporal_split(cleaned_df[CLAIM_DATE_COLUMN])
    write_temporal_split(split)
    return split
