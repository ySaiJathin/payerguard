"""Assembles one WindowFeatures row per window (FR-006 through FR-009).
`anomaly_count` is always None here -- it is only ever set via the
dedicated PATCH /features/windows/{window_id}/anomaly-count enrichment
path (FR-008).
"""

import pandas as pd

from app.baseline.schemas import BaselineSnapshot
from app.baseline.window_definition import DEFAULT_WINDOW_DEFINITION
from app.data_engineering.invalid_value_detection import ReferenceStats
from app.data_engineering.schemas import ColumnCategory
from app.features.schemas import AmountStats, WindowFeatures
from app.features.window_level.deviation_features import compute_deviation_features
from app.features.window_level.window_aggregates import compute_window_aggregates


def compute_window_features(
    df: pd.DataFrame,
    categories: dict[str, ColumnCategory],
    reference_stats: ReferenceStats,
    baseline: BaselineSnapshot,
    window_definition: str = DEFAULT_WINDOW_DEFINITION,
) -> list[WindowFeatures]:
    aggregates = compute_window_aggregates(df, categories, reference_stats, window_definition)
    deviations = compute_deviation_features(aggregates, baseline, window_definition)

    rows: list[WindowFeatures] = []
    for window in aggregates:
        deviation = deviations[window["window_id"]]
        rows.append(
            WindowFeatures(
                window_id=window["window_id"],
                start=window["start"],
                end=window["end"],
                claim_count=window["claim_count"],
                amount_stats={col: AmountStats(**stats) for col, stats in window["amount_stats"].items()},
                missing_pct=window["missing_pct"],
                duplicate_pct=window["duplicate_pct"],
                invalid_status_pct=window["invalid_status_pct"],
                volume_deviation=deviation["volume_deviation"],
                amount_deviation=deviation["amount_deviation"],
                anomaly_count=None,
            )
        )
    return rows
