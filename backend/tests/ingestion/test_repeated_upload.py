"""spec SC-003, Edge Cases bullet 5: repeated/near-simultaneous uploads
never collide -- each gets its own distinct, independently-tracked batch.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.ingestion import pipeline_runner
from app.ingestion.router import router as ingestion_router
from tests._db_fixtures import make_test_session
from tests.ingestion._fixtures import raw_claims_fixture, write_fixture_categories


def _client(db, monkeypatch, tmp_path):
    categories_path = write_fixture_categories(tmp_path)
    monkeypatch.setattr(pipeline_runner, "run", lambda *args, **kwargs: None)

    from app.ingestion import upload_validation

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


def test_same_file_uploaded_five_times_produces_five_distinct_batches(monkeypatch, tmp_path):
    db = make_test_session()
    client = _client(db, monkeypatch, tmp_path)
    content = raw_claims_fixture()

    batch_ids = []
    for _ in range(5):
        response = client.post("/claims/upload", files={"file": ("inpatient.csv", content, "text/csv")})
        assert response.status_code == 201, response.text
        batch_ids.append(response.json()["batch_id"])

    assert len(set(batch_ids)) == 5, "every upload must get its own independent batch_id"

    listing = client.get("/claims/batches", params={"page_size": 10}).json()
    assert listing["total_count"] == 5
    stored_paths = {b["stored_path"] for b in listing["batches"]}
    assert len(stored_paths) == 5, "no two batches share the same storage path"


def test_different_file_after_repeats_is_its_own_sixth_batch(monkeypatch, tmp_path):
    db = make_test_session()
    client = _client(db, monkeypatch, tmp_path)
    content = raw_claims_fixture()

    for _ in range(3):
        client.post("/claims/upload", files={"file": ("a.csv", content, "text/csv")})

    other = content.replace(b"5001", b"5099")
    response = client.post("/claims/upload", files={"file": ("b.csv", other, "text/csv")})
    assert response.status_code == 201

    listing = client.get("/claims/batches", params={"page_size": 10}).json()
    assert listing["total_count"] == 4
