"""The demo API surface, including upload schema rejection."""

import pytest
from fastapi.testclient import TestClient

from app.demo import batches, paths, upload
from app.main import app


@pytest.fixture(scope="module")
def client():
    # As a context manager, so the app's lifespan runs and `init_db()`
    # creates the tables -- without it these tests only pass on a machine
    # that happens to already have a populated payerguard.db.
    with TestClient(app) as test_client:
        yield test_client


def test_batches_endpoint_lists_the_three_demo_batches(client):
    response = client.get("/demo/batches")
    assert response.status_code == 200
    body = response.json()
    assert [entry["batch_id"] for entry in body] == ["batch-1", "batch-2", "batch-3"]
    assert all(entry["injected_rows"] > 0 for entry in body)


def test_unknown_simulation_run_is_a_404_that_says_where_to_look(client):
    response = client.get("/demo/simulation/does-not-exist")
    assert response.status_code == 404
    assert "/demo/pipeline/runs" in response.json()["detail"]


def test_empty_upload_is_rejected(client):
    response = client.post("/demo/upload", files={"file": ("empty.csv", b"", "text/csv")})
    assert response.status_code == 422


def test_upload_with_the_wrong_schema_names_what_is_missing(client):
    response = client.post(
        "/demo/upload", files={"file": ("wrong.csv", b"a,b,c\n1,2,3\n", "text/csv")}
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "missing" in detail
    assert "CLM_ID" in detail


def test_upload_with_too_few_rows_is_rejected():
    header = ",".join(batches.load_column_profile()["column_order"])
    row = ",".join([""] * len(header.split(",")))
    content = (header + "\n" + row + "\n").encode()
    with pytest.raises(upload.UploadSchemaError) as excinfo:
        upload.validate_and_load(content, "tiny.csv")
    assert "CLM_ID" in str(excinfo.value) or "row" in str(excinfo.value)


def test_a_generated_batch_file_passes_upload_validation():
    path = paths.batch_csv_path("batch-3")
    if not path.exists():
        batches.ensure_generated()
    frame, labels = upload.validate_and_load(path.read_bytes(), "batch-3.csv")
    assert len(frame) > 0
    assert (labels == "none").all(), "an uploaded file has no injected ground truth to claim"
