"""Shared fixture builders for risk/benchmark tests -- not a test module
itself (no `test_` prefix, so pytest doesn't collect it)."""

from datetime import date, datetime, timedelta, timezone

import numpy as np

from app.features.selection.schemas import DateRange, TemporalSplit
from app.risk.dataset.schemas import RiskDatasetRow


def make_split(n_days: int = 100) -> TemporalSplit:
    start = date(2020, 1, 1)
    train_end = start + timedelta(days=int(n_days * 0.70))
    val_end = train_end + timedelta(days=int(n_days * 0.15))
    test_end = start + timedelta(days=n_days)
    return TemporalSplit(
        split_id="split-fixture-1",
        train_date_range=DateRange(start=start, end=train_end),
        validation_date_range=DateRange(start=train_end + timedelta(days=1), end=val_end),
        test_date_range=DateRange(start=val_end + timedelta(days=1), end=test_end),
        train_count=int(n_days * 0.70),
        validation_count=int(n_days * 0.15),
        test_count=int(n_days * 0.15),
        computed_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
    )


def make_rows(n_days: int = 100, seed: int = 0, separable: bool = True) -> list[RiskDatasetRow]:
    """Builds a window-per-day fixture risk dataset. When `separable` is
    True, the label correlates with anomaly_frequency/deviation so models
    have real signal to learn (useful for tuning/selection tests); when
    False, labels are assigned independently of the features (useful for
    exercising the "poorly discriminating" calibration path)."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_days):
        start = date(2020, 1, 1) + timedelta(days=i)
        label = 1 if rng.random() < 0.3 else 0
        if separable:
            anomaly_frequency = (0.5 if label else 0.05) + rng.random() * 0.05
            volume_deviation = (5.0 if label else 0.5) + rng.random()
        else:
            anomaly_frequency = rng.random() * 0.5
            volume_deviation = rng.random() * 5
        rows.append(
            RiskDatasetRow(
                window_id=f"W{i}",
                window_start=start,
                window_end=start,
                claim_count=10,
                gx_failure_count=2,
                anomaly_score=anomaly_frequency * 100,
                anomaly_frequency=anomaly_frequency,
                affected_claim_pct=anomaly_frequency * 100,
                volume_deviation=volume_deviation,
                amount_deviation=volume_deviation,
                historical_quality_failure_rate=5.0,
                investigation_risk_indicator=anomaly_frequency,
                investigation_risk_label=label,
            )
        )
    return rows
