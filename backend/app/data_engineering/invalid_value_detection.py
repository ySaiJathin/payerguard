"""Invalid-value detection (FR-005): flags without altering the value.

Per research.md, thresholds are derived from the data itself rather than
hardcoded:
- the plausible date range is the observed min/max across a reference
  file's date columns, computed fresh at run time (never a constant --
  constitution Principle II; MVP_CONTEXT.md's stated 2015-04-01..2022-10-31
  was found stale during Phase 1 implementation), plus a documented slack
  window;
- the "known code set" for a categorical/diagnosis column is the set of
  values actually observed in that same reference file for that column.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from app.data_engineering.date_standardization import standardize_date_column
from app.data_engineering.schemas import ColumnCategory, QualityIssue, QualityIssueRecord

DATE_RANGE_SLACK_DAYS = 365
_CODE_SET_CATEGORIES = (ColumnCategory.CATEGORICAL_CODE, ColumnCategory.DIAGNOSIS_PROCEDURE_CODE)
_NUMERIC_NONNEGATIVE_CATEGORIES = (ColumnCategory.AMOUNT, ColumnCategory.UTILIZATION_DURATION)


@dataclass
class ReferenceStats:
    date_min: date | None
    date_max: date | None
    known_values: dict[str, set[str]]


def build_reference_stats(
    reference_df: pd.DataFrame, categories: dict[str, ColumnCategory]
) -> ReferenceStats:
    observed_dates: list[date] = []
    known_values: dict[str, set[str]] = {}

    for column in reference_df.columns:
        category = categories.get(column)
        if category == ColumnCategory.DATE:
            result = standardize_date_column(reference_df[column])
            for change in result.changes:
                if change.cleaned_value is not None:
                    observed_dates.append(date.fromisoformat(change.cleaned_value))
        elif category in _CODE_SET_CATEGORIES:
            known_values[column] = set(reference_df[column].dropna().astype(str))

    date_min = min(observed_dates) if observed_dates else None
    date_max = max(observed_dates) if observed_dates else None
    return ReferenceStats(date_min=date_min, date_max=date_max, known_values=known_values)


def detect_invalid_values(
    df: pd.DataFrame,
    categories: dict[str, ColumnCategory],
    row_id_map: dict[int, str],
    reference_stats: ReferenceStats,
) -> list[QualityIssueRecord]:
    """`row_id_map` is a plain dict, not a pandas Series -- see dtype_conversion
    .convert_dtypes for why (per-cell `.loc[idx]` lookups don't scale here).
    """
    now = datetime.now(timezone.utc)
    records: list[QualityIssueRecord] = []

    plausible_min = plausible_max = None
    if reference_stats.date_min is not None and reference_stats.date_max is not None:
        slack = timedelta(days=DATE_RANGE_SLACK_DAYS)
        plausible_min = reference_stats.date_min - slack
        plausible_max = reference_stats.date_max + slack

    for column in df.columns:
        category = categories.get(column)
        series = df[column]

        if category in _NUMERIC_NONNEGATIVE_CATEGORIES:
            invalid_idx = series.index[series.notna() & (series < 0)]
            for idx, value in zip(invalid_idx.to_numpy(), series.loc[invalid_idx].to_numpy()):
                records.append(
                    QualityIssueRecord.model_construct(
                        row_identifier=row_id_map[idx],
                        column_name=column,
                        original_value=str(value),
                        cleaned_value=str(value),
                        quality_issue=QualityIssue.INVALID_VALUE_NEGATIVE_AMOUNT,
                        detected_at=now,
                    )
                )
        elif category == ColumnCategory.DATE and plausible_min is not None:
            populated = series.dropna()
            if not populated.empty:
                parsed = pd.to_datetime(populated, format="%Y-%m-%d", errors="coerce")
                out_of_range = populated.index[(parsed.dt.date < plausible_min) | (parsed.dt.date > plausible_max)]
                for idx, value in zip(out_of_range.to_numpy(), populated.loc[out_of_range].to_numpy()):
                    records.append(
                        QualityIssueRecord.model_construct(
                            row_identifier=row_id_map[idx],
                            column_name=column,
                            original_value=value,
                            cleaned_value=value,
                            quality_issue=QualityIssue.INVALID_VALUE_DATE_OUT_OF_RANGE,
                            detected_at=now,
                        )
                    )
        elif category in _CODE_SET_CATEGORIES:
            known = reference_stats.known_values.get(column, set())
            populated = series.dropna()
            if not populated.empty:
                unrecognized_idx = populated.index[~populated.astype(str).isin(known)]
                for idx, value in zip(unrecognized_idx.to_numpy(), populated.loc[unrecognized_idx].to_numpy()):
                    records.append(
                        QualityIssueRecord.model_construct(
                            row_identifier=row_id_map[idx],
                            column_name=column,
                            original_value=str(value),
                            cleaned_value=str(value),
                            quality_issue=QualityIssue.UNRECOGNIZED_CODE,
                            detected_at=now,
                        )
                    )

    return records
