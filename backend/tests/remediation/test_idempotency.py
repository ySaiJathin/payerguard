"""Spec SC-005 / Edge Cases bullet 3: re-running remediation on an
incident with already-applied handlers must not double-apply them, and
must still complete any claims left unresolved by an earlier partial
run.
"""

from sqlalchemy import select

from app.remediation.models import RemediationAction as RemediationActionORM
from app.remediation.remediation_service import list_remediation_runs, run_remediation
from tests._db_fixtures import make_test_session
from tests.remediation._fixtures import make_claim, make_incident


def test_rerunning_the_same_claims_produces_no_duplicate_actions():
    db = make_test_session()
    incident = make_incident(db, status="accepted")
    claims = [
        make_claim(claim_id="CLM-DUP", is_duplicate=True),
        make_claim(claim_id="CLM-IMPUTE", fields={"ADMTG_DGNS_CD": None}),
    ]

    first_run = run_remediation(db, incident.incident_id, claims)
    second_run = run_remediation(db, incident.incident_id, claims)

    assert len(first_run.actions) == 2
    assert len(second_run.actions) == 2
    # Both runs report the *same* action ids -- the second run resumed
    # (reused) rather than re-applied.
    assert {a.action_id for a in first_run.actions} == {a.action_id for a in second_run.actions}

    rows = db.execute(
        select(RemediationActionORM).where(RemediationActionORM.incident_id == incident.incident_id)
    ).scalars().all()
    assert len(rows) == 2  # not 4 -- no duplicates persisted across the two runs

    # data-model.md's per-run completeness rule (FR-009/SC-003) applies to
    # the *persisted, later-retrievable* history too, not just the
    # in-memory response returned at the moment of the call -- the
    # resumed second run's own history entry must still show both claims'
    # outcomes, even though it created zero new RemediationAction rows.
    history = list_remediation_runs(db, incident.incident_id)
    assert len(history) == 2
    assert {a.claim_id for a in history[1].actions} == {"CLM-DUP", "CLM-IMPUTE"}


def test_retry_after_partial_completion_finishes_the_remaining_claims():
    """Simulates a retry after a partial failure: the first call only
    covers CLM-DUP; the second call covers both CLM-DUP and a
    previously-unseen CLM-IMPUTE. The already-completed claim isn't
    re-applied, and the new one is completed by the resuming run."""
    db = make_test_session()
    incident = make_incident(db, status="accepted")

    first_run = run_remediation(db, incident.incident_id, [make_claim(claim_id="CLM-DUP", is_duplicate=True)])
    assert len(first_run.actions) == 1

    second_run = run_remediation(
        db,
        incident.incident_id,
        [
            make_claim(claim_id="CLM-DUP", is_duplicate=True),
            make_claim(claim_id="CLM-IMPUTE", fields={"ADMTG_DGNS_CD": None}),
        ],
    )

    assert len(second_run.actions) == 2
    second_run_action_ids = {a.action_id for a in second_run.actions}
    assert first_run.actions[0].action_id in second_run_action_ids

    rows = db.execute(
        select(RemediationActionORM).where(RemediationActionORM.incident_id == incident.incident_id)
    ).scalars().all()
    assert len(rows) == 2
