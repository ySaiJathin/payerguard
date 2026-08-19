"""Audit & history read endpoints.

Endpoints per specs/016-audit-history/contracts/api.md.

**Read-only by construction**: there is no endpoint here that accepts a
caller-supplied audit entry. Entries originate exclusively from
`aggregation_service.append_entry`, called by each owning module's own
write path (spec FR-009).

**Path deviation**: contracts/api.md names the baseline endpoint
`GET /baseline`, but Phase 4's `baseline` router already owns that prefix
on the same app. Registering a duplicate would make the served handler
depend on router include order rather than on intent -- FastAPI matches
the first registered route and gives no warning. It is mounted at
`GET /audit/baseline` instead; the content is identical either way, since
it is a pass-through to the same Phase 4 functions.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.audit import baseline_passthrough, history_service
from app.audit.schemas import HistoryQueryResult
from app.baseline.schemas import BaselineSnapshot
from app.core.database import get_db

router = APIRouter(tags=["audit"])


@router.get("/history/{entity_type}/{entity_id}", response_model=HistoryQueryResult)
def get_history(
    entity_type: str,
    entity_id: str,
    page: int = 1,
    page_size: int = Query(default=history_service.DEFAULT_PAGE_SIZE),
    stage: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db),
) -> HistoryQueryResult:
    """Returns 200 in both the found and not-found cases, distinguished by
    the `found` flag -- contracts/api.md deliberately specifies no 404
    here, so a caller can tell "this entity has no history" apart from
    "this endpoint doesn't exist" (spec FR-006, SC-006)."""
    return history_service.query_history(
        db,
        entity_type,
        entity_id,
        page=page,
        page_size=page_size,
        stage=stage,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/audit/baseline", response_model=BaselineSnapshot)
def get_baseline(snapshot_id: str | None = None) -> BaselineSnapshot:
    try:
        return baseline_passthrough.get_baseline(snapshot_id)
    except baseline_passthrough.BaselineNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
