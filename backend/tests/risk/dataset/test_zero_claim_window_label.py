from datetime import date, datetime, timezone

from app.features.selection.schemas import DateRange, TemporalSplit
from app.risk.dataset import label_formula


def _split() -> TemporalSplit:
    return TemporalSplit(
        split_id="split-1",
        train_date_range=DateRange(start=date(2020, 1, 1), end=date(2020, 1, 21)),
        validation_date_range=DateRange(start=date(2020, 1, 22), end=date(2020, 1, 28)),
        test_date_range=DateRange(start=date(2020, 1, 29), end=date(2020, 2, 4)),
        train_count=70,
        validation_count=15,
        test_count=15,
        computed_at=datetime(2022, 1, 1, tzinfo=timezone.utc),
    )


def _rows(zero_claim_extreme: bool) -> list[dict]:
    rows = []
    for i in range(10):
        start = date(2020, 1, 1 + i * 3)
        rows.append(
            {
                "window_id": f"W{i}",
                "window_start": start,
                "window_end": start,
                "claim_count": 10 + i,
                "gx_failure_count": 3,
                "anomaly_score": (i % 4) * 25.0,
                "anomaly_frequency": (i % 4) / 4,
                "affected_claim_pct": (i % 4) * 10.0,
                "volume_deviation": float(i - 5),
                "amount_deviation": float(i * 2),
                "historical_quality_failure_rate": 4.0 + i,
            }
        )

    # A zero-claim window whose raw signals would otherwise clear the
    # threshold by a wide margin (max anomaly frequency + max deviation) --
    # the label MUST still be forced to 0 (spec FR-006, SC-004).
    extreme = 1.0 if zero_claim_extreme else 0.0
    rows.append(
        {
            "window_id": "W-zero",
            "window_start": date(2020, 2, 6),
            "window_end": date(2020, 2, 6),
            "claim_count": 0,
            "gx_failure_count": 3,
            "anomaly_score": 100.0 * extreme,
            "anomaly_frequency": extreme,
            "affected_claim_pct": 0.0,
            "volume_deviation": 999.0 * extreme,
            "amount_deviation": 999.0 * extreme,
            "historical_quality_failure_rate": 99.0 * extreme,
        }
    )
    return rows


def test_zero_claim_window_label_forced_to_zero_even_when_iri_would_clear_threshold():
    rows = _rows(zero_claim_extreme=True)
    split = _split()
    formula = label_formula.compute_formula(rows, split)
    labeled = label_formula.apply_formula(rows, formula, split)

    zero_claim_row = next(r for r in labeled if r["window_id"] == "W-zero")
    assert zero_claim_row["investigation_risk_label"] == 0
    # The IRI itself is still computed honestly (not zeroed/hidden) --
    # only the label is forced, per FR-006's documented exception.
    assert zero_claim_row["investigation_risk_indicator"] > 0
