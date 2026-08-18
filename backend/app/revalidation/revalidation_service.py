"""Orchestrates revalidation for a completed `RemediationRun` (spec
FR-007, FR-008, FR-009, FR-011).

Wraps `recompute_service.recompute` (US1) and `comparison_service.
build_comparison` (US2) with the accepted-run gate, the manual-action-
outstanding check, `resolution_criteria.determine_resolution` (US3), and
the incident-status transition via `hitl`'s state machine -- exactly
mirroring `app/remediation/remediation_service.py`'s own layered
orchestrator pattern from 013.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hitl import state_machine
from app.hitl.models import IncidentStatusTransition
from app.incidents.service import get_incident_orm
from app.remediation.remediation_service import list_remediation_runs
from app.revalidation import comparison_service, recompute_service, resolution_criteria
from app.revalidation.errors import IncompleteRemediationRunError
from app.revalidation.models import RevalidationRun as RevalidationRunORM
from app.revalidation.schemas import (
    BeforeAfterComparison,
    ResolutionDetermination,
    ResolutionOutcome,
    RevalidationRun,
    RevalidationRunRequest,
    RevalidationRunResponse,
)


def run_revalidation(db: Session, incident_id: str, request: RevalidationRunRequest) -> RevalidationRunResponse:
    incident_orm = get_incident_orm(db, incident_id)
    if incident_orm is None:
        raise LookupError(f"Unknown incident_id {incident_id!r}.")

    remediation_runs = list_remediation_runs(db, incident_id)
    matched_run = next((run for run in remediation_runs if run.run_id == request.remediation_run_id), None)
    if matched_run is None or matched_run.completed_at is None:
        raise IncompleteRemediationRunError(
            f"remediation_run_id {request.remediation_run_id!r} is unknown or not yet complete for "
            f"incident {incident_id!r} -- revalidation refuses to run against an incomplete remediation "
            "(spec FR-009)."
        )
    has_outstanding_manual_actions = bool(matched_run.manual_actions_required)

    revalidation_id = str(uuid4())
    started_at = datetime.now(timezone.utc)

    recomputed = recompute_service.recompute(incident_orm, request)
    comparison = comparison_service.build_comparison(revalidation_id, incident_orm, recomputed)
    resolution = resolution_criteria.determine_resolution(
        revalidation_id=revalidation_id,
        quality_results=recomputed.quality_results,
        anomaly_score_percentile=recomputed.anomaly_score_percentile,
        risk_score_0_100=recomputed.risk_score,
        has_outstanding_manual_actions=has_outstanding_manual_actions,
    )

    legal_destinations = state_machine.validate_transition(incident_orm.status, "revalidation_result")
    to_status = resolution.outcome.value
    if to_status not in legal_destinations:
        # Structurally unreachable given TRANSITIONS["accepted"]["revalidation_result"]
        # == {"resolved", "reopened"} matches ResolutionOutcome's own two
        # members exactly -- guarded explicitly rather than trusted
        # silently, per this project's error-honesty conventions.
        raise state_machine.InvalidTransitionError(
            f"resolution outcome {to_status!r} is not a legal destination from {incident_orm.status!r} "
            f"(legal: {sorted(legal_destinations)})."
        )

    completed_at = datetime.now(timezone.utc)
    db.add(
        IncidentStatusTransition(
            transition_id=str(uuid4()),
            incident_id=incident_id,
            from_status=incident_orm.status,
            to_status=to_status,
            action="revalidation_result",
            reviewer_id=None,
            occurred_at=completed_at,
        )
    )
    incident_orm.status = to_status
    incident_orm.updated_at = completed_at

    db.add(
        RevalidationRunORM(
            revalidation_id=revalidation_id,
            incident_id=incident_id,
            remediation_run_id=request.remediation_run_id,
            recomputed_quality_results=recomputed.quality_results,
            recomputed_anomaly_score=recomputed.anomaly_score,
            recomputed_risk_score=recomputed.risk_score,
            recomputed_severity_business_impact_priority=recomputed.severity_business_impact_priority,
            anomaly_model_version=recomputed.anomaly_model_version,
            risk_model_version=recomputed.risk_model_version,
            started_at=started_at,
            completed_at=completed_at,
            quality_before=comparison.quality_before,
            quality_after=comparison.quality_after,
            quality_delta=comparison.quality_delta,
            anomaly_before=comparison.anomaly_before,
            anomaly_after=comparison.anomaly_after,
            anomaly_delta=comparison.anomaly_delta,
            risk_before=comparison.risk_before,
            risk_after=comparison.risk_after,
            risk_delta=comparison.risk_delta,
            severity_before=comparison.severity_before,
            severity_after=comparison.severity_after,
            severity_delta=comparison.severity_delta,
            priority_before=comparison.priority_before,
            priority_after=comparison.priority_after,
            priority_delta=comparison.priority_delta,
            outcome=resolution.outcome.value,
            criteria_evaluated=resolution.criteria_evaluated,
            blocked_by_manual_actions=resolution.blocked_by_manual_actions,
        )
    )
    db.commit()

    revalidation_run = RevalidationRun(
        revalidation_id=revalidation_id,
        incident_id=incident_id,
        remediation_run_id=request.remediation_run_id,
        recomputed_quality_results=recomputed.quality_results,
        recomputed_anomaly_score=recomputed.anomaly_score,
        recomputed_risk_score=recomputed.risk_score,
        recomputed_severity_business_impact_priority=recomputed.severity_business_impact_priority,
        anomaly_model_version=recomputed.anomaly_model_version,
        risk_model_version=recomputed.risk_model_version,
        started_at=started_at,
        completed_at=completed_at,
    )

    return RevalidationRunResponse(
        revalidation_run=revalidation_run,
        comparison=comparison,
        resolution=resolution,
        incident_status=to_status,
    )


def list_revalidation_runs(db: Session, incident_id: str) -> list[RevalidationRunResponse]:
    rows = (
        db.execute(
            select(RevalidationRunORM).where(RevalidationRunORM.incident_id == incident_id).order_by(RevalidationRunORM.started_at)
        )
        .scalars()
        .all()
    )

    incident_orm = get_incident_orm(db, incident_id)
    current_status = incident_orm.status if incident_orm is not None else None

    responses: list[RevalidationRunResponse] = []
    for row in rows:
        revalidation_run = RevalidationRun(
            revalidation_id=row.revalidation_id,
            incident_id=row.incident_id,
            remediation_run_id=row.remediation_run_id,
            recomputed_quality_results=row.recomputed_quality_results,
            recomputed_anomaly_score=row.recomputed_anomaly_score,
            recomputed_risk_score=row.recomputed_risk_score,
            recomputed_severity_business_impact_priority=row.recomputed_severity_business_impact_priority,
            anomaly_model_version=row.anomaly_model_version,
            risk_model_version=row.risk_model_version,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )
        comparison = BeforeAfterComparison(
            revalidation_id=row.revalidation_id,
            quality_before=row.quality_before,
            quality_after=row.quality_after,
            quality_delta=row.quality_delta,
            anomaly_before=row.anomaly_before,
            anomaly_after=row.anomaly_after,
            anomaly_delta=row.anomaly_delta,
            risk_before=row.risk_before,
            risk_after=row.risk_after,
            risk_delta=row.risk_delta,
            severity_before=row.severity_before,
            severity_after=row.severity_after,
            severity_delta=row.severity_delta,
            priority_before=row.priority_before,
            priority_after=row.priority_after,
            priority_delta=row.priority_delta,
        )
        resolution = ResolutionDetermination(
            revalidation_id=row.revalidation_id,
            outcome=ResolutionOutcome(row.outcome),
            criteria_evaluated=row.criteria_evaluated,
            blocked_by_manual_actions=row.blocked_by_manual_actions,
        )
        responses.append(
            RevalidationRunResponse(
                revalidation_run=revalidation_run,
                comparison=comparison,
                resolution=resolution,
                incident_status=current_status,
            )
        )
    return responses
