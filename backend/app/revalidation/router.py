"""Revalidation API endpoints.

Endpoints per specs/014-revalidation/contracts/api.md.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.revalidation import revalidation_service
from app.revalidation.errors import IncompleteRemediationRunError
from app.revalidation.schemas import RevalidationRunRequest, RevalidationRunResponse

router = APIRouter(prefix="/revalidation", tags=["revalidation"])


@router.post("/{incident_id}/run", response_model=RevalidationRunResponse)
def run(incident_id: str, request: RevalidationRunRequest, db: Session = Depends(get_db)) -> RevalidationRunResponse:
    try:
        return revalidation_service.run_revalidation(db, incident_id, request)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IncompleteRemediationRunError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{incident_id}", response_model=list[RevalidationRunResponse])
def get_history(incident_id: str, db: Session = Depends(get_db)) -> list[RevalidationRunResponse]:
    runs = revalidation_service.list_revalidation_runs(db, incident_id)
    if not runs:
        raise HTTPException(status_code=404, detail=f"No revalidation runs found for incident_id {incident_id!r}.")
    return runs
