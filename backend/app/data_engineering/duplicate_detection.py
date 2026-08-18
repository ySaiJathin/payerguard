"""Full-row duplicate detection (FR-004).

Duplicates are excluded from the working/cleaned dataset but never deleted
from any source file -- the excluded row's existence is recoverable via its
QualityIssueRecord (research.md: "Duplicates are excluded from the working
dataset, never deleted from source").
"""

from datetime import datetime, timezone

import pandas as pd

from app.data_engineering.schemas import QualityIssue, QualityIssueRecord


def detect_and_exclude_duplicates(
    df: pd.DataFrame, row_id_map: dict[int, str]
) -> tuple[pd.DataFrame, list[QualityIssueRecord]]:
    """Returns (deduplicated_df, records) -- one record per excluded row."""
    is_duplicate = df.duplicated(keep="first")
    now = datetime.now(timezone.utc)

    records = [
        QualityIssueRecord.model_construct(
            row_identifier=row_id_map[idx],
            column_name="*",
            original_value=row_id_map[idx],
            cleaned_value=None,
            quality_issue=QualityIssue.DUPLICATE_ROW,
            detected_at=now,
        )
        for idx in df.index[is_duplicate]
    ]

    return df.loc[~is_duplicate].copy(), records
