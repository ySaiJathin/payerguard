"""Accept action (spec FR-002): the sole authorization mechanism Phase
13's remediation engine checks before acting on an incident.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.hitl import state_machine
from app.hitl.models import IncidentStatusTransition
from app.incidents.schemas import Incident
from app.incidents.service import get_incident_orm


def accept_incident(db: Session, incident_id: str, reviewer_id: str) -> Incident:
    orm = get_incident_orm(db, incident_id)
    if orm is None:
        raise LookupError(f"Unknown incident_id {incident_id!r}.")

    legal_destinations = state_machine.validate_transition(orm.status, "accept")
    to_status = next(iter(legal_destinations))  # "accept" has exactly one legal destination

    now = datetime.now(timezone.utc)
    db.add(
        IncidentStatusTransition(
            transition_id=str(uuid4()),
            incident_id=incident_id,
            from_status=orm.status,
            to_status=to_status,
            action="accept",
            reviewer_id=reviewer_id,
            occurred_at=now,
        )
    )
    orm.status = to_status
    orm.updated_at = now

    db.commit()
    db.refresh(orm)
    return Incident.model_validate(orm)
