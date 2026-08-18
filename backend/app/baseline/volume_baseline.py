"""Claim volume per processing window (FR-001, FR-010).

Every window in the observed date range appears in the output, including
windows with zero claims -- a genuinely quiet period is a real fact about
the historical data, not something to omit or interpolate away.
"""

import pandas as pd

from app.baseline.schemas import VolumeBaseline, VolumeWindow
from app.baseline.window_definition import DEFAULT_WINDOW_DEFINITION, resolve_windows

FROM_DATE_COLUMN = "CLM_FROM_DT"


def compute_volume_baseline(
    df: pd.DataFrame, window_definition: str = DEFAULT_WINDOW_DEFINITION
) -> VolumeBaseline:
    windows = resolve_windows(df[FROM_DATE_COLUMN], window_definition)

    parsed = pd.to_datetime(df[FROM_DATE_COLUMN], errors="coerce")
    normalized = parsed.dt.normalize()

    volume_windows: list[VolumeWindow] = []
    for w in windows:
        if window_definition == "daily":
            claim_count = int((normalized.dt.date == w.start).sum())
        else:
            start_ts = pd.Timestamp(w.start)
            end_ts = pd.Timestamp(w.end)
            claim_count = int(((normalized >= start_ts) & (normalized <= end_ts)).sum())
        volume_windows.append(
            VolumeWindow(window_id=w.window_id, start=w.start, end=w.end, claim_count=claim_count)
        )

    return VolumeBaseline(window_definition=window_definition, windows=volume_windows)
