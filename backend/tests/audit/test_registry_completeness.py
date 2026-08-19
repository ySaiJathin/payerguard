"""SC-005 / FR-008: no pipeline stage can silently skip auditing.

The guarantee has two halves and both are tested, because either alone is
worthless:

- **Positive** -- every module in `EXPECTED_AUDITED_MODULES` really does
  append an entry when exercised. Driven through the real services and
  routers, not by writing rows by hand: hand-written rows would prove the
  table accepts inserts, not that the pipeline calls `append_entry`.
- **Negative** -- the check actually fails for a module with no audit
  source. Without this, a check that returned "all registered"
  unconditionally would pass the positive half forever.
"""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.anomaly.router import router as anomaly_router
from app.audit.registry import (
    EXPECTED_AUDITED_MODULES,
    check_registry_completeness,
    registered_modules,
    unregistered_modules,
)
from app.core.database import get_db
from app.data_engineering.categorization import categorize
from app.data_engineering.cleaning_service import run_cleaning
from app.quality.router import router as quality_router
from app.risk.benchmark.router import router as risk_benchmark_router
from tests._db_fixtures import make_test_session
from tests.audit._fixtures import run_full_incident_lifecycle
from tests.data_engineering.test_cleaning_service import CLEAN_FIXTURE, FIXTURE_COLUMNS

# Modules whose audit entries the incident lifecycle produces directly.
_LIFECYCLE_MODULES = {"incidents", "risk.scoring", "llm", "hitl", "remediation", "revalidation"}


