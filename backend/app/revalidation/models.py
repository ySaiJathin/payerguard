"""SQLAlchemy ORM model: `RevalidationRun` (spec data-model.md).

Flattens `BeforeAfterComparison`/`ResolutionDetermination`'s fields onto
the same row rather than separate tables -- data-model.md's Relationships
note states both are strictly 1:1 with their `RevalidationRun`, so a join
would add nothing but complexity. Append-only like `app/remediation/
models.py` -- each revalidation is a new row, never updated/deleted, so
an incident's full revalidation history is always reconstructable
(FR-011, SC-005).
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RevalidationRun(Base):
    __tablename__ = "revalidation_runs"

    revalidation_id: Mapped[str] = mapped_column(String, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String, ForeignKey("incidents.incident_id"), index=True)
    remediation_run_id: Mapped[str] = mapped_column(String, ForeignKey("remediation_runs.run_id"), index=True)

    recomputed_quality_results: Mapped[list] = mapped_column(JSON, nullable=False)
    recomputed_anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    recomputed_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    recomputed_severity_business_impact_priority: Mapped[dict] = mapped_column(JSON, nullable=False)
    anomaly_model_version: Mapped[str] = mapped_column(String, nullable=False)
    risk_model_version: Mapped[str] = mapped_column(String, nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    quality_before: Mapped[float] = mapped_column(Float, nullable=False)
    quality_after: Mapped[float] = mapped_column(Float, nullable=False)
    quality_delta: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_before: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_after: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_delta: Mapped[float] = mapped_column(Float, nullable=False)
    risk_before: Mapped[float] = mapped_column(Float, nullable=False)
    risk_after: Mapped[float] = mapped_column(Float, nullable=False)
    risk_delta: Mapped[float] = mapped_column(Float, nullable=False)
    severity_before: Mapped[float] = mapped_column(Float, nullable=False)
    severity_after: Mapped[float] = mapped_column(Float, nullable=False)
    severity_delta: Mapped[float] = mapped_column(Float, nullable=False)
    priority_before: Mapped[float] = mapped_column(Float, nullable=False)
    priority_after: Mapped[float] = mapped_column(Float, nullable=False)
    priority_delta: Mapped[float] = mapped_column(Float, nullable=False)

    outcome: Mapped[str] = mapped_column(String, nullable=False)
    criteria_evaluated: Mapped[dict] = mapped_column(JSON, nullable=False)
    blocked_by_manual_actions: Mapped[bool] = mapped_column(Boolean, nullable=False)
