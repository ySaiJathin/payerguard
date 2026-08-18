"""Pydantic models for Severity/Business Impact/Priority scoring.

See specs/010-severity-impact-priority-scoring/data-model.md for field
definitions and validation rules.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.baseline.schemas import Percentiles


class SeverityResult(BaseModel):
    quality_failure_severity: float
    anomaly_magnitude_score: float
    materiality_score: float
    weights_used: dict[str, float]
    severity: float
    computed_at: datetime


class BusinessImpactComponent(BaseModel):
    name: str
    value: float | None
    status: Literal["computed", "unavailable"]
    reason: str | None = None


class BusinessImpactResult(BaseModel):
    components: list[BusinessImpactComponent]
    has_unavailable_components: bool
    business_impact: float
    computed_at: datetime


class PriorityResult(BaseModel):
    severity: float
    risk: float
    business_impact: float
    affected_claims_score: float
    weights_used: dict[str, float]
    priority: float
    computed_at: datetime


class QualityCheckBandInput(BaseModel):
    band: Literal["CRITICAL", "WARNING", "PASS"]


class ScoreWeightsInput(BaseModel):
    severity: dict[str, float] | None = None
    priority: dict[str, float] | None = None


class ScoreRequest(BaseModel):
    """Request body for the `POST /risk/score` convenience endpoint
    (contracts/api.md). `baseline_amount_percentiles` is an additive,
    optional field beyond quickstart.md's illustrative example -- without
    it, `business_impact()`'s dollar-exposure component and
    `materiality_score()`'s amount component both fall back to their
    documented "unavailable" / claim-pct-only behavior rather than
    fabricating a scale to bucket dollar amounts against.
    """

    quality_check_results: list[QualityCheckBandInput] = []
    anomaly_score: float = 0.0
    affected_claim_pct: float = 0.0
    affected_claims_amounts: list[float] = []
    risk_score: float | None = None
    baseline_amount_percentiles: Percentiles | None = None
    weights: ScoreWeightsInput | None = None


class ScoreResponse(BaseModel):
    severity_result: SeverityResult
    business_impact_result: BusinessImpactResult
    priority_result: PriorityResult
