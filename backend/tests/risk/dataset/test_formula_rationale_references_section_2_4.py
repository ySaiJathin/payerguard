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


def _rows() -> list[dict]:
    rows = []
    for i in range(5):
        start = date(2020, 1, 1 + i * 3)
        rows.append(
            {
                "window_id": f"W{i}",
                "window_start": start,
                "window_end": start,
                "claim_count": 10,
                "gx_failure_count": 1,
                "anomaly_score": 10.0,
                "anomaly_frequency": 0.1,
                "affected_claim_pct": 10.0,
                "volume_deviation": 1.0,
                "amount_deviation": 1.0,
                "historical_quality_failure_rate": 5.0,
            }
        )
    return rows


def test_formula_rationale_and_markdown_reference_section_2_4():
    formula = label_formula.compute_formula(_rows(), _split())
    assert "section 2.4" in formula.rationale_text.lower()

    markdown = label_formula.render_formula_markdown(formula)
    assert "section 2.4" in markdown.lower()
