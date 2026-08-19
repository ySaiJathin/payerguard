"""spec SC-005: every accepted and rejected upload produces a
corresponding audit-trail entry, and `ingestion` now reports as
registered in Phase 16's completeness check.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.audit.history_service import query_history
from app.audit.registry import check_registry_completeness
from app.core.database import get_db
from app.ingestion import pipeline_runner, upload_validation
from app.ingestion.router import router as ingestion_router
from tests._db_fixtures import make_test_session
from tests.ingestion._fixtures import raw_claims_fixture, write_fixture_categories


def _client(db, monkeypatch, tmp_path):
    categories_path = write_fixture_categories(tmp_path)
    monkeypatch.setattr(pipeline_runner, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(upload_validation, "MIN_ROWS", 3)
    original_validate = upload_validation.validate_and_load
    monkeypatch.setattr(
        upload_validation,
        "validate_and_load",
        lambda content, filename, _cp=None: original_validate(content, filename, categories_path),
    )
    app = FastAPI()
    app.include_router(ingestion_router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_accepted_and_rejected_uploads_are_both_audited(monkeypatch, tmp_path):
    db = make_test_session()
    client = _client(db, monkeypatch, tmp_path)

    accepted = client.post(
        "/claims/upload", files={"file": ("good.csv", raw_claims_fixture(), "text/csv")}
    ).json()
    # 422 responses go through FastAPI's HTTPException wrapping, so the
    # IngestedBatch dict this router raised lives under "detail".
    rejected = client.post("/claims/upload", files={"file": ("bad.csv", b"", "text/csv")}).json()["detail"]

    accepted_history = query_history(db, "batch", accepted["batch_id"])
    assert accepted_history.found is True
    assert any(e.pipeline_stage.value == "ingestion" for e in accepted_history.entries)

    rejected_history = query_history(db, "batch", rejected["batch_id"])
    assert rejected_history.found is True
    assert any(e.pipeline_stage.value == "ingestion" for e in rejected_history.entries)


def test_ingestion_registers_in_completeness_check(monkeypatch, tmp_path):
    db = make_test_session()
    client = _client(db, monkeypatch, tmp_path)
    client.post("/claims/upload", files={"file": ("good.csv", raw_claims_fixture(), "text/csv")})

    entries = {e.module_name: e for e in check_registry_completeness(db)}
    assert entries["ingestion"].registered is True
