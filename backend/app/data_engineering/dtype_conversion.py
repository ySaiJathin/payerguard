"""Category-driven dtype coercion, reading Phase 1's column_categories.json
as the schema source of truth (research.md: "Cleaning reads Phase 1's
column_categories.json as its schema source of truth").
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.data_engineering.date_standardization import standardize_date_column
from app.data_engineering.paths import reports_dir
from app.data_engineering.schemas import ColumnCategory, QualityIssueRecord

COLUMN_CATEGORIES_FILENAME = "column_categories.json"


class CategoriesUnavailableError(RuntimeError):
    """Phase 1 profiling hasn't been run yet -- column_categories.json is missing."""


def load_column_categories(reports_path: Path | None = None) -> dict[str, ColumnCategory]:
    path = (reports_path or reports_dir()) / COLUMN_CATEGORIES_FILENAME
    if not path.exists():
        raise CategoriesUnavailableError(
            f"{path} not found -- run POST /data-engineering/profile (Phase 1) first."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {col: ColumnCategory(cat) for col, cat in raw.items()}


def convert_dtypes(
    df: pd.DataFrame, categories: dict[str, ColumnCategory], row_id_map: dict[int, str]
) -> tuple[pd.DataFrame, list[QualityIssueRecord]]:
    """Coerce every column to its category-implied dtype (FR-002).

    Returns the converted dataframe and the QualityIssueRecords for cells
    whose value actually changed during conversion (date reformatting).
    Missing-value records are emitted by cleaning_service.py, which has a
    uniform view across every column regardless of category.

    `row_id_map` is a plain dict (row index -> row_identifier), not a
    pandas Series -- at this dataset's scale (a few million date cells
    across all columns), a `pd.Series.loc[idx]` lookup per cell is
    dramatically slower than a native dict lookup.
    """
    now = datetime.now(timezone.utc)
    converted: dict[str, pd.Series] = {}
    records: list[QualityIssueRecord] = []

    for column in df.columns:
        category = categories[column]
        series = df[column]

        if category in (ColumnCategory.AMOUNT, ColumnCategory.UTILIZATION_DURATION):
            converted[column] = pd.to_numeric(series, errors="coerce")
        elif category == ColumnCategory.DATE:
            result = standardize_date_column(series)
            converted[column] = result.cleaned
            for change in result.changes:
                records.append(
                    QualityIssueRecord.model_construct(
                        row_identifier=row_id_map[change.row_index],
                        column_name=column,
                        original_value=change.original_value,
                        cleaned_value=change.cleaned_value,
                        quality_issue=change.quality_issue,
                        detected_at=now,
                    )
                )
        else:
            # identifier / categorical_code / diagnosis_procedure_code -> string;
            # missing cells stay missing rather than becoming the literal "nan".
            converted[column] = series.where(series.isna(), series.astype(str))

    return pd.DataFrame(converted, index=df.index), records
