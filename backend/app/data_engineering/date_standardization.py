"""DD-Mon-YYYY -> ISO 8601 date standardization.

Every populated date cell changes representation (raw string -> ISO, or ->
null if unparseable), so every populated cell in a date column produces
exactly one QualityIssueRecord (FR-003, FR-007) -- either
`date_format_standardized` or `date_unparseable`. Missing cells are left
alone here; cleaning_service.py emits their `missing_value` record.
"""

import re
from dataclasses import dataclass, field

import pandas as pd

from app.data_engineering.schemas import QualityIssue

_DATE_PATTERN = re.compile(r"^\d{2}-[A-Za-z]{3}-\d{4}$")
_STRPTIME_FORMAT = "%d-%b-%Y"


@dataclass
class DateChange:
    row_index: int
    original_value: str
    cleaned_value: str | None
    quality_issue: QualityIssue


@dataclass
class DateStandardizationResult:
    cleaned: pd.Series
    changes: list[DateChange] = field(default_factory=list)


def standardize_date_column(series: pd.Series) -> DateStandardizationResult:
    """Vectorized: parses the whole column in one `pd.to_datetime` call
    rather than once per cell -- calling it per-scalar is ~100x slower at
    this dataset's scale (a few million date cells across all columns) and
    was the dominant cost in an earlier per-cell implementation.
    """
    non_null_mask = series.notna()
    str_series = series.astype(str).where(non_null_mask)
    format_ok = str_series.str.match(_DATE_PATTERN, na=False)

    parsed = pd.to_datetime(str_series.where(format_ok), format=_STRPTIME_FORMAT, errors="coerce")
    success = parsed.notna()
    iso = parsed.dt.strftime("%Y-%m-%d").where(success, other=None)

    changes: list[DateChange] = []
    changed_idx = series.index[non_null_mask]
    if len(changed_idx) > 0:
        orig_vals = str_series.loc[changed_idx].to_numpy()
        cleaned_vals = iso.loc[changed_idx].to_numpy()
        ok_vals = success.loc[changed_idx].to_numpy()
        for idx_val, orig, cln, ok in zip(changed_idx.to_numpy(), orig_vals, cleaned_vals, ok_vals):
            if ok:
                changes.append(DateChange(idx_val, orig, cln, QualityIssue.DATE_FORMAT_STANDARDIZED))
            else:
                changes.append(DateChange(idx_val, orig, None, QualityIssue.DATE_UNPARSEABLE))

    return DateStandardizationResult(
        cleaned=pd.Series(iso.to_numpy(), index=series.index, name=series.name),
        changes=changes,
    )
