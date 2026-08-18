from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.selection.schemas import DateRange, TemporalSplit
from app.risk.dataset import dataset_log, router as router_module, service
from app.risk.dataset.errors import RiskDatasetInputUnavailableError


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


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router_module.router)
    return app


def test_build_then_get_dataset_and_label_formula(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "assemble_rows", lambda: _rows())
    monkeypatch.setattr(service, "read_temporal_split", lambda: _split())
    monkeypatch.setattr(dataset_log, "risk_dir", lambda: tmp_path)

    client = TestClient(_app())

    build_response = client.post("/risk/dataset/build")
    assert build_response.status_code == 200
    body = build_response.json()
    assert body["rows_built"] == 10
    assert body["formula_version"] == "v1"
    assert body["label_distribution"]["total_rows"] == 10

    dataset_response = client.get("/risk/dataset")
    assert dataset_response.status_code == 200
    assert len(dataset_response.json()) == 10

    formula_response = client.get("/risk/dataset/label-formula")
    assert formula_response.status_code == 200
    assert "section 2.4" in formula_response.json()["rationale_text"].lower()


def test_build_returns_409_when_prerequisites_missing(monkeypatch):
    def _raise():
        raise RiskDatasetInputUnavailableError("No Phase 6 temporal split found.")

    # router.py imports build_risk_dataset by name, so the router's own
    # bound reference must be patched directly (patching service.py's copy
    # would not affect router.py's already-imported name).
    monkeypatch.setattr(router_module, "build_risk_dataset", _raise)
    client = TestClient(_app())

    response = client.post("/risk/dataset/build")
    assert response.status_code == 409


def test_get_dataset_returns_404_before_any_build(monkeypatch, tmp_path):
    monkeypatch.setattr(dataset_log, "risk_dir", lambda: tmp_path)
    client = TestClient(_app())

    assert client.get("/risk/dataset").status_code == 404
    assert client.get("/risk/dataset/label-formula").status_code == 404
