"""Top-level orchestrator: loads Phase 1/2/4 outputs once and computes
both ClaimFeatures and WindowFeatures (contracts/api.md's POST
/features/compute).
"""

from pathlib import Path

import pandas as pd

from app.baseline.snapshot_log import read_latest_baseline_snapshot
from app.baseline.window_definition import DEFAULT_WINDOW_DEFINITION
from app.data_engineering.cleaning_service import CLEANED_OUTPUT_FILENAME
from app.data_engineering.dtype_conversion import CategoriesUnavailableError, load_column_categories
from app.data_engineering.invalid_value_detection import build_reference_stats
from app.data_engineering.paths import cleaned_dir, raw_inpatient_csv
from app.data_engineering.profiling_service import load_source_csv
from app.features.claim_feature_service import compute_claim_features
from app.features.schemas import ClaimFeatures, WindowFeatures
from app.features.window_feature_service import compute_window_features
from app.quality.data_loader import QualityInputUnavailableError, load_cleaned_batch


class FeaturesInputUnavailableError(FileNotFoundError):
    """Raised when Phase 1's categories, Phase 2's cleaned batch, or
    Phase 4's baseline snapshot aren't available yet (contracts/api.md's
    409 response)."""


def compute_features(
    window_definition: str = DEFAULT_WINDOW_DEFINITION,
    batch_path: Path | None = None,
) -> tuple[list[ClaimFeatures], list[WindowFeatures]]:
    try:
        categories = load_column_categories()
    except CategoriesUnavailableError as exc:
        raise FeaturesInputUnavailableError(str(exc)) from exc

    batch_path = batch_path or (cleaned_dir() / CLEANED_OUTPUT_FILENAME)
    try:
        cleaned_df = load_cleaned_batch(batch_path, categories)
    except QualityInputUnavailableError as exc:
        raise FeaturesInputUnavailableError(str(exc)) from exc

    baseline = read_latest_baseline_snapshot()
    if baseline is None:
        raise FeaturesInputUnavailableError(
            "No baseline snapshot found -- run POST /baseline/compute (Phase 4) first."
        )

    raw_df = load_source_csv(raw_inpatient_csv(), expected_column_count=None)
    reference_stats = build_reference_stats(raw_df, categories)

    claim_features = compute_claim_features(cleaned_df, categories)
    window_features = compute_window_features(
        cleaned_df, categories, reference_stats, baseline, window_definition
    )
    return claim_features, window_features
