"""Spec SC-003 / US3 Acceptance Scenario 3: an incident is never marked
"resolved" while any `ManualActionRequired` record remains outstanding
from the `RemediationRun` being revalidated, even if every recomputed
signal otherwise clears.
"""

from app.revalidation.revalidation_service import run_revalidation
from tests._db_fixtures import make_test_session
from tests.revalidation._fixtures import (
    make_anomaly_artifact,
    make_incident,
    make_remediation_run,
    make_revalidation_request,
    make_risk_artifact,
    patch_recompute_dependencies,
)


def _clean_artifacts():
    # Low anomaly raw score (well under the p95 threshold) and low risk
    # probability -- signals that clear every criterion on their own.
    anomaly_artifact = make_anomaly_artifact(scores=[0.1], feature_columns=["f1", "f2"], p95_threshold=5.0)
    risk_artifact = make_risk_artifact(probabilities=[0.05], feature_columns=["f1", "f2"])
    return anomaly_artifact, risk_artifact


def test_clean_signals_and_no_manual_actions_resolves(monkeypatch):
    db = make_test_session()
    anomaly_artifact, risk_artifact = _clean_artifacts()
    patch_recompute_dependencies(monkeypatch, anomaly_artifact, risk_artifact)

    incident = make_incident(db, status="accepted")
    run_id = make_remediation_run(db, incident.incident_id, completed=True, with_manual_action=False)

    response = run_revalidation(db, incident.incident_id, make_revalidation_request(remediation_run_id=run_id))

    assert response.resolution.outcome == "resolved"
    assert response.resolution.blocked_by_manual_actions is False
    assert response.incident_status == "resolved"


def test_outstanding_manual_action_blocks_resolved_even_with_clean_signals(monkeypatch):
    db = make_test_session()
    anomaly_artifact, risk_artifact = _clean_artifacts()
    patch_recompute_dependencies(monkeypatch, anomaly_artifact, risk_artifact)

    incident = make_incident(db, status="accepted")
    run_id = make_remediation_run(db, incident.incident_id, completed=True, with_manual_action=True)

    response = run_revalidation(db, incident.incident_id, make_revalidation_request(remediation_run_id=run_id))

    assert response.resolution.outcome != "resolved"
    assert response.resolution.outcome == "reopened"
    assert response.resolution.blocked_by_manual_actions is True
    assert response.incident_status == "reopened"
