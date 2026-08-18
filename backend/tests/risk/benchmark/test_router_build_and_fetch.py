from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.risk.benchmark import benchmark_log, benchmark_runner, data_loading, router as router_module
from app.risk.benchmark.errors import RiskModelInputUnavailableError
from tests.risk.benchmark._fixtures import make_rows, make_split


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router_module.router)
    return app


def test_build_then_get_results_round_trip(monkeypatch, tmp_path):
    rows = make_rows(n_days=100, seed=5)
    split = make_split(n_days=100)

    monkeypatch.setattr(data_loading, "read_risk_dataset_rows", lambda out_dir=None: rows)
    monkeypatch.setattr(data_loading, "read_temporal_split", lambda: split)
    monkeypatch.setattr(benchmark_log, "reports_dir", lambda: tmp_path)
    # Isolate model artifact persistence from the real repo data/ directory
    # -- benchmark_runner.py defaults model_out_dir to models_dir()/"risk"
    # when the router calls it without an explicit path.
    monkeypatch.setattr(benchmark_runner, "models_dir", lambda: tmp_path)

    client = TestClient(_app())

    build_response = client.post("/risk/benchmark")
    assert build_response.status_code == 200
    body = build_response.json()
    assert len(body["benchmark_results"]) == 3
    assert body["production_model_selection"]["selected_model"] in (
        "logistic_regression",
        "random_forest",
        "xgboost",
    )

    results_response = client.get("/risk/benchmark/results")
    assert results_response.status_code == 200
    assert results_response.json()["production_model_selection"]["selected_model"] == body[
        "production_model_selection"
    ]["selected_model"]

    version = body["benchmark_results"][0]["risk_dataset_version"]
    versioned_response = client.get(f"/risk/benchmark/results?risk_dataset_version={version}")
    assert versioned_response.status_code == 200


def test_build_returns_409_when_prerequisites_missing(monkeypatch):
    def _raise():
        raise RiskModelInputUnavailableError("No Phase 8 risk dataset found.")

    monkeypatch.setattr(router_module, "_run_and_persist", _raise)
    client = TestClient(_app())

    response = client.post("/risk/benchmark")
    assert response.status_code == 409


def test_get_results_returns_404_before_any_build(monkeypatch, tmp_path):
    monkeypatch.setattr(benchmark_log, "reports_dir", lambda: tmp_path)
    client = TestClient(_app())

    assert client.get("/risk/benchmark/results").status_code == 404
    assert client.get("/risk/benchmark/results?risk_dataset_version=nope").status_code == 404
