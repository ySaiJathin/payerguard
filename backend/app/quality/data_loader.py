"""Loads Phase 2's cleaned batch with the correct per-category dtypes.

Reading a cleaned CSV back from disk without dtype hints lets pandas
re-infer numeric-looking identifier strings (e.g. BENE_ID) as ints,
silently undoing Phase 2's category-implied string dtype. Columns are
therefore read with an explicit dtype map derived from column_categories.json
rather than relying on pandas' inference (constitution Principle II --
categories, not guesses, decide dtype).
"""

from pathlib import Path

import pandas as pd

from app.quality.schemas import ColumnCategory

_STRING_CATEGORIES = (
    ColumnCategory.IDENTIFIER,
    ColumnCategory.DATE,
    ColumnCategory.CATEGORICAL_CODE,
    ColumnCategory.DIAGNOSIS_PROCEDURE_CODE,
)
_NUMERIC_CATEGORIES = (ColumnCategory.AMOUNT, ColumnCategory.UTILIZATION_DURATION)


class QualityInputUnavailableError(FileNotFoundError):
    """Raised when the cleaned batch this feature depends on doesn't exist (FR-012)."""


def _dtype_map(categories: dict[str, ColumnCategory]) -> dict[str, type]:
    dtype_map: dict[str, type] = {}
    for column, category in categories.items():
        if category in _STRING_CATEGORIES:
            dtype_map[column] = str
        elif category in _NUMERIC_CATEGORIES:
            dtype_map[column] = float
    return dtype_map


def load_cleaned_batch(path: Path, categories: dict[str, ColumnCategory]) -> pd.DataFrame:
    if not path.exists():
        raise QualityInputUnavailableError(
            f"No cleaned batch found at {path} -- run Phase 2 (002-cleaning-standardization) first."
        )
    return pd.read_csv(path, dtype=_dtype_map(categories))
