"""Incident CRUD API endpoints.

Endpoints per specs/012-incident-management-hitl/contracts/api.md. Status
changes are never accepted here -- `IncidentUpdate` has no `status`
field, and only `hitl`'s router can transition an incident's status.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.incidents import service
from app.incidents.schemas import Incident, IncidentCreate, IncidentUpdate
from app.risk.scoring.errors import MissingRiskScoreError, WeightConfigError

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=Incident, status_code=201)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)) -> Incident:
    try:
        return service.create_incident(db, payload)
    except (MissingRiskScoreError, WeightConfigError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[Incident])
def list_incidents(
    status: str | None = None, min_priority: float | None = None, db: Session = Depends(get_db)
) -> list[Incident]:
    return service.list_incidents(db, status=status, min_priority=min_priority)


@router.get("/{incident_id}", response_model=Incident)
def get_incident(incident_id: str, db: Session = Depends(get_db)) -> Incident:
    incident = service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Unknown incident_id {incident_id!r}.")
    return incident


@router.patch("/{incident_id}", response_model=Incident)
def update_incident(incident_id: str, payload: IncidentUpdate, db: Session = Depends(get_db)) -> Incident:
    incident = service.update_incident(db, incident_id, payload)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Unknown incident_id {incident_id!r}.")
    return incident
