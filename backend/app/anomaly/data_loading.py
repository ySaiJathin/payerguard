"""Builds the per-claim numeric feature matrix that `benchmark.py` splits
train/validation/test and injects synthetic anomalies into.

Reuses Phase 6's `build_claim_candidate_frame`/`build_window_candidate_frame`
column-flattening, joins each claim to its containing window's flattened
columns (nearest window start at or before the claim's date -- the same
join `selection_service.py` performs, reimplemented here rather than
importing that module's private helper across the package boundary, per
constitution Principle VI), then restricts the result to
`SelectedFeatureSet.features` columns that are numeric. Non-numeric
survivors (raw categoricals Stage 1/2/3 didn't drop) aren't usable by
IQR/HBOS/Isolation Forest/LOF's numeric distance/statistics without further
encoding, which is out of this feature's scope (spec Assumptions).
"""

import pandas as pd

from app.data_engineering.cleaning_service import CLEANED_OUTPUT_FILENAME
from app.data_engineering.dtype_conversion import CategoriesUnavailableError, load_column_categories
from app.data_engineering.paths import cleaned_dir
from app.features.features_log import read_claim_features, read_window_features
from app.features.selection.drop_decision_log import read_selected_feature_set
from app.features.selection.schemas import SelectedFeatureSet, TemporalSplit
from app.features.selection.stage1_structural import build_claim_candidate_frame, build_window_candidate_frame
from app.features.selection.temporal_split import CLAIM_DATE_COLUMN, read_temporal_split
from app.quality.data_loader import QualityInputUnavailableError, load_cleaned_batch

CLAIM_ID_COLUMN = "CLM_ID"


class AnomalyInputUnavailableError(FileNotFoundError):
    """Raised when Phase 1/2/5/6 prerequisites (column categories, cleaned
    batch, ClaimFeatures/WindowFeatures, TemporalSplit, SelectedFeatureSet)
    aren't available yet (contracts/api.md's 409 response)."""


def _claim_to_window_ids(cleaned_df: pd.DataFrame, window_features: list) -> pd.DataFrame:
    """Maps each claim (`CLM_ID`) to its containing window's `window_id` --
    the window whose `start` is the latest one at or before the claim's
    `CLM_FROM_DT`. Shared by `_claim_window_join` (used to build the
    benchmark's numeric matrix) and `load_claim_window_map` (used by
    `window_enrichment.py` to count flagged claims per window)."""
    # Both sides are cast to the same datetime64 unit ("ns") -- pandas'
    # merge_asof requires an exact dtype match between join keys, and
    # `pd.to_datetime` on `date` objects vs. on a datetime-like Series can
    # otherwise infer different units (e.g. [s] vs [us]), matching
    # selection_service.py's `_claim_to_window_map` workaround for the same
    # issue.
    windows_df = pd.DataFrame(
        {
            "window_id": [w.window_id for w in window_features],
            "start": pd.to_datetime([w.start for w in window_features]).astype("datetime64[ns]"),
        }
    ).sort_values("start")
    claims_df = pd.DataFrame(
        {
            CLAIM_ID_COLUMN: cleaned_df[CLAIM_ID_COLUMN],
            CLAIM_DATE_COLUMN: pd.to_datetime(cleaned_df[CLAIM_DATE_COLUMN]).astype("datetime64[ns]"),
        }
    ).sort_values(CLAIM_DATE_COLUMN)

    merged = pd.merge_asof(claims_df, windows_df, left_on=CLAIM_DATE_COLUMN, right_on="start", direction="backward")
    return merged[[CLAIM_ID_COLUMN, "window_id"]]


def _claim_window_join(cleaned_df: pd.DataFrame, window_features: list) -> pd.DataFrame:
    """Returns one row per claim (`CLM_ID`), carrying its containing
    window's flattened `WindowFeatures` columns."""
    window_frame = build_window_candidate_frame(window_features)
    claim_to_window = _claim_to_window_ids(cleaned_df, window_features)
    return claim_to_window.merge(window_frame, on="window_id", how="left").drop(columns=["window_id"])


