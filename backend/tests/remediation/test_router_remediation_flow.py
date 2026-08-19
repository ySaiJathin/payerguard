"""End-to-end HTTP flow: accept an incident via `hitl`, then remediate it
via `remediation` -- mirrors backend/tests/hitl/test_router_hitl_flow.py's
pattern. Uses an ORM-level incident fixture (status="ready_for_review")
rather than POST /incidents, so this test doesn't need Phase 11's LLM
client -- accepting via `hitl` doesn't call it either.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.hitl.router import router as hitl_router
from app.remediation.router import router as remediation_router
from tests._db_fixtures import make_test_session
from tests.remediation._fixtures import make_incident


def _app_and_client(db):
    app = FastAPI()
    app.include_router(hitl_router)
    app.include_router(remediation_router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_full_accept_then_remediate_flow_covers_every_affected_claim():
    db = make_test_session()
    incident = make_incident(db, status="ready_for_review")
    client = _app_and_client(db)

    accept_response = client.post(f"/hitl/{incident.incident_id}/accept", json={"reviewer_id": "r1"})
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"

    run_response = client.post(
        f"/remediation/{incident.incident_id}/run",
        json={
            "affected_claims": [
                {"claim_id": "CLM-DUP", "is_duplicate": True},
                {"claim_id": "CLM-STATUS", "fields": {"PTNT_DSCHRG_STUS_CD": "01"}},
                {"claim_id": "CLM-IMPUTE", "fields": {"ADMTG_DGNS_CD": None}},
                {"claim_id": "CLM-UNHANDLED", "fields": {"PTNT_DSCHRG_STUS_CD": "1", "ADMTG_DGNS_CD": "J45"}},
            ]
        },
    )
    assert run_response.status_code == 200
    run_body = run_response.json()

    handled_ids = {a["claim_id"] for a in run_body["actions"]}
    manual_ids = {m["claim_id"] for m in run_body["manual_actions_required"]}
    assert handled_ids == {"CLM-DUP", "CLM-STATUS", "CLM-IMPUTE"}
    assert manual_ids == {"CLM-UNHANDLED"}

    history_response = client.get(f"/remediation/{incident.incident_id}")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["run_id"] == run_body["run_id"]


def test_get_history_404s_when_no_runs_exist_yet():
    db = make_test_session()
    incident = make_incident(db, status="accepted")
    client = _app_and_client(db)

    response = client.get(f"/remediation/{incident.incident_id}")
    assert response.status_code == 404


def test_run_against_non_accepted_incident_returns_409():
    db = make_test_session()
    incident = make_incident(db, status="pending_investigation")
    client = _app_and_client(db)

    response = client.post(f"/remediation/{incident.incident_id}/run", json={"affected_claims": []})
    assert response.status_code == 409
