"""Spec SC-002 / US3 Acceptance Scenario 1: remediation refuses to
execute against any incident whose status isn't "accepted", and succeeds
against one that is.
"""

import pytest
from sqlalchemy import select

from app.remediation.errors import NotAcceptedIncidentError
from app.remediation.models import RemediationAction as RemediationActionORM
from app.remediation.remediation_service import run_remediation
from tests._db_fixtures import make_test_session
from tests.remediation._fixtures import make_claim, make_incident


@pytest.mark.parametrize("status", ["pending_investigation", "ready_for_review", "rejected"])
def test_non_accepted_incident_is_refused(status):
    db = make_test_session()
    incident = make_incident(db, status=status)
    claims = [make_claim(claim_id="CLM1", is_duplicate=True)]

    with pytest.raises(NotAcceptedIncidentError):
        run_remediation(db, incident.incident_id, claims)

    rows = db.execute(select(RemediationActionORM)).scalars().all()
    assert rows == []


def test_accepted_incident_succeeds():
    db = make_test_session()
    incident = make_incident(db, status="accepted")
    claims = [make_claim(claim_id="CLM1", is_duplicate=True)]

    run = run_remediation(db, incident.incident_id, claims)

    assert run.incident_id == incident.incident_id
    assert len(run.actions) == 1
    assert run.actions[0].claim_id == "CLM1"


def test_unknown_incident_raises_lookup_error():
    db = make_test_session()

    with pytest.raises(LookupError):
        run_remediation(db, "does-not-exist", [make_claim()])
