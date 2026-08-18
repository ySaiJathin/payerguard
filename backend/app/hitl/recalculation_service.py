"""Recalculation action (spec FR-005; research.md).

Always re-invokes Phase 11's investigation unconditionally -- a reviewer
may want a fresh LLM read even against unchanged evidence. Only
re-invokes Phase 10's scoring functions when the caller supplies a
`new_evidence` bundle that genuinely differs from the incident's stored
`evidence_snapshot`; otherwise reuses the stored `SeverityResult`/
`BusinessImpactResult`/`PriorityResult` as-is and reports
`evidence_changed=False` -- the system never claims evidence changed when
it didn't (spec Edge Cases).
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.hitl import state_machine
from app.hitl.models import IncidentStatusTransition
from app.hitl.schemas import RecalculateResponse
from app.incidents.schemas import EvidenceBundle, Incident
from app.incidents.service import get_incident_orm
from app.llm import payload_builder
from app.llm.errors import MalformedResponseError, MistralAPIError
from app.llm.investigation_service import investigate
from app.risk.scoring import priority as priority_module
from app.risk.scoring.business_impact import compute_business_impact
from app.risk.scoring.schemas import BusinessImpactResult, PriorityResult, SeverityResult
from app.risk.scoring.severity import compute_severity


def _to_dict(model) -> dict:
    return json.loads(model.model_dump_json())


def recalculate_incident(
    db: Session, incident_id: str, new_evidence: EvidenceBundle | None, mistral_client_override=None
) -> RecalculateResponse:
    orm = get_incident_orm(db, incident_id)
    if orm is None:
        raise LookupError(f"Unknown incident_id {incident_id!r}.")

    legal_destinations = state_machine.validate_transition(orm.status, "recalculate")

    stored_evidence = json.loads(json.dumps(orm.evidence_snapshot))
    new_evidence_dict = json.loads(new_evidence.model_dump_json()) if new_evidence is not None else None
    evidence_changed = new_evidence is not None and new_evidence_dict != stored_evidence

    if evidence_changed:
        severity_result = compute_severity(
            quality_check_bands=new_evidence.quality_check_bands,
            anomaly_score_percentile=new_evidence.anomaly_score_percentile,
            affected_claim_pct=new_evidence.affected_claim_pct,
            affected_claims_amounts=new_evidence.affected_claims_amounts,
            baseline_amount_percentiles=new_evidence.baseline_amount_percentiles,
            weights=(new_evidence.weights.severity if new_evidence.weights else None),
        )
        business_impact_result = compute_business_impact(
            affected_claims_amounts=new_evidence.affected_claims_amounts,
            baseline_amount_percentiles=new_evidence.baseline_amount_percentiles,
        )
        priority_result = priority_module.compute_priority(
            severity=severity_result.severity,
            risk=new_evidence.risk_score,
            business_impact=business_impact_result.business_impact,
            affected_claims_score=priority_module.affected_claims_score(new_evidence.affected_claim_pct),
            weights=(new_evidence.weights.priority if new_evidence.weights else None),
        )
    else:
        severity_result = SeverityResult.model_validate(orm.severity_result)
        business_impact_result = BusinessImpactResult.model_validate(orm.business_impact_result)
        priority_result = PriorityResult.model_validate(orm.priority_result)

    llm_payload = payload_builder.build_payload(
        incident_context={"incident_id": incident_id, "window_id": orm.window_id},
        quality_check_results=[
            {"band": band}
            for band in (new_evidence.quality_check_bands if evidence_changed else stored_evidence.get("quality_check_bands", []))
        ],
        anomaly_evidence={
            "anomaly_score_percentile": new_evidence.anomaly_score_percentile
            if evidence_changed
            else stored_evidence.get("anomaly_score_percentile", 0.0)
        },
        risk_evidence={"risk_score": priority_result.risk},
        severity_result=severity_result,
        business_impact_result=business_impact_result,
    )

    new_investigation = None
    try:
        new_investigation = investigate(incident_id, llm_payload, mistral_client_override=mistral_client_override)
        to_status = "ready_for_review"
    except (MistralAPIError, MalformedResponseError):
        to_status = "pending_investigation"

    assert to_status in legal_destinations  # state_machine.py's table is the single source of truth for this set

    now = datetime.now(timezone.utc)
    db.add(
        IncidentStatusTransition(
            transition_id=str(uuid4()),
            incident_id=incident_id,
            from_status=orm.status,
            to_status=to_status,
            action="recalculate",
            reviewer_id=None,
            occurred_at=now,
        )
    )

    orm.status = to_status
    if evidence_changed:
        orm.quality_score = severity_result.quality_failure_severity
        orm.anomaly_score = severity_result.anomaly_magnitude_score
        orm.risk_score = priority_result.risk
        orm.severity_result = _to_dict(severity_result)
        orm.business_impact_result = _to_dict(business_impact_result)
        orm.priority_result = _to_dict(priority_result)
        orm.evidence_snapshot = new_evidence_dict
    if new_investigation is not None:
        orm.current_investigation_id = new_investigation.investigation_id
    orm.updated_at = now

    db.commit()
    db.refresh(orm)

    return RecalculateResponse(
        incident=Incident.model_validate(orm),
        new_investigation=new_investigation,
        evidence_changed=evidence_changed,
    )
