"""Per-window claim count, amount stats, missingness/duplicate/invalid-
status % (FR-006, FR-009), reusing Phase 4's window definition (every
window, including zero-claim windows, gets a row) and Phase 2's reference-
value-set methodology for invalid-status detection.
"""

import pandas as pd

from app.baseline.window_definition import DEFAULT_WINDOW_DEFINITION, WindowBounds, resolve_windows
from app.data_engineering.invalid_value_detection import ReferenceStats
from app.data_engineering.schemas import ColumnCategory

FROM_DATE_COLUMN = "CLM_FROM_DT"
STATUS_COLUMN = "PTNT_DSCHRG_STUS_CD"


def _window_slice(df: pd.DataFrame, normalized: pd.Series, window: WindowBounds, window_definition: str) -> pd.DataFrame:
    if window_definition == "daily":
        mask = normalized.dt.date == window.start
    else:
        start_ts = pd.Timestamp(window.start)
        end_ts = pd.Timestamp(window.end)
        mask = (normalized >= start_ts) & (normalized <= end_ts)
    return df.loc[mask]


def _amount_stats(window_df: pd.DataFrame, amount_columns: list[str]) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    for column in amount_columns:
        if column not in window_df.columns:
            continue
        series = pd.to_numeric(window_df[column], errors="coerce").dropna()
        if series.empty:
            continue
        stats[column] = {"mean": float(series.mean()), "median": float(series.median()), "std": float(series.std(ddof=0))}
    return stats


def compute_window_aggregates(
    df: pd.DataFrame,
    categories: dict[str, ColumnCategory],
    reference_stats: ReferenceStats,
    window_definition: str = DEFAULT_WINDOW_DEFINITION,
) -> list[dict]:
    windows = resolve_windows(df[FROM_DATE_COLUMN], window_definition)
    normalized = pd.to_datetime(df[FROM_DATE_COLUMN], errors="coerce").dt.normalize()
    amount_columns = [col for col, cat in categories.items() if cat == ColumnCategory.AMOUNT]
    known_status_values = reference_stats.known_values.get(STATUS_COLUMN, set())

    rows: list[dict] = []
    for window in windows:
        window_df = _window_slice(df, normalized, window, window_definition)
        claim_count = len(window_df)

        if claim_count == 0:
            missing_pct = 0.0
            duplicate_pct = 0.0
            invalid_status_pct = 0.0
        else:
            missing_pct = float(window_df.isna().to_numpy().mean() * 100)
            duplicate_pct = float(window_df.duplicated().mean() * 100)
            status = window_df[STATUS_COLUMN].dropna().astype(str) if STATUS_COLUMN in window_df.columns else pd.Series(dtype=str)
            invalid_status_pct = (
                float((~status.isin(known_status_values)).mean() * 100) if not status.empty else 0.0
            )

        rows.append(
            {
                "window_id": window.window_id,
                "start": window.start,
                "end": window.end,
                "claim_count": claim_count,
                "amount_stats": _amount_stats(window_df, amount_columns),
                "missing_pct": missing_pct,
                "duplicate_pct": duplicate_pct,
                "invalid_status_pct": invalid_status_pct,
            }
        )
    return rows
