"""Spec SC-006 / Edge Cases bullet 1: revalidation refuses to run against
a `remediation_run_id` that isn't complete (or doesn't exist on the
incident), rather than drawing a premature conclusion from a partial
remediation.
"""

import pytest
from sqlalchemy import select

from app.revalidation.errors import IncompleteRemediationRunError
from app.revalidation.models import RevalidationRun as RevalidationRunORM
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


def test_incomplete_remediation_run_is_refused(monkeypatch):
    db = make_test_session()
    anomaly_artifact = make_anomaly_artifact(scores=[0.1], feature_columns=["f1", "f2"])
    risk_artifact = make_risk_artifact(probabilities=[0.05], feature_columns=["f1", "f2"])
    patch_recompute_dependencies(monkeypatch, anomaly_artifact, risk_artifact)

    incident = make_incident(db, status="accepted")
    run_id = make_remediation_run(db, incident.incident_id, completed=False)

    with pytest.raises(IncompleteRemediationRunError):
        run_revalidation(db, incident.incident_id, make_revalidation_request(remediation_run_id=run_id))

    rows = db.execute(select(RevalidationRunORM)).scalars().all()
    assert rows == []


def test_unknown_remediation_run_id_is_refused(monkeypatch):
    db = make_test_session()
    anomaly_artifact = make_anomaly_artifact(scores=[0.1], feature_columns=["f1", "f2"])
    risk_artifact = make_risk_artifact(probabilities=[0.05], feature_columns=["f1", "f2"])
    patch_recompute_dependencies(monkeypatch, anomaly_artifact, risk_artifact)

    incident = make_incident(db, status="accepted")
    make_remediation_run(db, incident.incident_id, completed=True)

    with pytest.raises(IncompleteRemediationRunError):
        run_revalidation(db, incident.incident_id, make_revalidation_request(remediation_run_id="does-not-exist"))


def test_completed_remediation_run_succeeds(monkeypatch):
    db = make_test_session()
    anomaly_artifact = make_anomaly_artifact(scores=[0.1], feature_columns=["f1", "f2"])
    risk_artifact = make_risk_artifact(probabilities=[0.05], feature_columns=["f1", "f2"])
    patch_recompute_dependencies(monkeypatch, anomaly_artifact, risk_artifact)

    incident = make_incident(db, status="accepted")
    run_id = make_remediation_run(db, incident.incident_id, completed=True)

    response = run_revalidation(db, incident.incident_id, make_revalidation_request(remediation_run_id=run_id))
    assert response.revalidation_run.remediation_run_id == run_id
