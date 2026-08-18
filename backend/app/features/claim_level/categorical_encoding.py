"""Categorical encoding scheme: one-hot for low-cardinality columns,
frequency encoding for high-cardinality columns (FR-004), per
specs/005-feature-engineering research.md's cardinality rule.

Every scheme reserves an explicit "unknown" bucket for categories not
observed during fitting: a dedicated one-hot indicator column for
one-hot-encoded columns, and a real 0.0 (a genuinely computed zero
historical occurrence, not a fabricated stand-in) for frequency-encoded
columns -- never an error, never a silent alias to an existing category's
code (spec SC-005).
"""

import pandas as pd

from app.data_engineering.schemas import ColumnCategory
from app.features.schemas import EncodingScheme

LOW_CARDINALITY_THRESHOLD = 100
UNKNOWN_BUCKET = "__unknown__"
ONE_HOT = "one_hot"
FREQUENCY = "frequency"
_ENCODABLE_CATEGORIES = (ColumnCategory.CATEGORICAL_CODE, ColumnCategory.DIAGNOSIS_PROCEDURE_CODE)


def fit_encoding_scheme(df: pd.DataFrame, categories: dict[str, ColumnCategory]) -> dict[str, EncodingScheme]:
    schemes: dict[str, EncodingScheme] = {}
    for column, category in categories.items():
        if category not in _ENCODABLE_CATEGORIES or column not in df.columns:
            continue
        observed = df[column].dropna().astype(str)
        if observed.empty:
            continue

        fitted_categories = sorted(observed.unique())
        if len(fitted_categories) <= LOW_CARDINALITY_THRESHOLD:
            schemes[column] = EncodingScheme(
                column_name=column, strategy=ONE_HOT, fitted_categories=fitted_categories
            )
        else:
            counts = observed.value_counts()
            frequency_map = {str(k): float(v) / len(observed) for k, v in counts.items()}
            schemes[column] = EncodingScheme(
                column_name=column,
                strategy=FREQUENCY,
                fitted_categories=fitted_categories,
                frequency_map=frequency_map,
            )
    return schemes


def apply_encoding_scheme(df: pd.DataFrame, schemes: dict[str, EncodingScheme]) -> pd.DataFrame:
    encoded: dict[str, pd.Series] = {}

    for column, scheme in schemes.items():
        series = df[column] if column in df.columns else pd.Series(index=df.index, dtype=object)
        as_str = series.astype(str)
        is_missing = series.isna()

        if scheme.strategy == ONE_HOT:
            is_known = as_str.isin(scheme.fitted_categories)
            for category in scheme.fitted_categories:
                indicator = (as_str == category).astype(float)
                encoded[f"{column}={category}"] = indicator.mask(is_missing)
            unknown_indicator = (~is_known).astype(float)
            encoded[f"{column}={UNKNOWN_BUCKET}"] = unknown_indicator.mask(is_missing)
        else:
            frequency = as_str.map(scheme.frequency_map)
            unseen_mask = (~is_missing) & frequency.isna()
            frequency = frequency.mask(unseen_mask, 0.0)
            encoded[column] = frequency.mask(is_missing)

    return pd.DataFrame(encoded, index=df.index)
