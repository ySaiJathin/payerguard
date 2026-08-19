"""`append_entry` -- the one write path into the audit trail (spec FR-001,
FR-004, FR-005, FR-009).

Deliberately dependency-light: it imports nothing from any other
pipeline-stage module and takes only plain values plus a `Session`
(research.md's no-circular-dependency decision). `audit` is the last
module built but must be callable from every earlier module's write path,
so it cannot know anything about their domains.

Two design points that matter and are easy to get wrong:

- **It does not commit.** The row is added to the caller's existing
  transaction, so an audit entry can never become durable for a fact whose
  own write was rolled back. A trail that records things that didn't
  happen is worse than no trail.
- **`sequence_number` is assigned from the table, not the clock.** Two
  events in the same millisecond still get distinct, strictly increasing
  numbers, which is the entire reason the column exists (FR-004, SC-004).
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.audit.schemas import AuditTrailEntry


def _next_sequence_number(db: Session) -> int:
    # Computed inside the caller's transaction. flush() first so entries
    # appended earlier in this same transaction (a remediation run writing
    # one row per claim, say) are visible and cannot collide on the
    # unique constraint.
    db.flush()
    current_max = db.execute(select(func.coalesce(func.max(AuditLog.sequence_number), 0))).scalar_one()
    return int(current_max) + 1


def append_entry(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    pipeline_stage: str,
    source_module: str,
    source_record_id: str,
    baseline_snapshot_id_used: str | None = None,
    occurred_at: datetime | None = None,
) -> AuditTrailEntry:
    """Appends one referencing audit entry. Called by the owning module at
    the moment it persists its own record.

    `source_record_id` must be the id of a record that module genuinely
    persisted -- this function stores the reference and nothing of the
    record's content, so provenance stays resolvable and no fact is
    duplicated (FR-001, SC-002).
    """
    return append_entries(
        db,
        [
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "pipeline_stage": pipeline_stage,
                "source_module": source_module,
                "source_record_id": source_record_id,
                "baseline_snapshot_id_used": baseline_snapshot_id_used,
                "occurred_at": occurred_at,
            }
        ],
    )[0]


def append_entries(db: Session, entries: list[dict]) -> list[AuditTrailEntry]:
    """Bulk form: appends many entries with a single sequence-number
    lookup.

    Batch stages append per-record, and a cleaning run over the real
    58,066-row file produces far too many records for a per-entry
    `MAX(sequence_number)` query to be viable -- that would be one round
    trip per record. Computing the base once and handing out
    `base + 1 … base + n` keeps the numbers strictly increasing and
    contiguous while costing a single query, and preserves the caller's
    input order as the audit order.
    """
    if not entries:
        return []

    base = _next_sequence_number(db) - 1
    now = datetime.now(timezone.utc)

    orms = [
        AuditLog(
            entry_id=str(uuid4()),
            entity_type=entry["entity_type"],
            entity_id=entry["entity_id"],
            pipeline_stage=entry["pipeline_stage"],
            source_module=entry["source_module"],
            source_record_id=entry["source_record_id"],
            baseline_snapshot_id_used=entry.get("baseline_snapshot_id_used"),
            sequence_number=base + offset,
            occurred_at=entry.get("occurred_at") or now,
        )
        for offset, entry in enumerate(entries, start=1)
    ]
    db.add_all(orms)
    # No commit: the caller owns the transaction boundary (see docstring).
    db.flush()
    return [AuditTrailEntry.model_validate(orm) for orm in orms]
