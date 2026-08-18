from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.hitl import accept_service, recalculation_service, reject_service
from app.hitl.router import router as hitl_router
from app.incidents import service as incidents_service
from app.incidents.router import router as incidents_router
from tests._db_fixtures import make_test_session
from tests.llm._fixtures import always_returns, make_draft


def _app_and_client(db):
    app = FastAPI()
    app.include_router(incidents_router)
    app.include_router(hitl_router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _inject_client_everywhere(monkeypatch, fake_client):
    """The router endpoints never expose Mistral-client injection over
    HTTP (correctly -- that's an internal test-only seam), so wrap each
    service's public function to always pass the fake client through."""
    real_create = incidents_service.create_incident
    monkeypatch.setattr(
        incidents_service,
        "create_incident",
        lambda db, payload, **kw: real_create(db, payload, mistral_client_override=fake_client),
    )
    real_recalculate = recalculation_service.recalculate_incident
    monkeypatch.setattr(
        recalculation_service,
        "recalculate_incident",
        lambda db, incident_id, new_evidence, **kw: real_recalculate(
            db, incident_id, new_evidence, mistral_client_override=fake_client
        ),
    )


def test_full_create_reject_recalculate_accept_flow(monkeypatch):
    db = make_test_session()
    fake_client = always_returns(make_draft())
    _inject_client_everywhere(monkeypatch, fake_client)
    # (unlike 009's router.py, incidents/router.py and hitl/router.py call
    # through `service.create_incident(...)`/`recalculation_service.
    # recalculate_incident(...)` -- a module-attribute lookup at call
    # time -- so patching the attribute on the service module, as
    # `_inject_client_everywhere` already does, is sufficient here.)

    client = _app_and_client(db)

    create_response = client.post(
        "/incidents",
        json={
            "window_id": "W1",
            "evidence": {
                "quality_check_bands": ["CRITICAL", "WARNING"],
                "anomaly_score_percentile": 0.9,
                "affected_claim_pct": 0.2,
                "risk_score": 0.6,
            },
        },
    )
    assert create_response.status_code == 201
    incident = create_response.json()
    assert incident["status"] == "ready_for_review"
    incident_id = incident["incident_id"]

    reject_response = client.post(
        f"/hitl/{incident_id}/reject",
        json={"reviewer_id": "r1", "reason_category": "false_positive", "feedback_text": "Known holiday dip."},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"

    duplicate_reject = client.post(
        f"/hitl/{incident_id}/reject",
        json={"reviewer_id": "r1", "reason_category": "other", "feedback_text": "again"},
    )
    assert duplicate_reject.status_code == 409

    recalc_response = client.post(f"/hitl/{incident_id}/recalculate", json={})
    assert recalc_response.status_code == 200
    recalc_body = recalc_response.json()
    assert recalc_body["incident"]["status"] == "ready_for_review"
    assert recalc_body["evidence_changed"] is False

    accept_response = client.post(f"/hitl/{incident_id}/accept", json={"reviewer_id": "r1"})
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"

    duplicate_accept = client.post(f"/hitl/{incident_id}/accept", json={"reviewer_id": "r1"})
    assert duplicate_accept.status_code == 409

    feedback_response = client.get(f"/hitl/{incident_id}/feedback")
    assert feedback_response.status_code == 200
    assert len(feedback_response.json()) == 1  # the original reject's feedback, preserved


def test_reject_without_feedback_returns_422(monkeypatch):
    db = make_test_session()
    fake_client = always_returns(make_draft())
    _inject_client_everywhere(monkeypatch, fake_client)

    client = _app_and_client(db)
    create_response = client.post(
        "/incidents",
        json={"window_id": "W2", "evidence": {"risk_score": 0.5}},
    )
    incident_id = create_response.json()["incident_id"]

    response = client.post(f"/hitl/{incident_id}/reject", json={"reviewer_id": "r1", "reason_category": "other"})
    assert response.status_code == 422
