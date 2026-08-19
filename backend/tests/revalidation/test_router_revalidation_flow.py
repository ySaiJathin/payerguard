"""End-to-end HTTP flow: revalidate a completed 013 `RemediationRun` and
confirm the full response shape, incident-status transition, and history
persistence -- mirroring `backend/tests/remediation/test_router_
remediation_flow.py`'s pattern.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.revalidation.router import router as revalidation_router
from tests._db_fixtures import make_test_session
from tests.revalidation._fixtures import (
    make_anomaly_artifact,
    make_incident,
    make_remediation_run,
    make_risk_artifact,
    patch_recompute_dependencies,
)


def _app_and_client(db):
    app = FastAPI()
    app.include_router(revalidation_router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _request_body(remediation_run_id: str) -> dict:
    return {
        "remediation_run_id": remediation_run_id,
        "current_claims": [
            {
                "claim_id": "1001",
                "raw_fields": {
                    "BENE_ID": "5001",
                    "CLM_FROM_DT": "2015-04-01",
                    "CLM_THRU_DT": "2015-04-05",
                    "CLM_PMT_AMT": 1200.50,
                    "CLM_IP_ADMSN_TYPE_CD": "1",
                    "PRNCPAL_DGNS_CD": "I10",
                    "OT_PHYSN_UPIN": "UPIN001",
                    "CLM_LINE_NUM": "1",
                },
            }
        ],
        "anomaly_features": {"f1": 1.0, "f2": 2.0},
        "risk_features": {"f1": 1.0, "f2": 2.0},
    }


def test_full_revalidation_flow_over_http(monkeypatch):
    db = make_test_session()
    anomaly_artifact = make_anomaly_artifact(scores=[0.1], feature_columns=["f1", "f2"])
    risk_artifact = make_risk_artifact(probabilities=[0.05], feature_columns=["f1", "f2"])
    patch_recompute_dependencies(monkeypatch, anomaly_artifact, risk_artifact)

    incident = make_incident(db, status="accepted")
    # An outstanding manual action blocks "resolved" (FR-007) -- the
    # incident lands on "reopened", which spec Edge Cases bullet 4
    # explicitly expects to support a further revalidation cycle after a
    # reviewer applies additional manual fixes.
    run_id = make_remediation_run(db, incident.incident_id, completed=True, with_manual_action=True)
    client = _app_and_client(db)

    response = client.post(f"/revalidation/{incident.incident_id}/run", json=_request_body(run_id))
    assert response.status_code == 200
    body = response.json()
    assert "revalidation_run" in body
    assert "comparison" in body
    assert "resolution" in body
    assert body["incident_status"] == "reopened"

    history_response = client.get(f"/revalidation/{incident.incident_id}")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["revalidation_run"]["revalidation_id"] == body["revalidation_run"]["revalidation_id"]

    # A reviewer applies further manual fixes and re-triggers remediation
    # (a new remediation_run_id) then revalidation again (spec Edge Cases
    # bullet 4) -- each revalidation is its own distinct, timestamped
    # record, never overwriting a prior one (FR-011/SC-005).
    second_run_id = make_remediation_run(
        db, incident.incident_id, completed=True, with_manual_action=True, claim_id="CLM2002"
    )
    second_response = client.post(f"/revalidation/{incident.incident_id}/run", json=_request_body(second_run_id))
    assert second_response.status_code == 200
    second_body = second_response.json()
    assert second_body["revalidation_run"]["revalidation_id"] != body["revalidation_run"]["revalidation_id"]

    history_after_second = client.get(f"/revalidation/{incident.incident_id}").json()
    assert len(history_after_second) == 2


def test_run_against_incomplete_remediation_returns_409(monkeypatch):
    db = make_test_session()
    anomaly_artifact = make_anomaly_artifact(scores=[0.1], feature_columns=["f1", "f2"])
    risk_artifact = make_risk_artifact(probabilities=[0.05], feature_columns=["f1", "f2"])
    patch_recompute_dependencies(monkeypatch, anomaly_artifact, risk_artifact)

    incident = make_incident(db, status="accepted")
    run_id = make_remediation_run(db, incident.incident_id, completed=False)
    client = _app_and_client(db)

    response = client.post(f"/revalidation/{incident.incident_id}/run", json=_request_body(run_id))
    assert response.status_code == 409
