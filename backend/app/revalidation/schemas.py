"""Pydantic models for the revalidation engine.

See specs/014-revalidation/data-model.md for field definitions and
validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class CurrentClaimState(BaseModel):
    """Caller-supplied current (post-remediation) state for one affected
    claim -- mirrors 013-remediation-engine's `AffectedClaimInput`. No
    live `claims` table exists yet, so the caller supplies this
    explicitly rather than revalidation autonomously fetching it."""

    claim_id: str
    raw_fields: dict[str, str | float | None] = {}


class RevalidationRunRequest(BaseModel):
    """The `POST /revalidation/{incident_id}/run` request body.

    `anomaly_features`/`risk_features` are the feature vectors Phase 7's
    and Phase 9's saved production models need to genuinely re-score
    (SC-001 requires the real model be invoked, not a pass-through
    score) -- restricted internally to each artifact's own
    `feature_columns`. `current_affected_claims_amounts` is optional;
    omitting it reuses the incident's originally stored amounts (see
    tasks.md's Design Note 2)."""

    remediation_run_id: str
    current_claims: list[CurrentClaimState]
    anomaly_features: dict[str, float] = {}
    risk_features: dict[str, float] = {}
    current_affected_claims_amounts: list[float] | None = None


class RecomputedScores(BaseModel):
    """Internal carrier between `recompute_service.recompute` and
    `comparison_service.build_comparison`/`resolution_criteria.
    determine_resolution` -- not part of the public API response shape
    directly (that's `RevalidationRun`/`BeforeAfterComparison`/
    `ResolutionDetermination`)."""

    quality_results: list[dict]
    quality_score: float
    anomaly_score: float
    anomaly_score_percentile: float
    risk_score: float
    severity: float
    business_impact: float
    priority: float
    severity_business_impact_priority: dict
    anomaly_model_version: str
    risk_model_version: str


class RevalidationRun(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revalidation_id: str
    incident_id: str
    remediation_run_id: str
    recomputed_quality_results: list[dict]
    recomputed_anomaly_score: float
    recomputed_risk_score: float
    recomputed_severity_business_impact_priority: dict
    anomaly_model_version: str
    risk_model_version: str
    started_at: datetime
    completed_at: datetime | None


class BeforeAfterComparison(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revalidation_id: str
    quality_before: float
    quality_after: float
    quality_delta: float
    anomaly_before: float
    anomaly_after: float
    anomaly_delta: float
    risk_before: float
    risk_after: float
    risk_delta: float
    severity_before: float
    severity_after: float
    severity_delta: float
    priority_before: float
    priority_after: float
    priority_delta: float


class ResolutionOutcome(str, Enum):
    resolved = "resolved"
    reopened = "reopened"


class ResolutionDetermination(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revalidation_id: str
    outcome: ResolutionOutcome
    criteria_evaluated: dict
    blocked_by_manual_actions: bool


class RevalidationRunResponse(BaseModel):
    """The `POST /revalidation/{incident_id}/run` response shape
    (contracts/api.md) and one entry of `GET /revalidation/{incident_id}`'s
    history list."""

    revalidation_run: RevalidationRun
    comparison: BeforeAfterComparison
    resolution: ResolutionDetermination
    incident_status: str
