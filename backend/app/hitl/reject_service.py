"""Reject action (spec FR-003, FR-004, FR-006; research.md).

**No auto-retrain guarantee (spec FR-006, SC-005)**: this module imports
only `app.hitl`'s own state machine/models and `app.incidents`' read
accessor -- zero import of `app.anomaly.benchmark` or `app.risk.
benchmark`'s model-fitting functions. `HumanFeedback` is written to its
own table and nothing else happens automatically; there is no code path
here that could reach a retraining trigger even by mistake, mirroring
Phase 11's read-only-boundary pattern (import-graph isolation, not just
a convention).
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.hitl import state_machine
from app.hitl.errors import MissingFeedbackError
from app.hitl.models import HumanFeedback, IncidentStatusTransition
from app.incidents.schemas import Incident
from app.incidents.service import get_incident_orm


def reject_incident(
    db: Session, incident_id: str, reviewer_id: str, reason_category: str, feedback_text: str
) -> Incident:
    if not feedback_text or not feedback_text.strip():
        raise MissingFeedbackError("A reject action requires non-empty feedback_text.")

    orm = get_incident_orm(db, incident_id)
    if orm is None:
        raise LookupError(f"Unknown incident_id {incident_id!r}.")

    legal_destinations = state_machine.validate_transition(orm.status, "reject")
    to_status = next(iter(legal_destinations))

    now = datetime.now(timezone.utc)
    db.add(
        IncidentStatusTransition(
            transition_id=str(uuid4()),
            incident_id=incident_id,
            from_status=orm.status,
            to_status=to_status,
            action="reject",
            reviewer_id=reviewer_id,
            occurred_at=now,
        )
    )
    db.add(
        HumanFeedback(
            feedback_id=str(uuid4()),
            incident_id=incident_id,
            investigation_id=orm.current_investigation_id or "",
            reason_category=reason_category,
            feedback_text=feedback_text,
            reviewer_id=reviewer_id,
            submitted_at=now,
        )
    )
    orm.status = to_status
    orm.updated_at = now

    db.commit()
    db.refresh(orm)
    return Incident.model_validate(orm)
