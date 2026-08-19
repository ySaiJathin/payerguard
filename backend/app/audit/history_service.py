"""`/history` query logic (spec FR-002, FR-006, FR-007).

Ordering is always by `sequence_number`, never `occurred_at` -- the whole
reason that column exists is that timestamps tie (spec FR-004, SC-004).
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.audit.schemas import AuditTrailEntry, HistoryQueryResult

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500


def _base_statement(entity_type: str, entity_id: str):
    return select(AuditLog).where(
        AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id
    )


def entity_has_any_history(db: Session, entity_type: str, entity_id: str) -> bool:
    """Whether the entity has *any* audit activity at all, independent of
    the current query's filters. This is what separates FR-006's "no
    history found" from an ordinary empty page."""
    stmt = select(func.count()).select_from(
        _base_statement(entity_type, entity_id).subquery()
    )
    return db.execute(stmt).scalar_one() > 0


def query_history(
    db: Session,
    entity_type: str,
    entity_id: str,
    *,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    stage: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> HistoryQueryResult:
    """Paginated, filterable, deterministically-ordered history.

    `found` reflects whether the *entity* has any recorded activity, not
    whether this particular page/filter matched. A reviewer paging past
    the end of a real history, or filtering to a stage the entity never
    reached, must not get a response that reads as "this entity has no
    history" -- that is exactly the ambiguity FR-006 exists to remove.
    """
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    stmt = _base_statement(entity_type, entity_id)
    if stage is not None:
        stmt = stmt.where(AuditLog.pipeline_stage == stage)
    if start_date is not None:
        stmt = stmt.where(AuditLog.occurred_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(AuditLog.occurred_at <= end_date)

    total_count = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()

    rows = (
        db.execute(
            stmt.order_by(AuditLog.sequence_number).offset((page - 1) * page_size).limit(page_size)
        )
        .scalars()
        .all()
    )

    return HistoryQueryResult(
        entity_type=entity_type,
        entity_id=entity_id,
        entries=[AuditTrailEntry.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total_count=total_count,
        found=entity_has_any_history(db, entity_type, entity_id),
    )
