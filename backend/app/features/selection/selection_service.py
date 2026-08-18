"""Top-level feature-selection orchestrator (contracts/api.md's POST
/features/select): loads Phase 5's engineered features and Phase 2's
cleaned batch, computes/reuses the shared TemporalSplit, and runs Stage 1
(full dataset) -> Stage 2 -> Stage 3 (train+validation only) to produce a
SelectedFeatureSet.

Test-set isolation (FR-010) is structural, not just observed: the
train+validation frames built here are the *only* thing passed to Stage
2/3 -- those modules never receive a full dataframe or a split argument,
so there is no code path by which test rows could leak into their
statistics.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd

from app.data_engineering.cleaning_service import CLEANED_OUTPUT_FILENAME
from app.data_engineering.dtype_conversion import CategoriesUnavailableError, load_column_categories
from app.data_engineering.paths import cleaned_dir
from app.features.features_log import read_claim_features, read_window_features
from app.features.schemas import deferred_window_feature_fields
from app.features.selection.drop_decision_log import write_drop_decisions, write_selected_feature_set
from app.features.selection.schemas import FeatureDropDecision, SelectedFeatureSet, TemporalSplit
from app.features.selection.stage1_structural import (
    apply_stage1,
    build_claim_candidate_frame,
    build_window_candidate_frame,
)
from app.features.selection.stage2_statistical import apply_stage2
from app.features.selection.stage3_model_based import apply_stage3
from app.features.selection.temporal_split import (
    CLAIM_DATE_COLUMN,
    assign_split,
    compute_temporal_split,
    read_temporal_split,
    write_temporal_split,
)
from app.quality.data_loader import QualityInputUnavailableError, load_cleaned_batch

TARGET_USED = "provisional_deviation_magnitude"


class FeaturesInputUnavailableError(FileNotFoundError):
    """Raised when Phase 1's categories, Phase 2's cleaned batch, or
    Phase 5's claim/window features aren't available yet (contracts/api.md's
    409 response)."""


def _load_inputs() -> tuple[pd.DataFrame, dict, list, list]:
    try:
        categories = load_column_categories()
    except CategoriesUnavailableError as exc:
        raise FeaturesInputUnavailableError(str(exc)) from exc

    batch_path = cleaned_dir() / CLEANED_OUTPUT_FILENAME
    try:
        cleaned_df = load_cleaned_batch(batch_path, categories)
    except QualityInputUnavailableError as exc:
        raise FeaturesInputUnavailableError(str(exc)) from exc

    claim_features = read_claim_features()
    window_features = read_window_features()
    if not claim_features or not window_features:
        raise FeaturesInputUnavailableError(
            "No Phase 5 ClaimFeatures/WindowFeatures found -- run POST /features/compute first."
        )

    return cleaned_df, categories, claim_features, window_features


def _get_or_compute_split(cleaned_df: pd.DataFrame) -> TemporalSplit:
    split = read_temporal_split()
    if split is not None:
        return split
    split = compute_temporal_split(cleaned_df[CLAIM_DATE_COLUMN])
    write_temporal_split(split)
    return split


def _provisional_target_by_window(window_features: list) -> dict[str, float]:
    targets = {}
    for wf in window_features:
        magnitude = abs(wf.volume_deviation) + sum(abs(v) for v in wf.amount_deviation.values())
        targets[wf.window_id] = magnitude
    return targets


def _claim_to_window_map(cleaned_df: pd.DataFrame, window_features: list) -> dict[str, str]:
    windows_df = pd.DataFrame(
        {
            "window_id": [w.window_id for w in window_features],
            "start": pd.to_datetime([w.start for w in window_features]).astype("datetime64[ns]"),
        }
    ).sort_values("start")
    claims_df = pd.DataFrame(
        {
            "CLM_ID": cleaned_df["CLM_ID"],
            "CLM_FROM_DT": pd.to_datetime(cleaned_df[CLAIM_DATE_COLUMN]).astype("datetime64[ns]"),
        }
    ).sort_values("CLM_FROM_DT")

    merged = pd.merge_asof(claims_df, windows_df, left_on="CLM_FROM_DT", right_on="start", direction="backward")
    return dict(zip(merged["CLM_ID"], merged["window_id"]))


def run_selection() -> SelectedFeatureSet:
    cleaned_df, categories, claim_features, window_features = _load_inputs()
    split = _get_or_compute_split(cleaned_df)
    exempt_fields = deferred_window_feature_fields()

    surviving, stage1_decisions = apply_stage1(cleaned_df, claim_features, window_features, categories, exempt_fields)

    # -- Claim-level frame: filter to train+validation before Stage 2/3 --
    claim_frame_full = build_claim_candidate_frame(cleaned_df, claim_features)
    claim_dates = pd.to_datetime(claim_frame_full[CLAIM_DATE_COLUMN])
    claim_split_labels = claim_dates.apply(lambda d: assign_split(d, split))
    claim_train_val_mask = claim_split_labels != "test"
    claim_frame_train_val = claim_frame_full.loc[claim_train_val_mask, surviving["claim"]].reset_index(drop=True)

    window_target_by_id = _provisional_target_by_window(window_features)
    claim_to_window = _claim_to_window_map(cleaned_df, window_features)
    claim_targets_full = claim_frame_full["CLM_ID"].map(claim_to_window).map(window_target_by_id).fillna(0.0)
    claim_target_train_val = claim_targets_full.loc[claim_train_val_mask].reset_index(drop=True)

    claim_stage2_survivors, claim_stage2_decisions = apply_stage2(
        claim_frame_train_val, surviving["claim"], exempt_fields
    )
    claim_stage3_survivors, claim_stage3_decisions = apply_stage3(
        claim_frame_train_val, claim_stage2_survivors, claim_target_train_val
    )

    # -- Window-level frame: Stage 2 only. Running Stage 3 here would rank
    # volume_deviation/amount_deviation against a target derived from those
    # same columns, which is circular -- window-level features stop at
    # Stage 2's statistical narrowing.
    window_frame_full = build_window_candidate_frame(window_features)
    window_dates = pd.Series([pd.Timestamp(w.start) for w in window_features])
    window_split_labels = window_dates.apply(lambda d: assign_split(d, split))
    window_train_val_mask = (window_split_labels != "test").to_numpy()
    window_frame_train_val = window_frame_full.loc[window_train_val_mask, surviving["window"]].reset_index(drop=True)

    window_stage2_survivors, window_stage2_decisions = apply_stage2(
        window_frame_train_val, surviving["window"], exempt_fields
    )

    all_decisions: list[FeatureDropDecision] = (
        stage1_decisions + claim_stage2_decisions + window_stage2_decisions + claim_stage3_decisions
    )
    all_features = claim_stage3_survivors + window_stage2_survivors

    feature_set = SelectedFeatureSet(
        version_id=str(uuid4()),
        features=all_features,
        split_id=split.split_id,
        target_used_for_stage3=TARGET_USED,
        stage1_drop_count=sum(1 for d in all_decisions if d.stage == 1),
        stage2_drop_count=sum(1 for d in all_decisions if d.stage == 2),
        stage3_drop_count=sum(1 for d in all_decisions if d.stage == 3),
        generated_at=datetime.now(timezone.utc),
    )

    write_drop_decisions(all_decisions)
    write_selected_feature_set(feature_set)

    return feature_set
