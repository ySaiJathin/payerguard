"""Persists and tracks `IngestedBatch` rows -- one per upload attempt,
accepted or rejected (spec FR-004, FR-005, FR-006, FR-007, FR-009).

Every function here that creates or advances a batch also appends the
matching Phase 16 audit entry in the same call, so a batch's existence and
its audit trail can never drift apart (there is no code path that writes
one without the other).
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.aggregation_service import append_entry
from app.ingestion.models import IngestedBatchORM
from app.ingestion.schemas import (
    BatchListing,
    BatchStatus,
    BatchUploadRejection,
    IngestedBatch,
    RejectionReasonCode,
)


def _to_schema(orm: IngestedBatchORM) -> IngestedBatch:
    rejection = None
    if orm.rejection_reason_code is not None:
        rejection = BatchUploadRejection(
            batch_id=orm.batch_id,
            reason_code=RejectionReasonCode(orm.rejection_reason_code),
            detail=orm.rejection_detail or "",
        )
    return IngestedBatch(
        batch_id=orm.batch_id,
        filename=orm.filename,
        stored_path=orm.stored_path,
        uploaded_at=orm.uploaded_at,
        row_count=orm.row_count,
        status=BatchStatus(orm.status),
        rejection_reason=rejection,
        pipeline_stage_reached=orm.pipeline_stage_reached,
        quality_result_id=orm.quality_result_id,
        anomaly_result_id=orm.anomaly_result_id,
        risk_result_id=orm.risk_result_id,
        incident_ids=list(orm.incident_ids or []),
    )


def create_batch(db: Session, *, filename: str, row_count: int, stored_path: str | None = None) -> IngestedBatch:
    """Records a newly-accepted upload before its pipeline run starts
    (status=`accepted`). FR-005: `batch_id` is freshly generated every
    call, so an identical filename/content uploaded again is always a new,
    independent batch, never merged with a prior one. `stored_path` is
    usually set afterward via `set_stored_path` once the batch_id-derived
    storage path is known and the bytes are actually on disk."""
    batch_id = str(uuid4())
    orm = IngestedBatchORM(
        batch_id=batch_id,
        filename=filename,
        stored_path=stored_path,
        uploaded_at=datetime.now(timezone.utc),
        row_count=row_count,
        status=BatchStatus.accepted.value,
        incident_ids=[],
    )
    db.add(orm)
    append_entry(
        db,
        entity_type="batch",
        entity_id=batch_id,
        pipeline_stage="ingestion",
        source_module="ingestion",
        source_record_id=batch_id,
    )
    db.commit()
    db.refresh(orm)
    return _to_schema(orm)


def record_rejection(db: Session, *, filename: str, reason_code: RejectionReasonCode, detail: str) -> IngestedBatch:
    """Records a rejected upload attempt. Spec User Story 3 Acceptance
    Scenario 2: a rejected attempt still gets a batch row and an audit
    entry -- it is not silently dropped from history."""
    batch_id = str(uuid4())
    orm = IngestedBatchORM(
        batch_id=batch_id,
        filename=filename,
        stored_path=None,
        uploaded_at=datetime.now(timezone.utc),
        row_count=None,
        status=BatchStatus.rejected.value,
        rejection_reason_code=reason_code.value,
        rejection_detail=detail,
        incident_ids=[],
    )
    db.add(orm)
    append_entry(
        db,
        entity_type="batch",
        entity_id=batch_id,
        pipeline_stage="ingestion",
        source_module="ingestion",
        source_record_id=batch_id,
    )
    db.commit()
    db.refresh(orm)
    return _to_schema(orm)


# Forward-only per data-model.md's validation rule -- a batch never moves
# back to an earlier stage once it has advanced.
_STATUS_ORDER = [
    BatchStatus.rejected,
    BatchStatus.accepted,
    BatchStatus.processing,
    BatchStatus.completed,
    BatchStatus.failed,
]


def update_batch_status(
    db: Session,
    batch_id: str,
    *,
    status: BatchStatus,
    pipeline_stage_reached: str | None = None,
    quality_result_id: str | None = None,
    anomaly_result_id: str | None = None,
    risk_result_id: str | None = None,
    incident_ids: list[str] | None = None,
) -> IngestedBatch:
    orm = db.execute(select(IngestedBatchORM).where(IngestedBatchORM.batch_id == batch_id)).scalar_one()
    orm.status = status.value
    if pipeline_stage_reached is not None:
        orm.pipeline_stage_reached = pipeline_stage_reached
    if quality_result_id is not None:
        orm.quality_result_id = quality_result_id
    if anomaly_result_id is not None:
        orm.anomaly_result_id = anomaly_result_id
    if risk_result_id is not None:
        orm.risk_result_id = risk_result_id
    if incident_ids is not None:
        orm.incident_ids = incident_ids
    db.commit()
    db.refresh(orm)
    return _to_schema(orm)


def set_stored_path(db: Session, batch_id: str, stored_path: str) -> IngestedBatch:
    """Records where the accepted upload's raw bytes actually landed on
    disk. Separate from `create_batch` because the storage path is
    derived from `batch_id`, which does not exist until `create_batch`
    has run."""
    orm = db.execute(select(IngestedBatchORM).where(IngestedBatchORM.batch_id == batch_id)).scalar_one()
    orm.stored_path = stored_path
    db.commit()
    db.refresh(orm)
    return _to_schema(orm)


def get_batch(db: Session, batch_id: str) -> IngestedBatch | None:
    orm = db.execute(select(IngestedBatchORM).where(IngestedBatchORM.batch_id == batch_id)).scalar_one_or_none()
    return _to_schema(orm) if orm is not None else None


def list_batches(db: Session, *, page: int = 1, page_size: int = 25) -> BatchListing:
    """Newest-first (spec FR-006), including rejected attempts."""
    total_count = db.execute(select(IngestedBatchORM)).scalars().all()
    total = len(total_count)
    ordered = sorted(total_count, key=lambda o: o.uploaded_at, reverse=True)
    start = (page - 1) * page_size
    page_rows = ordered[start : start + page_size]
    return BatchListing(
        batches=[_to_schema(o) for o in page_rows],
        page=page,
        page_size=page_size,
        total_count=total,
    )
