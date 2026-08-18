"""Stage 1: structural feature selection -- constant/near-constant,
duplicate, raw-identifier, high-missingness, and leakage-risk column
drops. Runs on the full dataset (train+validation+test): these are
column-shape properties, not statistics fit on labels, so evaluating them
across all rows doesn't violate the test-isolation guarantee that Stage
2/3 must honor (spec 006 data-model.md's `stage_computed_on: full_dataset`
note; FR-003, FR-004, FR-005).
"""

from collections import defaultdict

import pandas as pd

from app.data_engineering.schemas import ColumnCategory
from app.features.schemas import ClaimFeatures, WindowFeatures
from app.features.selection.schemas import FeatureDropDecision

DEFAULT_NEAR_CONSTANT_THRESHOLD = 0.99
DEFAULT_MISSINGNESS_THRESHOLD = 0.95
DEFAULT_LEAKAGE_NAME_PATTERNS = ("OUTCOME", "INVESTIGATION", "INCIDENT", "REMEDIATION")

STAGE = 1
STAGE_COMPUTED_ON = "full_dataset"


class AllFeaturesDroppedError(RuntimeError):
    """Raised when every column of a single Phase-1 `ColumnCategory` would
    be dropped by Stage 1 -- reported explicitly rather than silently
    proceeding with zero features from that category (FR-011)."""


def build_claim_candidate_frame(cleaned_df: pd.DataFrame, claim_features: list[ClaimFeatures]) -> pd.DataFrame:
    """Joins Phase 2's raw cleaned columns with Phase 5's engineered
    `ClaimFeatures` scalar fields (excluding `encoded_categoricals`, a
    nested dict, not a candidate model column) on `CLM_ID`."""
    claim_features_df = pd.DataFrame(
        [{k: v for k, v in cf.model_dump().items() if k != "encoded_categoricals"} for cf in claim_features]
    )
    merged = cleaned_df.merge(claim_features_df, left_on="CLM_ID", right_on="claim_id", how="left")
    return merged.drop(columns=["claim_id"])


def build_window_candidate_frame(window_features: list[WindowFeatures]) -> pd.DataFrame:
    """Flattens Phase 5's `WindowFeatures` (including per-AMOUNT-column
    nested `amount_stats`/`amount_deviation` dicts) into one scalar column
    per candidate feature, keyed by `window_id`."""
    rows = []
    for wf in window_features:
        row: dict[str, object] = {
            "window_id": wf.window_id,
            "claim_count": wf.claim_count,
            "missing_pct": wf.missing_pct,
            "duplicate_pct": wf.duplicate_pct,
            "invalid_status_pct": wf.invalid_status_pct,
            "volume_deviation": wf.volume_deviation,
            "anomaly_count": wf.anomaly_count,
        }
        for amount_col, stats in wf.amount_stats.items():
            row[f"amount_stats_mean__{amount_col}"] = stats.mean
            row[f"amount_stats_median__{amount_col}"] = stats.median
            row[f"amount_stats_std__{amount_col}"] = stats.std
        for amount_col, deviation in wf.amount_deviation.items():
            row[f"amount_deviation__{amount_col}"] = deviation
        rows.append(row)
    return pd.DataFrame(rows)


def _decision(feature_name: str, reason: str, statistic_value: float | None) -> FeatureDropDecision:
    return FeatureDropDecision(
        feature_name=feature_name,
        stage=STAGE,
        reason=reason,
        statistic_value=statistic_value,
        stage_computed_on=STAGE_COMPUTED_ON,
    )


def drop_constant_and_near_constant(
    df: pd.DataFrame, near_constant_threshold: float = DEFAULT_NEAR_CONSTANT_THRESHOLD
) -> list[FeatureDropDecision]:
    decisions = []
    for col in df.columns:
        non_null = df[col].dropna()
        if non_null.empty:
            continue  # fully-null is high-missingness's concern, not "constant"
        value_fractions = non_null.value_counts(normalize=True)
        top_fraction = float(value_fractions.iloc[0])
        if len(value_fractions) <= 1:
            decisions.append(
                _decision(col, "constant column (single value across all non-null rows)", 1.0)
            )
        elif top_fraction >= near_constant_threshold:
            decisions.append(
                _decision(
                    col,
                    f"near-constant column ({top_fraction:.1%} of non-null rows share one value)",
                    top_fraction,
                )
            )
    return decisions


def drop_high_missingness(
    df: pd.DataFrame,
    threshold: float = DEFAULT_MISSINGNESS_THRESHOLD,
    exempt_fields: frozenset[str] = frozenset(),
) -> list[FeatureDropDecision]:
    decisions = []
    for col in df.columns:
        if col in exempt_fields:
            continue
        missing_fraction = float(df[col].isna().mean())
        if missing_fraction >= threshold:
            decisions.append(
                _decision(col, f"high-missingness column ({missing_fraction:.1%} null)", missing_fraction)
            )
    return decisions