def load_claim_window_map() -> dict[str, str]:
    """Returns `{CLM_ID: window_id}` for every claim -- used by
    `window_enrichment.py` to count real, per-window flagged claims without
    re-deriving the full flattened window-feature join."""
    cleaned_df, _claim_features, window_features, _split, _feature_set = _load_inputs()
    mapping = _claim_to_window_ids(cleaned_df, window_features)
    return dict(zip(mapping[CLAIM_ID_COLUMN], mapping["window_id"]))


def _load_inputs() -> tuple[pd.DataFrame, list, list, TemporalSplit, SelectedFeatureSet]:
    try:
        categories = load_column_categories()
    except CategoriesUnavailableError as exc:
        raise AnomalyInputUnavailableError(str(exc)) from exc

    batch_path = cleaned_dir() / CLEANED_OUTPUT_FILENAME
    try:
        cleaned_df = load_cleaned_batch(batch_path, categories)
    except QualityInputUnavailableError as exc:
        raise AnomalyInputUnavailableError(str(exc)) from exc

    claim_features = read_claim_features()
    window_features = read_window_features()
    if not claim_features or not window_features:
        raise AnomalyInputUnavailableError(
            "No Phase 5 ClaimFeatures/WindowFeatures found -- run POST /features/compute first."
        )

    split = read_temporal_split()
    if split is None:
        raise AnomalyInputUnavailableError("No TemporalSplit computed yet -- run POST /features/split first.")

    feature_set = read_selected_feature_set()
    if feature_set is None:
        raise AnomalyInputUnavailableError("No SelectedFeatureSet computed yet -- run POST /features/select first.")

    # Phase 2's cleaned batch and Phase 5's `ClaimFeatures` are both persisted
    # at claim-LINE grain (one row per CLM_LINE_NUM, e.g. up to 46 rows for a
    # single CLM_ID) rather than one row per claim. This module's contract is
    # claim grain (see module docstring), so collapse both to one row per
    # CLM_ID here, before any join touches them -- left ungated, the later
    # merge on CLM_ID becomes many-to-many (a 46-line claim produced 46x46
    # duplicate rows), which both explodes runtime and breaks the injection
    # harness's scalar `.loc[row_id, col]` reads once a row_id repeats in the
    # index. Keeping the first line per claim is a lossless collapse, not an
    # aggregation choice: CMS RIF-format data replicates every claim-level
    # source column identically across a claim's lines, so all candidates
    # being dropped are exact duplicates of the one being kept.
    cleaned_df = cleaned_df.drop_duplicates(subset=[CLAIM_ID_COLUMN], keep="first")
    seen_claim_ids: set[str] = set()
    deduped_claim_features = []
    for cf in claim_features:
        if cf.claim_id not in seen_claim_ids:
            seen_claim_ids.add(cf.claim_id)
            deduped_claim_features.append(cf)
    claim_features = deduped_claim_features

    return cleaned_df, claim_features, window_features, split, feature_set


def load_benchmark_inputs() -> pd.DataFrame:
    """Builds the per-claim numeric feature matrix, indexed by `CLM_ID`
    with `CLM_FROM_DT` retained (so `benchmark.py` can assign each row to
    train/validation/test via Phase 6's `assign_split`)."""
    cleaned_df, claim_features, window_features, _split, feature_set = _load_inputs()

    claim_frame = build_claim_candidate_frame(cleaned_df, claim_features)
    window_join = _claim_window_join(cleaned_df, window_features)
    joined = claim_frame.merge(window_join, on=CLAIM_ID_COLUMN, how="left")

    numeric_selected = [
        col for col in feature_set.features if col in joined.columns and pd.api.types.is_numeric_dtype(joined[col])
    ]

    matrix = joined[[CLAIM_ID_COLUMN, CLAIM_DATE_COLUMN] + numeric_selected].set_index(CLAIM_ID_COLUMN)
    return matrix
