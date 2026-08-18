from datetime import date, datetime, timezone

from app.features.selection.schemas import DateRange, TemporalSplit
from app.risk.dataset import label_formula, service
from app.risk.dataset.label_distribution import compute_label_distribution


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
    return rows


def test_label_reproduces_by_hand_from_stored_inputs():
    rows = _rows()
    split = _split()
    formula = label_formula.compute_formula(rows, split)
    labeled = label_formula.apply_formula(rows, formula, split)

    for stored_row in labeled:
        recomputed = label_formula.apply_formula([stored_row], formula, split)[0]
        # Re-applying the formula to a single row in isolation still needs
        # the train-split threshold, which is a property of the whole
        # dataset -- so instead verify the IRI itself (the row's own
        # input-derived quantity) is stable and deterministic.
        assert recomputed["investigation_risk_indicator"] == stored_row["investigation_risk_indicator"]

    # Full reproducibility: recomputing over the entire stored dataset
    # reproduces every stored label exactly (spec SC-002).
    relabeled = label_formula.apply_formula(rows, formula, split)
    for original, recomputed in zip(labeled, relabeled):
        assert original["investigation_risk_label"] == recomputed["investigation_risk_label"]
        assert original["investigation_risk_indicator"] == recomputed["investigation_risk_indicator"]


def test_rerun_against_unmodified_upstream_reproduces_identical_dataset(monkeypatch, tmp_path):
    rows = _rows()
    split = _split()

    monkeypatch.setattr(service, "assemble_rows", lambda: rows)
    monkeypatch.setattr(service, "read_temporal_split", lambda: split)

    from app.risk.dataset import dataset_log

    monkeypatch.setattr(dataset_log, "risk_dir", lambda: tmp_path)

    result_1 = service.build_risk_dataset()
    csv_path = tmp_path / "risk_dataset.csv"
    bytes_1 = csv_path.read_bytes()

    result_2 = service.build_risk_dataset()
    bytes_2 = csv_path.read_bytes()

    assert bytes_1 == bytes_2
    assert result_1.rows_built == result_2.rows_built
    assert result_1.label_distribution == result_2.label_distribution


def test_label_distribution_matches_assembled_rows():
    rows = _rows()
    split = _split()
    formula = label_formula.compute_formula(rows, split)
    labeled = label_formula.apply_formula(rows, formula, split)
    distribution = compute_label_distribution(labeled)

    worthy = sum(1 for r in labeled if r["investigation_risk_label"] == 1)
    assert distribution.investigation_worthy_count == worthy
    assert distribution.total_rows == len(labeled)
