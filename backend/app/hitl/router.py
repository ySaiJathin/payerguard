"""HITL accept/reject/recalculate API endpoints.

Endpoints per specs/012-incident-management-hitl/contracts/api.md.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.hitl import accept_service, recalculation_service, reject_service
from app.hitl.errors import InvalidTransitionError, MissingFeedbackError
from app.hitl.models import HumanFeedback as HumanFeedbackORM
from app.hitl.schemas import (
    AcceptRequest,
    HumanFeedbackRead,
    RecalculateRequest,
    RecalculateResponse,
    RejectRequest,
)
from app.incidents.schemas import Incident

router = APIRouter(prefix="/hitl", tags=["hitl"])


@router.post("/{incident_id}/accept", response_model=Incident)
def accept(incident_id: str, request: AcceptRequest, db: Session = Depends(get_db)) -> Incident:
    try:
        return accept_service.accept_incident(db, incident_id, request.reviewer_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{incident_id}/reject", response_model=Incident)
def reject(incident_id: str, request: RejectRequest, db: Session = Depends(get_db)) -> Incident:
    try:
        return reject_service.reject_incident(
            db, incident_id, request.reviewer_id, request.reason_category.value, request.feedback_text
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingFeedbackError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{incident_id}/recalculate", response_model=RecalculateResponse)
def recalculate(incident_id: str, request: RecalculateRequest, db: Session = Depends(get_db)) -> RecalculateResponse:
    try:
        return recalculation_service.recalculate_incident(db, incident_id, request.new_evidence)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{incident_id}/feedback", response_model=list[HumanFeedbackRead])
def get_feedback(incident_id: str, db: Session = Depends(get_db)) -> list[HumanFeedbackRead]:
    rows = (
        db.execute(
            select(HumanFeedbackORM)
            .where(HumanFeedbackORM.incident_id == incident_id)
            .order_by(HumanFeedbackORM.submitted_at.desc())
        )
        .scalars()
        .all()
    )
    return [HumanFeedbackRead.model_validate(row) for row in rows]
