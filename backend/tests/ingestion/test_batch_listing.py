"""spec User Story 3: every upload attempt -- accepted or rejected -- is
listable with an accurate filename/timestamp/row-count/status.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.ingestion import pipeline_runner, upload_validation
from app.ingestion.router import router as ingestion_router
from tests._db_fixtures import make_test_session
from tests.ingestion._fixtures import raw_claims_fixture, write_fixture_categories


def _client(db, monkeypatch, tmp_path, *, min_rows: int | None = 3):
    categories_path = write_fixture_categories(tmp_path)
    monkeypatch.setattr(pipeline_runner, "run", lambda *args, **kwargs: None)
    if min_rows is not None:
        monkeypatch.setattr(upload_validation, "MIN_ROWS", min_rows)

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


def test_accepted_and_rejected_uploads_both_appear_distinctly(monkeypatch, tmp_path):
    db = make_test_session()
    client = _client(db, monkeypatch, tmp_path)

    accepted = client.post(
        "/claims/upload", files={"file": ("good.csv", raw_claims_fixture(), "text/csv")}
    )
    assert accepted.status_code == 201

    rejected = client.post("/claims/upload", files={"file": ("bad.csv", b"", "text/csv")})
    assert rejected.status_code == 422

    listing = client.get("/claims/batches").json()
    assert listing["total_count"] == 2
    statuses = {b["filename"]: b["status"] for b in listing["batches"]}
    # pipeline_runner.run is stubbed to a no-op in this helper (see
    # _client), so an accepted upload stays "accepted" rather than
    # advancing to "completed" -- this test's own scope is the listing
    # endpoint's accuracy, not re-proving the full pipeline (SC-001's own
    # test, test_full_pipeline_upload.py, covers that).
    assert statuses["good.csv"] == "accepted"
    assert statuses["bad.csv"] == "rejected"

    rejected_entry = next(b for b in listing["batches"] if b["filename"] == "bad.csv")
    assert rejected_entry["rejection_reason"]["reason_code"] == "empty_file"


def test_pagination(monkeypatch, tmp_path):
    db = make_test_session()
    client = _client(db, monkeypatch, tmp_path)
    for i in range(3):
        client.post("/claims/upload", files={"file": (f"f{i}.csv", raw_claims_fixture(), "text/csv")})

    page = client.get("/claims/batches", params={"page": 1, "page_size": 1}).json()
    assert len(page["batches"]) == 1
    assert page["total_count"] == 3


def test_unknown_batch_id_returns_404(monkeypatch, tmp_path):
    db = make_test_session()
    client = _client(db, monkeypatch, tmp_path)
    response = client.get("/claims/batches/does-not-exist")
    assert response.status_code == 404
