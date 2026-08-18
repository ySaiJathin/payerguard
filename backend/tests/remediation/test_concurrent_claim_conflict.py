"""Spec FR-010 / Edge Cases bullet 5: a claim affected by more than one
incident must not have its remediation silently overwritten/interfered
with -- the second incident's run flags an explicit conflict instead of
double-applying.
"""

from app.remediation.schemas import ReasonCode
from app.remediation.remediation_service import run_remediation
from tests._db_fixtures import make_test_session
from tests.remediation._fixtures import make_claim, make_incident


def test_shared_claim_across_two_incidents_is_flagged_a_conflict():
    db = make_test_session()
    incident_a = make_incident(db, status="accepted")
    incident_b = make_incident(db, status="accepted")

    shared_claim = make_claim(claim_id="CLM-SHARED", is_duplicate=True)

    run_a = run_remediation(db, incident_a.incident_id, [shared_claim])
    assert len(run_a.actions) == 1
    assert run_a.actions[0].claim_id == "CLM-SHARED"

    run_b = run_remediation(
        db,
        incident_b.incident_id,
        [shared_claim, make_claim(claim_id="CLM-ONLY-B", fields={"ADMTG_DGNS_CD": None})],
    )

    assert run_b.actions == [] or all(a.claim_id != "CLM-SHARED" for a in run_b.actions)
    assert len(run_b.manual_actions_required) == 1
    conflict = run_b.manual_actions_required[0]
    assert conflict.claim_id == "CLM-SHARED"
    assert conflict.reason_code == ReasonCode.concurrent_incident_conflict
    assert incident_a.incident_id in conflict.description

    # The claim unique to incident B, with no conflict, remediates normally.
    assert any(a.claim_id == "CLM-ONLY-B" for a in run_b.actions)
