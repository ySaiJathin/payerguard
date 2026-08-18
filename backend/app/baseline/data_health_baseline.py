"""Historical missingness/duplicate/status-distribution baseline (FR-003,
FR-004).

Missingness and duplicate figures are sourced from Phase 3's persisted
`ExpectationCheckResult`s rather than independently recomputed, so this
baseline can never silently diverge from what Phase 3 itself measured on
the same batch (research.md decision).
"""

import pandas as pd

from app.baseline.schemas import DataHealthBaseline
from app.quality.schemas import ExpectationCheckResult, ExpectationType

STATUS_COLUMN = "PTNT_DSCHRG_STUS_CD"


def compute_data_health_baseline(
    df: pd.DataFrame,
    check_results: list[ExpectationCheckResult],
    categorical_columns: list[str] | None = None,
) -> DataHealthBaseline:
    categorical_columns = categorical_columns or [STATUS_COLUMN]

    missing_rate_by_column = {
        c.column_name: c.computed_rate_or_count
        for c in check_results
        if c.expectation_type == ExpectationType.COMPLETENESS and c.column_name is not None
    }

    duplicate_checks = [c for c in check_results if c.expectation_type == ExpectationType.DUPLICATE_RATE]
    duplicate_rate = duplicate_checks[0].computed_rate_or_count if duplicate_checks else 0.0

    categorical_distributions: dict[str, dict[str, int]] = {}
    for column in categorical_columns:
        if column not in df.columns:
            continue
        value_counts = df[column].dropna().astype(str).value_counts()
        categorical_distributions[column] = {str(k): int(v) for k, v in value_counts.items()}

    return DataHealthBaseline(
        historical_missing_rate_by_column=missing_rate_by_column,
        historical_duplicate_rate=duplicate_rate,
        categorical_distributions=categorical_distributions,
    )
