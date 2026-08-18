"""SQLAlchemy `Incident` model (spec data-model.md).

`status` is a plain `String` column, not a DB-level enum -- FR-008
requires the status field be extensible to Phase 13/14's future values
(`resolved`, `reopened`) without a breaking redesign; a string column
means adding a new status is a change to `hitl/state_machine.py`'s
Python-level transition table, never a schema migration. `severity_
result`/`business_impact_result`/`priority_result` are stored as JSON --
exactly Phase 10's own output, never recomputed independently (spec
FR-010). `evidence_snapshot` stores the raw evidence bundle the incident
was last (re)computed from, so `hitl/recalculation_service.py` can
honestly detect whether evidence actually changed (research.md).
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Incident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String, primary_key=True)
    window_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)

    severity_result: Mapped[dict] = mapped_column(JSON, nullable=False)
    business_impact_result: Mapped[dict] = mapped_column(JSON, nullable=False)
    priority_result: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, default="pending_investigation")
    current_investigation_id: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
