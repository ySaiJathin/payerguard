"""Remediation API endpoints.

Endpoints per specs/013-remediation-engine/contracts/api.md.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.remediation import remediation_service
from app.remediation.errors import NotAcceptedIncidentError
from app.remediation.schemas import RemediationRun, RemediationRunRequest

router = APIRouter(prefix="/remediation", tags=["remediation"])


@router.post("/{incident_id}/run", response_model=RemediationRun)
def run(incident_id: str, request: RemediationRunRequest, db: Session = Depends(get_db)) -> RemediationRun:
    try:
        return remediation_service.run_remediation(db, incident_id, request.affected_claims)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotAcceptedIncidentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{incident_id}", response_model=list[RemediationRun])
def get_history(incident_id: str, db: Session = Depends(get_db)) -> list[RemediationRun]:
    runs = remediation_service.list_remediation_runs(db, incident_id)
    if not runs:
        raise HTTPException(status_code=404, detail=f"No remediation runs found for incident_id {incident_id!r}.")
    return runs
