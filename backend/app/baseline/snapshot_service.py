"""Assembles and persists BaselineSnapshot with source-data provenance
(FR-007).

Reads Phase 2's cleaned batch and Phase 3's quality results as inputs --
this module owns loading both and raising a single, consistent
unavailable-input error rather than each sub-baseline module reaching
into Phase 2/3's internals independently.
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd

from app.baseline.amount_baseline import compute_amount_baselines
from app.baseline.data_health_baseline import compute_data_health_baseline
from app.baseline.length_of_stay_baseline import compute_length_of_stay_baseline
from app.baseline.schemas import BaselineSnapshot, SourceDateRange
from app.baseline.volume_baseline import compute_volume_baseline
from app.baseline.window_definition import DEFAULT_WINDOW_DEFINITION
from app.data_engineering.cleaning_service import CLEANED_OUTPUT_FILENAME
from app.data_engineering.dtype_conversion import CategoriesUnavailableError, load_column_categories
from app.data_engineering.paths import cleaned_dir
from app.quality.data_loader import QualityInputUnavailableError, load_cleaned_batch
from app.quality.quality_results_log import read_quality_results
from app.quality.schemas import ExpectationCheckResult, QualityScoreResult

FROM_DATE_COLUMN = "CLM_FROM_DT"


class BaselineInputUnavailableError(FileNotFoundError):
    """Raised when Phase 2's cleaned batch or Phase 3's quality results
    aren't available yet (contracts/api.md's 409 response)."""


def load_baseline_inputs(
    batch_path: Path | None = None,
) -> tuple[pd.DataFrame, Path, dict, QualityScoreResult, list[ExpectationCheckResult]]:
    """Loads Phase 2's cleaned dataframe and Phase 3's persisted quality
    results. Raises BaselineInputUnavailableError if either is missing.
    """
    batch_path = batch_path or (cleaned_dir() / CLEANED_OUTPUT_FILENAME)

    try:
        categories = load_column_categories()
    except CategoriesUnavailableError as exc:
        raise BaselineInputUnavailableError(str(exc)) from exc

    try:
        cleaned_df = load_cleaned_batch(batch_path, categories)
    except QualityInputUnavailableError as exc:
        raise BaselineInputUnavailableError(str(exc)) from exc

    quality_results = read_quality_results()
    if quality_results is None:
        raise BaselineInputUnavailableError(
            "No quality results found -- run POST /quality/validate (Phase 3) first."
        )
    score_result, check_results = quality_results

    return cleaned_df, batch_path, categories, score_result, check_results


def build_provenance(cleaned_df: pd.DataFrame, batch_path: Path) -> dict:
    """Produces {source_file, source_row_count, source_date_range} from
    the cleaned dataframe (FR-007, SC-006). Pure function, reusable by
    every sub-baseline's snapshot assembly.
    """
    parsed = pd.to_datetime(cleaned_df[FROM_DATE_COLUMN], errors="coerce").dropna()
    if parsed.empty:
        raise ValueError(f"{FROM_DATE_COLUMN} has no valid dates -- cannot establish source_date_range.")

    return {
        "source_file": str(batch_path),
        "source_row_count": len(cleaned_df),
        "source_date_range": {
            "min_date": parsed.min().date(),
            "max_date": parsed.max().date(),
        },
    }


def compute_baseline_snapshot(
    window_definition: str = DEFAULT_WINDOW_DEFINITION,
    batch_path: Path | None = None,
) -> BaselineSnapshot:
    """Full orchestrator (FR-001 through FR-010): loads Phase 2/3 outputs,
    computes every sub-baseline, and assembles a provenance-carrying
    BaselineSnapshot. Raises BaselineInputUnavailableError if Phase 2's
    cleaned batch or Phase 3's quality results aren't available yet.
    """
    cleaned_df, resolved_path, categories, _score_result, check_results = load_baseline_inputs(batch_path)
    provenance = build_provenance(cleaned_df, resolved_path)

    return BaselineSnapshot(
        snapshot_id=str(uuid4()),
        source_file=provenance["source_file"],
        source_row_count=provenance["source_row_count"],
        source_date_range=SourceDateRange(**provenance["source_date_range"]),
        volume_baseline=compute_volume_baseline(cleaned_df, window_definition),
        amount_baselines=compute_amount_baselines(cleaned_df, categories),
        data_health_baseline=compute_data_health_baseline(cleaned_df, check_results),
        length_of_stay_baseline=compute_length_of_stay_baseline(cleaned_df),
        computed_at=datetime.now(timezone.utc),
    )
