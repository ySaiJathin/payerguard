"""SQLAlchemy ORM model: `AuditLog` (spec data-model.md's `AuditTrailEntry`).

Table name `audit_logs` matches MVP_CONTEXT.md Section 3's core-tables
list. Append-only like `app/remediation/models.py` and
`app/revalidation/models.py` -- a row is never updated or deleted, since
an audit trail that can be rewritten is not an audit trail (spec FR-009).

Every row is a *reference*: `source_module` + `source_record_id` point at
the owning module's own persisted record, and no column carries a copy of
that record's payload (spec FR-001, SC-002).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    entry_id: Mapped[str] = mapped_column(String, primary_key=True)

    entity_type: Mapped[str] = mapped_column(String, index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    pipeline_stage: Mapped[str] = mapped_column(String, index=True, nullable=False)

    source_module: Mapped[str] = mapped_column(String, nullable=False)
    source_record_id: Mapped[str] = mapped_column(String, nullable=False)

    baseline_snapshot_id_used: Mapped[str | None] = mapped_column(String, nullable=True)

    # Monotonic and unique: the tiebreaker that makes ordering deterministic
    # when two events share a timestamp (spec FR-004, SC-004). Ordering by
    # `occurred_at` alone is exactly the ambiguity this column exists to fix.
    sequence_number: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    __table_args__ = (
        # The exact shape every /history query filters and orders by.
        Index("ix_audit_logs_entity_sequence", "entity_type", "entity_id", "sequence_number"),
    )
