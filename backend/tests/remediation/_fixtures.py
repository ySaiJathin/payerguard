"""Shared fixture builders for remediation tests -- not a test module
itself (no `test_` prefix, so pytest doesn't collect it)."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.incidents.models import Incident as IncidentORM
from app.remediation.schemas import AffectedClaimInput


def make_claim(claim_id: str = "CLM1", is_duplicate: bool = False, fields: dict | None = None) -> AffectedClaimInput:
    return AffectedClaimInput(claim_id=claim_id, is_duplicate=is_duplicate, fields=fields or {})


def make_incident(db: Session, status: str = "accepted", incident_id: str | None = None) -> IncidentORM:
    """Constructs and persists a minimal Incident row directly at the ORM
    layer, bypassing Phase 10/11's scoring/investigation pipeline --
    remediation tests only care about `status`, not how an incident got
    there (that's 012's own test suite's concern)."""
    now = datetime.now(timezone.utc)
    orm = IncidentORM(
        incident_id=incident_id or str(uuid4()),
        window_id="W1",
        quality_score=50.0,
        anomaly_score=50.0,
        risk_score=0.5,
        severity_result={},
        business_impact_result={},
        priority_result={},
        evidence_snapshot={},
        status=status,
        current_investigation_id=None,
        created_at=now,
        updated_at=now,
    )
    db.add(orm)
    db.commit()
    db.refresh(orm)
    return orm
