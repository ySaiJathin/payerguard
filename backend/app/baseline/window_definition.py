"""Documented, configurable processing-window definitions for the volume
baseline (FR-001).

Windows are date-based or batch-index-based, never wall-clock -- this
dataset has no live arrival timestamps, so a literal 5/15/30-minute
window (MVP_CONTEXT.md Section 3's architecture-diagram phrasing) would
be meaningless against a static historical CSV (research.md decision).
"""

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

DAILY = "daily"
WEEKLY = "weekly"
DEFAULT_WINDOW_DEFINITION = DAILY

_CALENDAR_WINDOWS = {
    DAILY: "D",
    WEEKLY: "W",
}


@dataclass
class WindowBounds:
    window_id: str
    start: date
    end: date


def resolve_windows(date_column: pd.Series, window_definition: str = DEFAULT_WINDOW_DEFINITION) -> list[WindowBounds]:
    """Returns every window in the observed date range, in chronological
    order, including windows with no claims -- claim counting happens in
    volume_baseline.py; this function only defines the window boundaries
    so zero-claim windows (FR-010) are representable.
    """
    if window_definition not in _CALENDAR_WINDOWS:
        raise ValueError(
            f"Unknown window_definition {window_definition!r}; supported: {sorted(_CALENDAR_WINDOWS)}"
        )

    parsed = pd.to_datetime(date_column, errors="coerce").dropna()
    if parsed.empty:
        return []

    min_date = parsed.min().normalize()
    max_date = parsed.max().normalize()

    if window_definition == DAILY:
        starts = pd.date_range(min_date, max_date, freq="D")
        return [
            WindowBounds(window_id=d.strftime("%Y-%m-%d"), start=d.date(), end=d.date()) for d in starts
        ]

    # weekly: Monday-anchored, chronological, no shuffling (constitution
    # Principle VII -- Temporal Integrity)
    week_start = min_date - timedelta(days=min_date.weekday())
    starts = pd.date_range(week_start, max_date, freq="W-MON")
    if starts.empty or starts[0] > week_start:
        starts = pd.DatetimeIndex([week_start]).append(starts)
    windows = []
    for s in starts:
        e = s + timedelta(days=6)
        windows.append(WindowBounds(window_id=s.strftime("%Y-W%W"), start=s.date(), end=e.date()))
    return windows
