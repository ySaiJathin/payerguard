"""SC-006 and FR-007: `/history` pagination, filtering, and the
distinguishable "no history found" response.

The `found` flag carries a specific meaning that is easy to implement
wrongly: it says whether *the entity* has any recorded activity, not
whether the current page/filter matched anything. Conflating the two
would make "you paged past the end" indistinguishable from "this claim
was never processed" -- which is exactly the ambiguity FR-006 exists to
remove, so both cases are asserted separately below.
"""

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.audit.aggregation_service import append_entry
from app.audit.router import router as audit_router
from app.core.database import get_db
from tests._db_fixtures import make_test_session
from tests.audit._fixtures import run_full_incident_lifecycle

BASE_TIME = datetime(2026, 8, 19, 12, 0, 0, tzinfo=timezone.utc)


def _client(db) -> TestClient:
    app = FastAPI()
    app.include_router(audit_router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_full_trail_is_returned_for_a_real_incident(monkeypatch):
    db = make_test_session()
    result = run_full_incident_lifecycle(db, monkeypatch)
    client = _client(db)

    response = client.get(f"/history/incident/{result.incident_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["total_count"] == 7
    stages = [e["pipeline_stage"] for e in body["entries"]]
    assert stages == [
        "incident_status",
        "severity_scoring",
        "llm_investigation",
        "incident_status",
        "remediation",
        "revalidation",
        "incident_status",
    ]


def test_unknown_entity_returns_200_with_found_false(monkeypatch):
    db = make_test_session()
    client = _client(db)

    response = client.get("/history/claim/does-not-exist")

    assert response.status_code == 200, "contracts/api.md specifies 200, not 404, for this case"
    body = response.json()
    assert body["found"] is False
    assert body["entries"] == []
    assert body["total_count"] == 0


def test_stage_filter_returns_only_that_stage(monkeypatch):
    db = make_test_session()
    result = run_full_incident_lifecycle(db, monkeypatch)
    client = _client(db)

    body = client.get(
        f"/history/incident/{result.incident_id}", params={"stage": "incident_status"}
    ).json()

    assert body["total_count"] == 3
    assert {e["pipeline_stage"] for e in body["entries"]} == {"incident_status"}
    assert body["found"] is True


def test_date_range_filter_returns_only_in_range_entries():
    db = make_test_session()
    for offset, record_id in enumerate(["R1", "R2", "R3"]):
        append_entry(
            db,
            entity_type="incident",
            entity_id="I1",
            pipeline_stage="incident_status",
            source_module="hitl",
            source_record_id=record_id,
            occurred_at=BASE_TIME + timedelta(days=offset),
        )
    db.commit()
    client = _client(db)

    body = client.get(
        "/history/incident/I1",
        params={
            "start_date": (BASE_TIME + timedelta(days=1)).isoformat(),
            "end_date": (BASE_TIME + timedelta(days=2)).isoformat(),
        },
    ).json()

    assert [e["source_record_id"] for e in body["entries"]] == ["R2", "R3"]
    assert body["total_count"] == 2


def test_pagination_slices_correctly_and_reports_unpaginated_total():
    db = make_test_session()
    for i in range(10):
        append_entry(
            db,
            entity_type="incident",
            entity_id="I1",
            pipeline_stage="incident_status",
            source_module="hitl",
            source_record_id=f"R{i}",
            occurred_at=BASE_TIME,
        )
    db.commit()
    client = _client(db)

    page_1 = client.get("/history/incident/I1", params={"page": 1, "page_size": 4}).json()
    page_2 = client.get("/history/incident/I1", params={"page": 2, "page_size": 4}).json()

    assert [e["source_record_id"] for e in page_1["entries"]] == ["R0", "R1", "R2", "R3"]
    assert [e["source_record_id"] for e in page_2["entries"]] == ["R4", "R5", "R6", "R7"]
    assert page_1["total_count"] == page_2["total_count"] == 10


def test_page_past_the_end_is_empty_but_still_found():
    """The FR-006 distinction: an empty page of a real history must not
    report `found: false`."""
    db = make_test_session()
    append_entry(
        db,
        entity_type="incident",
        entity_id="I1",
        pipeline_stage="incident_status",
        source_module="hitl",
        source_record_id="R1",
        occurred_at=BASE_TIME,
    )
    db.commit()
    client = _client(db)

    body = client.get("/history/incident/I1", params={"page": 99, "page_size": 10}).json()

    assert body["entries"] == []
    assert body["found"] is True, "An empty page is not the same as 'no history for this entity'."
    assert body["total_count"] == 1


def test_filter_matching_nothing_still_reports_found_true():
    """Same distinction, reached via a filter rather than pagination."""
    db = make_test_session()
    append_entry(
        db,
        entity_type="incident",
        entity_id="I1",
        pipeline_stage="incident_status",
        source_module="hitl",
        source_record_id="R1",
        occurred_at=BASE_TIME,
    )
    db.commit()
    client = _client(db)

    body = client.get("/history/incident/I1", params={"stage": "revalidation"}).json()

    assert body["entries"] == []
    assert body["total_count"] == 0
    assert body["found"] is True


def test_claim_history_is_scoped_to_that_claim(monkeypatch):
    db = make_test_session()
    run_full_incident_lifecycle(db, monkeypatch)
    client = _client(db)

    body = client.get("/history/claim/CLM-DUP").json()

    assert body["found"] is True
    assert body["total_count"] == 1
    assert body["entries"][0]["pipeline_stage"] == "remediation"
