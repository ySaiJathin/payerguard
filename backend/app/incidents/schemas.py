"""Pydantic models for incident management.

See specs/012-incident-management-hitl/data-model.md for field
definitions and validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.baseline.schemas import Percentiles
from app.risk.scoring.schemas import BusinessImpactResult, PriorityResult, SeverityResult, ScoreWeightsInput


class IncidentStatus(str, Enum):
    pending_investigation = "pending_investigation"
    ready_for_review = "ready_for_review"
    accepted = "accepted"
    rejected = "rejected"
    resolved = "resolved"  # reserved, Phase 14
    reopened = "reopened"  # reserved, Phase 14


class EvidenceBundle(BaseModel):
    """The already-resolved evidence shape Phase 10's own `/risk/score`
    accepts (spec's Evidence-input design note) -- neither `incidents`
    nor `hitl` can autonomously fetch a window's Phase 3/4/7/9 evidence
    from disk, so the caller supplies it explicitly, same as Phase 10/11.
    """

    quality_check_bands: list[str] = []
    anomaly_score_percentile: float = 0.0
    affected_claim_pct: float = 0.0
    affected_claims_amounts: list[float] = []
    risk_score: float | None = None
    baseline_amount_percentiles: Percentiles | None = None
    weights: ScoreWeightsInput | None = None


class IncidentCreate(BaseModel):
    window_id: str
    evidence: EvidenceBundle = EvidenceBundle()


class IncidentUpdate(BaseModel):
    """Every field except `status` -- status changes only ever happen
    through `hitl` endpoints (contracts/api.md's Notes; spec FR-001)."""

    quality_score: float | None = None
    anomaly_score: float | None = None
    risk_score: float | None = None
    severity_result: SeverityResult | None = None
    business_impact_result: BusinessImpactResult | None = None
    priority_result: PriorityResult | None = None


class Incident(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    window_id: str
    quality_score: float
    anomaly_score: float
    risk_score: float
    severity_result: dict
    business_impact_result: dict
    priority_result: dict
    evidence_snapshot: dict
    status: IncidentStatus
    current_investigation_id: str | None
    created_at: datetime
    updated_at: datetime
