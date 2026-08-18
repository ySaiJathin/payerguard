"""SQLAlchemy `IncidentStatusTransition` and `HumanFeedback` models (spec
data-model.md). Both are append-only audit tables -- every action creates
a new row, nothing is ever updated or deleted, so an incident's full
accept/reject/recalculate/feedback history is always reconstructable
(spec FR-004, SC-004).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IncidentStatusTransition(Base):
    __tablename__ = "incident_status_transitions"

    transition_id: Mapped[str] = mapped_column(String, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String, ForeignKey("incidents.incident_id"), index=True)
    from_status: Mapped[str] = mapped_column(String, nullable=False)
    to_status: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    reviewer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class HumanFeedback(Base):
    __tablename__ = "human_feedback"

    feedback_id: Mapped[str] = mapped_column(String, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String, ForeignKey("incidents.incident_id"), index=True)
    investigation_id: Mapped[str] = mapped_column(String, nullable=False)
    reason_category: Mapped[str] = mapped_column(String, nullable=False)
    feedback_text: Mapped[str] = mapped_column(String, nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