def drop_duplicate_columns(df: pd.DataFrame) -> list[FeatureDropDecision]:
    decisions = []
    kept: list[str] = []
    for col in df.columns:
        duplicate_of = next((other for other in kept if df[col].equals(df[other])), None)
        if duplicate_of is not None:
            decisions.append(_decision(col, f"duplicate of column '{duplicate_of}'", None))
        else:
            kept.append(col)
    return decisions


def drop_raw_identifiers(columns: list[str], categories: dict[str, ColumnCategory]) -> list[FeatureDropDecision]:
    return [
        _decision(
            col,
            "raw identifier column (not intended as a model input; remains available as a row key/join)",
            None,
        )
        for col in columns
        if categories.get(col) == ColumnCategory.IDENTIFIER
    ]


def drop_leakage_risk(
    columns: list[str], leakage_name_patterns: tuple[str, ...] = DEFAULT_LEAKAGE_NAME_PATTERNS
) -> list[FeatureDropDecision]:
    decisions = []
    for col in columns:
        matched = next((p for p in leakage_name_patterns if p in col.upper()), None)
        if matched is not None:
            decisions.append(
                _decision(
                    col,
                    f"leakage risk: column name matches pattern '{matched}', "
                    "likely encodes post-hoc outcome information not available at prediction time",
                    None,
                )
            )
    return decisions


def _check_no_category_fully_dropped(
    original_columns: list[str], surviving_columns: list[str], categories: dict[str, ColumnCategory]
) -> None:
    by_category: dict[ColumnCategory, list[str]] = defaultdict(list)
    for col in original_columns:
        category = categories.get(col)
        # IDENTIFIER is deliberately, wholesale dropped by drop_raw_identifiers
        # (FR-004) -- that's Stage 1 working as intended, not the accidental
        # over-filtering FR-011's guard exists to catch.
        if category is not None and category != ColumnCategory.IDENTIFIER:
            by_category[category].append(col)

    surviving_set = set(surviving_columns)
    for category, cols in by_category.items():
        if cols and not any(c in surviving_set for c in cols):
            raise AllFeaturesDroppedError(
                f"All {len(cols)} column(s) in category '{category.value}' were dropped by Stage 1: {cols}"
            )


def _apply_checks_to_frame(
    frame: pd.DataFrame,
    categories: dict[str, ColumnCategory],
    exempt_fields: frozenset[str],
    near_constant_threshold: float,
    missingness_threshold: float,
    leakage_name_patterns: tuple[str, ...],
) -> tuple[list[str], list[FeatureDropDecision]]:
    remaining = list(frame.columns)
    decisions: list[FeatureDropDecision] = []

    checks = (
        lambda cols: drop_constant_and_near_constant(frame[cols], near_constant_threshold),
        lambda cols: drop_high_missingness(frame[cols], missingness_threshold, exempt_fields),
        lambda cols: drop_duplicate_columns(frame[cols]),
        lambda cols: drop_raw_identifiers(cols, categories),
        lambda cols: drop_leakage_risk(cols, leakage_name_patterns),
    )
    for check in checks:
        check_decisions = check(remaining)
        decisions.extend(check_decisions)
        dropped_now = {d.feature_name for d in check_decisions}
        remaining = [c for c in remaining if c not in dropped_now]

    _check_no_category_fully_dropped(list(frame.columns), remaining, categories)

    return remaining, decisions


def apply_stage1(
    cleaned_df: pd.DataFrame,
    claim_features: list[ClaimFeatures],
    window_features: list[WindowFeatures],
    categories: dict[str, ColumnCategory],
    exempt_fields: frozenset[str] = frozenset(),
    near_constant_threshold: float = DEFAULT_NEAR_CONSTANT_THRESHOLD,
    missingness_threshold: float = DEFAULT_MISSINGNESS_THRESHOLD,
    leakage_name_patterns: tuple[str, ...] = DEFAULT_LEAKAGE_NAME_PATTERNS,
) -> tuple[dict[str, list[str]], list[FeatureDropDecision]]:
    claim_frame = build_claim_candidate_frame(cleaned_df, claim_features)
    window_frame = build_window_candidate_frame(window_features)

    claim_survivors, claim_decisions = _apply_checks_to_frame(
        claim_frame, categories, exempt_fields, near_constant_threshold, missingness_threshold, leakage_name_patterns
    )
    window_survivors, window_decisions = _apply_checks_to_frame(
        window_frame, categories, exempt_fields, near_constant_threshold, missingness_threshold, leakage_name_patterns
    )

    surviving = {"claim": claim_survivors, "window": window_survivors}
    return surviving, claim_decisions + window_decisions
