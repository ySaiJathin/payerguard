"""Shared fixture builders for audit tests -- not a test module itself
(no `test_` prefix, so pytest doesn't collect it).

The centrepiece is `run_full_incident_lifecycle`, which drives a fixture
incident through the *real* create -> accept -> remediate -> revalidate
path rather than hand-writing audit rows. That matters: a test that
appended its own entries would prove only that the audit table accepts
inserts, not that the pipeline actually calls `append_entry` at each
stage, which is the thing SC-001 and SC-005 are about.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.hitl import accept_service
from app.incidents import service as incidents_service
from app.incidents.schemas import EvidenceBundle, IncidentCreate
from app.remediation import remediation_service
from app.remediation.schemas import AffectedClaimInput
from app.revalidation import revalidation_service
from tests.llm._fixtures import always_returns, make_draft
from tests.revalidation._fixtures import (
    make_anomaly_artifact,
    make_risk_artifact,
    make_revalidation_request,
    patch_recompute_dependencies,
)

REMEDIATED_CLAIM_ID = "CLM-DUP"
UNHANDLED_CLAIM_ID = "CLM-UNHANDLED"


@dataclass
class LifecycleResult:
    """The ids every stage actually produced, so provenance assertions
    resolve against real records rather than guessed values."""

    incident_id: str
    investigation_id: str | None = None
    remediation_run_id: str | None = None
    revalidation_id: str | None = None
    claim_ids: list[str] = field(default_factory=list)


def make_evidence() -> EvidenceBundle:
    return EvidenceBundle(
        quality_check_bands=["CRITICAL", "WARNING"],
        anomaly_score_percentile=0.9,
        affected_claim_pct=0.2,
        risk_score=0.6,
        affected_claims_amounts=[1000.0],
        baseline_amount_percentiles={
            "p25": 100.0,
            "p50": 500.0,
            "p75": 1000.0,
            "p95": 5000.0,
            "p99": 10000.0,
        },
    )


def create_investigated_incident(db: Session) -> LifecycleResult:
    """Phase 10 scoring + Phase 11 investigation + Phase 12 incident,
    through the real `create_incident` with a deterministic fake Mistral
    client (no network)."""
    incident = incidents_service.create_incident(
        db,
        IncidentCreate(window_id="W1", evidence=make_evidence()),
        mistral_client_override=always_returns(make_draft()),
    )
    return LifecycleResult(
        incident_id=incident.incident_id,
        investigation_id=incident.current_investigation_id,
    )


def run_full_incident_lifecycle(db: Session, monkeypatch) -> LifecycleResult:
    """create -> accept -> remediate -> revalidate, all through the real
    services, returning every id produced along the way."""
    result = create_investigated_incident(db)

    accept_service.accept_incident(db, result.incident_id, reviewer_id="r1")

    run = remediation_service.run_remediation(
        db,
        result.incident_id,
        [
            AffectedClaimInput(claim_id=REMEDIATED_CLAIM_ID, is_duplicate=True),
            AffectedClaimInput(
                claim_id=UNHANDLED_CLAIM_ID,
                fields={"PTNT_DSCHRG_STUS_CD": "1", "ADMTG_DGNS_CD": "J45"},
            ),
        ],
    )
    result.remediation_run_id = run.run_id
    result.claim_ids = [REMEDIATED_CLAIM_ID, UNHANDLED_CLAIM_ID]

    patch_recompute_dependencies(
        monkeypatch,
        make_anomaly_artifact(scores=[0.1], feature_columns=["f1", "f2"]),
        make_risk_artifact(probabilities=[0.05], feature_columns=["f1", "f2"]),
    )
    response = revalidation_service.run_revalidation(
        db, result.incident_id, make_revalidation_request(run.run_id)
    )
    result.revalidation_id = response.revalidation_run.revalidation_id

    return result
