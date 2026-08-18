"""Stage 2: statistical feature selection -- missingness, near-zero
variance, high-cardinality, and correlation/redundancy drops. Every
statistic here is computed exclusively from the `train_val_df` passed in
by the caller (`selection_service.py`), which pre-filters to
train+validation rows before calling this module -- Stage 2 never
receives or requests test-split rows (spec FR-006, FR-010).
"""

import pandas as pd

from app.features.selection.schemas import FeatureDropDecision

STAGE = 2
STAGE_COMPUTED_ON = "train_validation"

DEFAULT_MISSINGNESS_THRESHOLD = 0.95
DEFAULT_VARIANCE_THRESHOLD = 1e-8
DEFAULT_CARDINALITY_THRESHOLD = 0.5
DEFAULT_CORRELATION_THRESHOLD = 0.95

# Tie-break for correlated pairs when missingness is equal: lower depth wins
# (raw source columns = 0, single-step derived features = 1, multi-step
# aggregates/deviations = 2+) -- prefers the simpler, more interpretable
# column (research.md's tie-breaking decision).
_KNOWN_DERIVATION_DEPTH = {
    "payment_to_charge_ratio": 1,
    "length_of_stay_days": 1,
    "admission_day_of_week": 1,
    "admission_month": 1,
    "admission_year": 1,
    "provider_frequency": 1,
    "volume_deviation": 2,
    "claim_count": 1,
    "missing_pct": 1,
    "duplicate_pct": 1,
    "invalid_status_pct": 1,
}


def _derivation_depth(col: str) -> int:
    if col in _KNOWN_DERIVATION_DEPTH:
        return _KNOWN_DERIVATION_DEPTH[col]
    if col.startswith("amount_deviation__") or col.startswith("amount_stats_"):
        return 2
    return 0


def _decision(feature_name: str, reason: str, statistic_value: float | None) -> FeatureDropDecision:
    return FeatureDropDecision(
        feature_name=feature_name,
        stage=STAGE,
        reason=reason,
        statistic_value=statistic_value,
        stage_computed_on=STAGE_COMPUTED_ON,
    )


def drop_missingness(
    df: pd.DataFrame, threshold: float = DEFAULT_MISSINGNESS_THRESHOLD, exempt_fields: frozenset[str] = frozenset()
) -> list[FeatureDropDecision]:
    decisions = []
    for col in df.columns:
        if col in exempt_fields:
            continue
        missing_fraction = float(df[col].isna().mean())
        if missing_fraction >= threshold:
            decisions.append(
                _decision(col, f"high-missingness column ({missing_fraction:.1%} null, train+validation)", missing_fraction)
            )
    return decisions


def drop_near_zero_variance(
    df: pd.DataFrame, columns: list[str], threshold: float = DEFAULT_VARIANCE_THRESHOLD
) -> list[FeatureDropDecision]:
    decisions = []
    for col in columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        series = df[col].dropna()
        if len(series) < 2:
            continue
        variance = float(series.var())
        if variance <= threshold:
            decisions.append(_decision(col, f"near-zero variance ({variance:.2e}, train+validation)", variance))
    return decisions


def drop_high_cardinality(
    df: pd.DataFrame, columns: list[str], threshold: float = DEFAULT_CARDINALITY_THRESHOLD
) -> list[FeatureDropDecision]:
    decisions = []
    for col in columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        series = df[col].dropna()
        if series.empty:
            continue
        cardinality_ratio = series.nunique() / len(series)
        if cardinality_ratio > threshold:
            decisions.append(
                _decision(
                    col,
                    f"high-cardinality categorical column ({cardinality_ratio:.1%} unique values, train+validation)",
                    cardinality_ratio,
                )
            )
    return decisions


def drop_correlated_redundant(
    df: pd.DataFrame, columns: list[str], threshold: float = DEFAULT_CORRELATION_THRESHOLD
) -> list[FeatureDropDecision]:
    numeric_columns = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(numeric_columns) < 2:
        return []

    numeric_df = df[numeric_columns]
    corr = numeric_df.corr().abs()
    missingness = {c: float(df[c].isna().mean()) for c in numeric_columns}

    decisions = []
    dropped: set[str] = set()
    for i, col_a in enumerate(numeric_columns):
        if col_a in dropped:
            continue
        for col_b in numeric_columns[i + 1 :]:
            if col_b in dropped:
                continue
            corr_value = corr.loc[col_a, col_b]
            if pd.isna(corr_value) or corr_value < threshold:
                continue

            if missingness[col_a] < missingness[col_b]:
                keep, drop = col_a, col_b
            elif missingness[col_b] < missingness[col_a]:
                keep, drop = col_b, col_a
            elif _derivation_depth(col_a) <= _derivation_depth(col_b):
                keep, drop = col_a, col_b
            else:
                keep, drop = col_b, col_a

            decisions.append(
                _decision(
                    drop,
                    f"correlation {corr_value:.2f} with '{keep}', train+validation -- kept '{keep}' "
                    "(lower missingness, or simpler derivation if tied)",
                    float(corr_value),
                )
            )
            dropped.add(drop)
    return decisions


def apply_stage2(
    train_val_df: pd.DataFrame,
    columns: list[str],
    exempt_fields: frozenset[str] = frozenset(),
    missingness_threshold: float = DEFAULT_MISSINGNESS_THRESHOLD,
    variance_threshold: float = DEFAULT_VARIANCE_THRESHOLD,
    cardinality_threshold: float = DEFAULT_CARDINALITY_THRESHOLD,
    correlation_threshold: float = DEFAULT_CORRELATION_THRESHOLD,
) -> tuple[list[str], list[FeatureDropDecision]]:
    remaining = list(columns)
    decisions: list[FeatureDropDecision] = []

    checks = (
        lambda cols: drop_missingness(train_val_df[cols], missingness_threshold, exempt_fields),
        lambda cols: drop_near_zero_variance(train_val_df, cols, variance_threshold),
        lambda cols: drop_high_cardinality(train_val_df, cols, cardinality_threshold),
        lambda cols: drop_correlated_redundant(train_val_df, cols, correlation_threshold),
    )
    for check in checks:
        check_decisions = check(remaining)
        decisions.extend(check_decisions)
        dropped_now = {d.feature_name for d in check_decisions}
        remaining = [c for c in remaining if c not in dropped_now]

    return remaining, decisions
