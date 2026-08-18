"""SQLAlchemy ORM models: `RemediationRun`, `RemediationAction`,
`ManualActionRequired` (spec data-model.md). Append-only, like
`app/hitl/models.py` -- a run's actions/manual-action records are never
updated or deleted, so an incident's full remediation history (every run
ever triggered) is always reconstructable via `remediation_service.
list_remediation_runs`.

`RemediationAction` carries a `UniqueConstraint` on
`(incident_id, claim_id, rule_id)` -- the idempotency key research.md
settled on: re-running remediation on an incident with some already-
completed handlers resumes rather than restarts, and the DB itself
refuses a double-apply as a backstop to the service-level existence
check (FR-008, SC-005).

`RemediationRunReusedAction` links a run to a `RemediationAction` it
*resumed* rather than newly created -- when run N re-processes a claim
already remediated by an earlier run, the unique constraint above means
no new `RemediationAction` row can exist with run N's `run_id`, but
data-model.md's per-run completeness rule (every affected claim appears
in exactly one of actions/manual_actions_required "for a completed run",
FR-009/SC-003) still requires run N's own persisted record to show that
claim's outcome. This table is that link, consulted by
`remediation_service.list_remediation_runs` alongside the direct
`run_id` filter.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RemediationRun(Base):
    __tablename__ = "remediation_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String, ForeignKey("incidents.incident_id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RemediationAction(Base):
    __tablename__ = "remediation_actions"
    __table_args__ = (UniqueConstraint("incident_id", "claim_id", "rule_id", name="uq_remediation_action_key"),)

    action_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("remediation_runs.run_id"), index=True)
    incident_id: Mapped[str] = mapped_column(String, index=True)
    claim_id: Mapped[str] = mapped_column(String, index=True)
    rule_id: Mapped[str] = mapped_column(String, nullable=False)
    before_value: Mapped[str | None] = mapped_column(String, nullable=True)
    after_value: Mapped[str | None] = mapped_column(String, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ManualActionRequired(Base):
    __tablename__ = "manual_actions_required"

    record_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("remediation_runs.run_id"), index=True)
    incident_id: Mapped[str] = mapped_column(String, index=True)
    claim_id: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    reason_code: Mapped[str] = mapped_column(String, nullable=False)
    flagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RemediationRunReusedAction(Base):
    __tablename__ = "remediation_run_reused_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("remediation_runs.run_id"), index=True)
    action_id: Mapped[str] = mapped_column(String, ForeignKey("remediation_actions.action_id"), index=True)