def _drive_cleaning(db, tmp_path):
    """Phase 2 cleaning through its real service, using the same fixture
    pattern `tests/data_engineering/test_cleaning_service.py` uses."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    categories = {col: categorize(col).value for col in FIXTURE_COLUMNS}
    (reports_dir / "column_categories.json").write_text(json.dumps(categories), encoding="utf-8")

    run_cleaning(
        source_path=CLEAN_FIXTURE,
        categories_dir=reports_dir,
        reference_path=CLEAN_FIXTURE,
        output_dir=tmp_path / "cleaned",
        reports_out_dir=reports_dir,
        db=db,
    )
    db.commit()


def test_ingestion_is_present_now_that_a_real_write_path_exists():
    """Through Phase 16 this test asserted `ingestion`'s *absence* (the
    continuous-ingestion phase had been removed and `app/ingestion/` had
    no write path). Spec 017-batch-file-ingestion (2026-08-20) built one --
    `app.ingestion.batch_service` appends an entry for every accepted and
    rejected upload -- so the assertion is flipped, not merely deleted, to
    keep the reasoning visible for whoever reads this test next."""
    assert "ingestion" in EXPECTED_AUDITED_MODULES


def test_data_engineering_is_deliberately_present():
    """The mirror image: research.md's list omitted it, but FR-001 and
    US1's first acceptance scenario both require Phase 2 cleaning in the
    trail."""
    assert "data_engineering" in EXPECTED_AUDITED_MODULES


def test_lifecycle_registers_every_incident_stage_module(monkeypatch):
    db = make_test_session()
    run_full_incident_lifecycle(db, monkeypatch)

    assert _LIFECYCLE_MODULES.issubset(registered_modules(db))


def test_cleaning_registers_data_engineering(tmp_path):
    db = make_test_session()
    _drive_cleaning(db, tmp_path)

    assert "data_engineering" in registered_modules(db)


def test_every_expected_module_registers_when_its_stage_runs(monkeypatch, tmp_path):
    """The positive half of SC-005, across all eleven modules."""
    db = make_test_session()

    run_full_incident_lifecycle(db, monkeypatch)
    _drive_cleaning(db, tmp_path)
    _drive_batch_routers(db, monkeypatch, tmp_path)
    _drive_ingestion(db, monkeypatch)

    gaps = unregistered_modules(db)
    assert not gaps, (
        f"These modules are expected to contribute audit entries but produced none: {gaps}. "
        "Either the module's write path is missing an append_entry call, or it should not be "
        "in EXPECTED_AUDITED_MODULES."
    )


def test_completeness_check_fails_for_a_module_with_no_audit_source(monkeypatch):
    """The negative half of SC-005 -- proves the check is not vacuous."""
    db = make_test_session()
    run_full_incident_lifecycle(db, monkeypatch)

    expected_with_mock = {**EXPECTED_AUDITED_MODULES, "mock_new_stage": ["MockRecord"]}
    entries = check_registry_completeness(db, expected_with_mock)
    by_name = {e.module_name: e for e in entries}

    assert by_name["mock_new_stage"].registered is False
    assert "mock_new_stage" in unregistered_modules(db, expected_with_mock)
    # And the modules that DID run still register -- the check reports the
    # real gap without collapsing everything to "incomplete".
    assert by_name["incidents"].registered is True


def _drive_batch_routers(db, monkeypatch, tmp_path):
    """Anomaly, risk-benchmark, and quality append from their routers, so
    they are driven through TestClient with their heavy pipeline work
    stubbed -- the append call under test is the router's, not the
    model-fitting behind it (which Phases 3/7/9 already test themselves).
    """
    from app.anomaly import router as anomaly_router_module
    from app.anomaly.schemas import BenchmarkRunResult, ModelType, ProductionModelSelection
    from app.quality import router as quality_router_module
    from app.quality.schemas import QualityScoreResult
    from app.risk.benchmark import router as risk_router_module
    from app.risk.benchmark.schemas import ModelType as RiskModelType
    from app.risk.benchmark.schemas import ProductionRiskModelSelection, RiskBenchmarkRunResult
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    monkeypatch.setattr(
        anomaly_router_module,
        "run_benchmark",
        lambda: BenchmarkRunResult(
            benchmark_results=[],
            production_model_selection=ProductionModelSelection(
                selected_model=ModelType.hbos,
                ranking_rule="test",
                tie_break_applied=False,
                benchmark_result_ids=["anom-result-1"],
                selected_at=now,
            ),
        ),
    )
    monkeypatch.setattr(
        risk_router_module,
        "_run_and_persist",
        lambda: RiskBenchmarkRunResult(
            benchmark_results=[],
            production_model_selection=ProductionRiskModelSelection(
                selected_model=RiskModelType.xgboost,
                ranking_rule="test",
                pr_auc_floor_used=0.0,
                tie_break_applied=False,
                benchmark_result_ids=["risk-result-1"],
                selected_at=now,
            ),
            data_scale_warning=None,
        ),
    )
    monkeypatch.setattr(
        quality_router_module,
        "run_validation",
        lambda: QualityScoreResult(
            run_id="qual-run-1",
            batch_source="fixture",
            composite_score=90.0,
            weights_used={},
            contributing_check_ids=["chk-1", "chk-2"],
            generated_at=now,
        ),
    )

    app = FastAPI()
    app.include_router(anomaly_router)
    app.include_router(risk_benchmark_router)
    app.include_router(quality_router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    assert client.post("/anomaly/benchmark").status_code == 200
    assert client.post("/risk/benchmark").status_code == 200
    assert client.post("/quality/validate").status_code == 200


def _drive_ingestion(db, monkeypatch):
    """`ingestion.batch_service.create_batch` appends its audit entry the
    moment an upload is accepted, before `pipeline_runner.run` does any
    heavy work -- so stubbing `pipeline_runner.run` to a no-op still
    exercises the append call under test, matching `_drive_batch_routers`'
    pattern of stubbing the model-fitting behind a router, not the append
    itself."""
    from app.ingestion import pipeline_runner
    from app.ingestion.router import router as ingestion_router

    monkeypatch.setattr(pipeline_runner, "run", lambda *args, **kwargs: None)

    app = FastAPI()
    app.include_router(ingestion_router)
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    content = CLEAN_FIXTURE.read_bytes()
    response = client.post("/claims/upload", files={"file": ("inpatient_sample.csv", content, "text/csv")})
    assert response.status_code in (201, 422), response.text
