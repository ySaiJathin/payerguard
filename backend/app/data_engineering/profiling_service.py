"""Full per-column and file-level statistical profiling of inpatient.csv.

See specs/001-data-profiling-foundation/spec.md (FR-001..FR-006) and
data-model.md for the exact fields computed here. Every statistic is
computed from the current contents of the source file at call time --
nothing here is a hardcoded/expected value (constitution Principle II).
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.data_engineering.categorization import categorize
from app.data_engineering.paths import raw_inpatient_csv
from app.data_engineering.schemas import (
    ColumnCategory,
    ColumnProfile,
    NumericStats,
    ProfilingReport,
    ValueCount,
)

EXPECTED_COLUMN_COUNT = 197
CLM_ID_COLUMN = "CLM_ID"
BENE_ID_COLUMN = "BENE_ID"
TOP_VALUES_LIMIT = 10
PERCENTILES = [0.25, 0.5, 0.75, 0.95, 0.99]

# Recognized raw date-string formats, tried in order against a sample value.
_DATE_FORMAT_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}$"), "DD-Mon-YYYY", "%d-%b-%Y"),
]


class ProfilingError(ValueError):
    """Source file is missing, unreadable, or structurally malformed."""


def load_source_csv(
    source_path: Path, expected_column_count: int | None = EXPECTED_COLUMN_COUNT
) -> pd.DataFrame:
    """Read and structurally validate the pipe-delimited source file.

    Shared with sampling_service.py so both features apply the same
    delimiter/column-count/required-column checks (FR-001, FR-013).
    `expected_column_count` defaults to the real inpatient.csv schema shape
    (197); tests pass the fixture's actual column count instead, since
    authoring a 197-column fixture would defeat the point of a fast,
    small, unit-test fixture.
    """
    if not source_path.exists():
        raise ProfilingError(f"Source file not found: {source_path}")
    try:
        df = pd.read_csv(source_path, sep="|", low_memory=False)
    except Exception as exc:
        raise ProfilingError(
            f"Failed to read {source_path} as a pipe-delimited CSV: {exc}"
        ) from exc
    if expected_column_count is not None and df.shape[1] != expected_column_count:
        raise ProfilingError(
            f"Expected {expected_column_count} columns, found {df.shape[1]} in "
            f"{source_path} -- check the file is pipe-delimited, not comma-delimited."
        )
    for required in (CLM_ID_COLUMN, BENE_ID_COLUMN):
        if required not in df.columns:
            raise ProfilingError(f"Required column '{required}' not present in {source_path}")
    return df


def _numeric_stats(series: pd.Series) -> NumericStats | None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    percentiles = numeric.quantile(PERCENTILES)
    return NumericStats(
        mean=float(numeric.mean()),
        median=float(numeric.median()),
        std=float(numeric.std()) if len(numeric) > 1 else 0.0,
        min=float(numeric.min()),
        max=float(numeric.max()),
        p25=float(percentiles.loc[0.25]),
        p50=float(percentiles.loc[0.50]),
        p75=float(percentiles.loc[0.75]),
        p95=float(percentiles.loc[0.95]),
        p99=float(percentiles.loc[0.99]),
    )


def _categorical_top_values(series: pd.Series, limit: int = TOP_VALUES_LIMIT) -> list[ValueCount] | None:
    counts = series.dropna().astype(str).value_counts()
    if counts.empty:
        return None
    return [ValueCount(value=value, count=int(count)) for value, count in counts.head(limit).items()]


def _profile_date_column(series: pd.Series) -> tuple[str | None, str | None, str | None]:
    non_null = series.dropna().astype(str)
    if non_null.empty:
        return None, None, None
    sample = non_null.iloc[0]
    for pattern, label, strptime_fmt in _DATE_FORMAT_PATTERNS:
        if pattern.match(sample):
            parsed = pd.to_datetime(non_null, format=strptime_fmt, errors="coerce")
            valid = parsed.dropna()
            if valid.empty:
                return label, None, None
            return label, non_null.loc[valid.idxmin()], non_null.loc[valid.idxmax()]
    # Unrecognized format: report raw lexicographic bounds as a best-effort fallback
    # rather than failing -- the format itself is what's flagged as unrecognized.
    return "unrecognized", non_null.min(), non_null.max()


def _profile_column(series: pd.Series, category: ColumnCategory, total_rows: int) -> ColumnProfile:
    missing_count = int(series.isna().sum())
    missing_pct = (missing_count / total_rows * 100) if total_rows else 0.0
    cardinality = int(series.dropna().nunique())

    numeric_stats = None
    categorical_top_values = None
    date_format_observed = date_min = date_max = None

    if category in (ColumnCategory.AMOUNT, ColumnCategory.UTILIZATION_DURATION):
        numeric_stats = _numeric_stats(series)
    elif category == ColumnCategory.DATE:
        date_format_observed, date_min, date_max = _profile_date_column(series)
    else:
        categorical_top_values = _categorical_top_values(series)

    return ColumnProfile(
        column_name=series.name,
        category=category,
        dtype_observed=str(series.dtype),
        missing_count=missing_count,
        missing_pct=missing_pct,
        cardinality=cardinality,
        numeric_stats=numeric_stats,
        categorical_top_values=categorical_top_values,
        date_format_observed=date_format_observed,
        date_min=date_min,
        date_max=date_max,
    )


def generate_profiling_report(
    source_path: Path | None = None, expected_column_count: int | None = EXPECTED_COLUMN_COUNT
) -> ProfilingReport:
    path = source_path or raw_inpatient_csv()
    df = load_source_csv(path, expected_column_count=expected_column_count)

    total_rows = len(df)
    lines_per_claim = df.groupby(CLM_ID_COLUMN).size()

    columns = [
        _profile_column(df[col], categorize(col), total_rows) for col in df.columns
    ]

    return ProfilingReport(
        source_file=str(path),
        generated_at=datetime.now(timezone.utc),
        total_rows=total_rows,
        total_columns=len(df.columns),
        unique_claim_count=int(df[CLM_ID_COLUMN].nunique(dropna=True)),
        unique_beneficiary_count=int(df[BENE_ID_COLUMN].nunique(dropna=True)),
        lines_per_claim_mean=float(lines_per_claim.mean()) if not lines_per_claim.empty else 0.0,
        lines_per_claim_median=float(lines_per_claim.median()) if not lines_per_claim.empty else 0.0,
        duplicate_row_count=int(df.duplicated(keep="first").sum()),
        columns=columns,
    )
