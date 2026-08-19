"""SC-002: every audit entry references a real upstream record, and
duplicates none of its content.

Two separate guarantees, tested separately:

1. **Resolvable** -- `source_record_id` genuinely exists in the owning
   module's own table. A reference pointing at nothing reads as coverage
   while providing none, which is worse than an admitted gap.
2. **Non-duplicating** -- the audit row carries no copy of the upstream
   record's payload. This is a structural property (what columns exist),
   so it is asserted against the model rather than sampled from data:
   FR-001's "never by independently re-deriving or duplicating" cannot be
   satisfied by a table that has somewhere to put a duplicate.
"""

from sqlalchemy import select

from app.audit.models import AuditLog
from app.hitl.models import HumanFeedback, IncidentStatusTransition
from app.incidents.models import Incident as IncidentORM
from app.llm import investigation_log
from app.remediation.models import ManualActionRequired, RemediationAction, RemediationRun
from app.revalidation.models import RevalidationRun
from tests._db_fixtures import make_test_session
from tests.audit._fixtures import run_full_incident_lifecycle

# Which ORM class owns each (source_module, pipeline_stage) pair's records,
# and which column holds the id `source_record_id` points at.
_DB_RESOLVERS = {
    ("incidents", "incident_status"): (IncidentORM, "incident_id"),
    ("risk.scoring", "severity_scoring"): (IncidentORM, "incident_id"),
    ("hitl", "incident_status"): (IncidentStatusTransition, "transition_id"),
    ("hitl", "human_feedback"): (HumanFeedback, "feedback_id"),
    ("revalidation", "revalidation"): (RevalidationRun, "revalidation_id"),
}

# The columns an AuditLog row is allowed to have. Anything else would be
# somewhere for upstream payload to be copied into.
_ALLOWED_COLUMNS = {
    "entry_id",
    "entity_type",
    "entity_id",
    "pipeline_stage",
    "source_module",
    "source_record_id",
    "baseline_snapshot_id_used",
    "sequence_number",
    "occurred_at",
}


def _resolve_remediation(db, entry: AuditLog) -> bool:
    """Remediation contributes three record types (action, manual action,
    and the run itself), so its resolver tries each rather than assuming
    one."""
    for model, column in (
        (RemediationAction, "action_id"),
        (ManualActionRequired, "record_id"),
        (RemediationRun, "run_id"),
    ):
        found = db.execute(
            select(model).where(getattr(model, column) == entry.source_record_id)
        ).scalar_one_or_none()
        if found is not None:
            return True
    return False


def test_every_audit_entry_resolves_to_a_real_upstream_record(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)
    db = make_test_session()
    run_full_incident_lifecycle(db, monkeypatch)

    entries = db.execute(select(AuditLog)).scalars().all()
    assert entries, "Fixture produced no audit entries -- nothing to verify."

    unresolved = []
    for entry in entries:
        key = (entry.source_module, entry.pipeline_stage)

        if entry.source_module == "remediation":
            if not _resolve_remediation(db, entry):
                unresolved.append(f"{key} -> {entry.source_record_id}")
            continue

        if entry.source_module == "llm":
            # File-based store, not a table -- resolved through Phase 11's
            # own reader rather than a SQL lookup.
            investigations, _failures = investigation_log.read_investigation_history(entry.entity_id)
            if entry.source_record_id not in {i.investigation_id for i in investigations}:
                unresolved.append(f"{key} -> {entry.source_record_id}")
            continue

        model, column = _DB_RESOLVERS[key]
        found = db.execute(
            select(model).where(getattr(model, column) == entry.source_record_id)
        ).scalar_one_or_none()
        if found is None:
            unresolved.append(f"{key} -> {entry.source_record_id}")

    assert not unresolved, "Audit entries reference records that do not exist:\n" + "\n".join(unresolved)


def test_audit_table_has_nowhere_to_duplicate_upstream_content():
    """FR-001's non-duplication clause, enforced structurally."""
    actual = set(AuditLog.__table__.columns.keys())

    assert actual == _ALLOWED_COLUMNS, (
        "audit_logs' columns changed. Every column must be a reference or ordering field -- "
        f"unexpected: {sorted(actual - _ALLOWED_COLUMNS)}, missing: {sorted(_ALLOWED_COLUMNS - actual)}"
    )


def test_every_entry_carries_a_non_empty_reference(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)
    db = make_test_session()
    run_full_incident_lifecycle(db, monkeypatch)

    for entry in db.execute(select(AuditLog)).scalars().all():
        assert entry.source_record_id, f"Entry {entry.entry_id} has an empty source_record_id"
        assert entry.source_module, f"Entry {entry.entry_id} has an empty source_module"
