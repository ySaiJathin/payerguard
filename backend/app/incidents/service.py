"""Incident CRUD (spec FR-001) -- creation composes Phase 10's scoring
functions and Phase 11's investigation service; reads/updates are plain
DB operations. `update_incident` never touches `status` -- structurally
impossible, since `IncidentUpdate` has no `status` field (contracts/
api.md's Notes: only `hitl` endpoints change status).
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hitl.models import IncidentStatusTransition
from app.incidents.models import Incident as IncidentORM
from app.incidents.schemas import EvidenceBundle, Incident, IncidentCreate, IncidentUpdate
from app.llm import payload_builder
from app.llm.errors import MalformedResponseError, MistralAPIError
from app.llm.investigation_service import investigate
from app.risk.scoring import priority as priority_module
from app.risk.scoring.business_impact import compute_business_impact
from app.risk.scoring.severity import compute_severity


def _to_dict(model) -> dict:
    return json.loads(model.model_dump_json())


def create_incident(db: Session, payload: IncidentCreate, mistral_client_override=None) -> Incident:
    evidence: EvidenceBundle = payload.evidence

    severity_result = compute_severity(
        quality_check_bands=evidence.quality_check_bands,
        anomaly_score_percentile=evidence.anomaly_score_percentile,
        affected_claim_pct=evidence.affected_claim_pct,
        affected_claims_amounts=evidence.affected_claims_amounts,
        baseline_amount_percentiles=evidence.baseline_amount_percentiles,
        weights=(evidence.weights.severity if evidence.weights else None),
    )
    business_impact_result = compute_business_impact(
        affected_claims_amounts=evidence.affected_claims_amounts,
        baseline_amount_percentiles=evidence.baseline_amount_percentiles,
    )
    priority_result = priority_module.compute_priority(
        severity=severity_result.severity,
        risk=evidence.risk_score,  # raises MissingRiskScoreError if None -- propagated, no fabricated default
        business_impact=business_impact_result.business_impact,
        affected_claims_score=priority_module.affected_claims_score(evidence.affected_claim_pct),
        weights=(evidence.weights.priority if evidence.weights else None),
    )

    incident_id = str(uuid4())
    now = datetime.now(timezone.utc)

    llm_payload = payload_builder.build_payload(
        incident_context={"incident_id": incident_id, "window_id": payload.window_id},
        quality_check_results=[{"band": band} for band in evidence.quality_check_bands],
        anomaly_evidence={"anomaly_score_percentile": evidence.anomaly_score_percentile},
        risk_evidence={"risk_score": evidence.risk_score},
        severity_result=severity_result,
        business_impact_result=business_impact_result,
    )

    investigation_id = None
    status = "pending_investigation"
    try:
        investigation = investigate(incident_id, llm_payload, mistral_client_override=mistral_client_override)
        investigation_id = investigation.investigation_id
        status = "ready_for_review"
    except (MistralAPIError, MalformedResponseError):
        # Investigation failure doesn't block incident creation -- real
        # Phase 10 scores exist regardless; the status reflects the
        # failure honestly instead (spec Edge Cases).
        pass

    incident_orm = IncidentORM(
        incident_id=incident_id,
        window_id=payload.window_id,
        quality_score=severity_result.quality_failure_severity,
        anomaly_score=severity_result.anomaly_magnitude_score,
        risk_score=priority_result.risk,
        severity_result=_to_dict(severity_result),
        business_impact_result=_to_dict(business_impact_result),
        priority_result=_to_dict(priority_result),
        evidence_snapshot=json.loads(evidence.model_dump_json()),
        status=status,
        current_investigation_id=investigation_id,
        created_at=now,
        updated_at=now,
    )
    db.add(incident_orm)

    if status == "ready_for_review":
        db.add(
            IncidentStatusTransition(
                transition_id=str(uuid4()),
                incident_id=incident_id,
                from_status="pending_investigation",
                to_status="ready_for_review",
                action="system",
                reviewer_id=None,
                occurred_at=now,
            )
        )

    db.commit()
    db.refresh(incident_orm)
    return Incident.model_validate(incident_orm)


def get_incident(db: Session, incident_id: str) -> Incident | None:
    orm = db.get(IncidentORM, incident_id)
    return Incident.model_validate(orm) if orm else None


def get_incident_orm(db: Session, incident_id: str) -> IncidentORM | None:
    """Returns the SQLAlchemy row itself -- used by `hitl` services that
    need to mutate the row, not just read a pydantic snapshot of it."""
    return db.get(IncidentORM, incident_id)


def list_incidents(db: Session, status: str | None = None, min_priority: float | None = None) -> list[Incident]:
    stmt = select(IncidentORM)
    if status is not None:
        stmt = stmt.where(IncidentORM.status == status)
    rows = db.execute(stmt).scalars().all()

    results = [Incident.model_validate(row) for row in rows]
    if min_priority is not None:
        results = [r for r in results if r.priority_result.get("priority", 0.0) >= min_priority]
    return results


def update_incident(db: Session, incident_id: str, payload: IncidentUpdate) -> Incident | None:
    orm = db.get(IncidentORM, incident_id)
    if orm is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field in ("severity_result", "business_impact_result", "priority_result"):
        if field in updates and updates[field] is not None:
            updates[field] = json.loads(json.dumps(updates[field], default=str))

    for field, value in updates.items():
        setattr(orm, field, value)
    orm.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(orm)
    return Incident.model_validate(orm)
