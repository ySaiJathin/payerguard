"""SC-001: every stage a claim/incident actually passed through appears
as a distinct, correctly-ordered audit entry.

The assertions are two-sided on purpose. A trail that *over*-reports --
claiming a stage the incident never reached -- is just as wrong as one
that misses a stage, and only an exact-set comparison catches both.
"""

from sqlalchemy import select

from app.audit.models import AuditLog
from app.incidents import service as incidents_service
from app.incidents.schemas import IncidentCreate
from app.llm.errors import MistralAPIError
from tests._db_fixtures import make_test_session
from tests.audit._fixtures import (
    REMEDIATED_CLAIM_ID,
    UNHANDLED_CLAIM_ID,
    create_investigated_incident,
    make_evidence,
    run_full_incident_lifecycle,
)


def _entries(db, entity_type: str, entity_id: str) -> list[AuditLog]:
    return list(
        db.execute(
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.sequence_number)
        )
        .scalars()
        .all()
    )


def test_incident_trail_covers_every_stage_it_passed_through(monkeypatch):
    db = make_test_session()
    result = run_full_incident_lifecycle(db, monkeypatch)

    entries = _entries(db, "incident", result.incident_id)
    stages = [e.pipeline_stage for e in entries]

    # create (incident_status + severity_scoring + llm_investigation),
    # accept (incident_status), remediate (remediation),
    # revalidate (revalidation + incident_status).
    assert stages == [
        "incident_status",
        "severity_scoring",
        "llm_investigation",
        "incident_status",
        "remediation",
        "revalidation",
        "incident_status",
    ], f"Unexpected stage sequence: {stages}"

    modules = {e.source_module for e in entries}
    assert modules == {"incidents", "risk.scoring", "llm", "hitl", "remediation", "revalidation"}


def test_entries_are_strictly_ordered_by_sequence_number(monkeypatch):
    db = make_test_session()
    result = run_full_incident_lifecycle(db, monkeypatch)

    sequences = [e.sequence_number for e in _entries(db, "incident", result.incident_id)]

    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences), "sequence_number must never be reused"


def test_claim_scoped_remediation_entries_are_recorded_per_claim(monkeypatch):
    """US1's 'audit trail for a claim' -- and the Edge Case about two
    incidents touching the same claim -- both depend on remediation
    entries being scoped to their own claim_id, not lumped onto the
    incident."""
    db = make_test_session()
    run_full_incident_lifecycle(db, monkeypatch)

    for claim_id in (REMEDIATED_CLAIM_ID, UNHANDLED_CLAIM_ID):
        entries = _entries(db, "claim", claim_id)
        assert len(entries) == 1, f"{claim_id} should have exactly one remediation entry"
        assert entries[0].pipeline_stage == "remediation"
        assert entries[0].source_module == "remediation"


def test_no_llm_entry_when_investigation_never_produced_a_record(monkeypatch):
    """A failed investigation produces no LLMInvestigation to reference,
    so emitting an entry for it would point at a record that does not
    exist. The absence is the correct behaviour, not a gap."""
    db = make_test_session()

    def _always_fails(*args, **kwargs):
        raise MistralAPIError("simulated outage")

    monkeypatch.setattr(incidents_service, "investigate", _always_fails)
    incident = incidents_service.create_incident(
        db, IncidentCreate(window_id="W1", evidence=make_evidence())
    )

    entries = _entries(db, "incident", incident.incident_id)
    stages = [e.pipeline_stage for e in entries]

    assert "llm_investigation" not in stages
    assert stages == ["incident_status", "severity_scoring"]


def test_incident_with_no_activity_has_no_entries():
    """Guards against the trail inventing entries for an entity that was
    never processed."""
    db = make_test_session()
    assert _entries(db, "incident", "never-existed") == []


def test_second_incident_does_not_inherit_the_first_incidents_trail(monkeypatch):
    db = make_test_session()
    first = run_full_incident_lifecycle(db, monkeypatch)
    second = create_investigated_incident(db)

    first_entries = _entries(db, "incident", first.incident_id)
    second_entries = _entries(db, "incident", second.incident_id)

    assert len(second_entries) == 3  # create only: status + scoring + llm
    assert {e.entry_id for e in first_entries}.isdisjoint({e.entry_id for e in second_entries})
