"""SQLAlchemy ORM model: `IngestedBatchORM` (spec data-model.md).

Unlike `app/audit/models.py`'s append-only `AuditLog`, one batch's own row
legitimately advances through its own status lifecycle (`accepted` ->
`processing` -> `completed`/`failed`, or `rejected` outright) -- so this
table is updated in place, not appended to. data-model.md's validation
rule (status only ever advances forward) is enforced by
`app.ingestion.batch_service`, not by the schema itself.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestedBatchORM(Base):
    __tablename__ = "ingested_batches"

    batch_id: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_path: Mapped[str | None] = mapped_column(String, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)

    rejection_reason_code: Mapped[str | None] = mapped_column(String, nullable=True)
    rejection_detail: Mapped[str | None] = mapped_column(String, nullable=True)

    pipeline_stage_reached: Mapped[str | None] = mapped_column(String, nullable=True)
    quality_result_id: Mapped[str | None] = mapped_column(String, nullable=True)
    anomaly_result_id: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_result_id: Mapped[str | None] = mapped_column(String, nullable=True)
    incident_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
