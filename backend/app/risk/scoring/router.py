"""Severity/Business Impact/Priority scoring API endpoint.

`POST /risk/score` is a thin convenience wrapper for manual invocation and
testing (contracts/api.md) -- production usage is Phase 12 calling
`severity.compute_severity`/`business_impact.compute_business_impact`/
`priority.compute_priority` directly, in-process.
"""

from fastapi import APIRouter, HTTPException

from app.risk.scoring import business_impact, priority, severity
from app.risk.scoring.errors import MissingRiskScoreError, WeightConfigError
from app.risk.scoring.schemas import ScoreRequest, ScoreResponse

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/score", response_model=ScoreResponse)
def score(request: ScoreRequest) -> ScoreResponse:
    weights = request.weights or None

    try:
        severity_result = severity.compute_severity(
            quality_check_bands=[c.band for c in request.quality_check_results],
            anomaly_score_percentile=request.anomaly_score,
            affected_claim_pct=request.affected_claim_pct,
            affected_claims_amounts=request.affected_claims_amounts,
            baseline_amount_percentiles=request.baseline_amount_percentiles,
            weights=(weights.severity if weights else None),
        )

        business_impact_result = business_impact.compute_business_impact(
            affected_claims_amounts=request.affected_claims_amounts,
            baseline_amount_percentiles=request.baseline_amount_percentiles,
        )

        priority_result = priority.compute_priority(
            severity=severity_result.severity,
            risk=request.risk_score,
            business_impact=business_impact_result.business_impact,
            affected_claims_score=priority.affected_claims_score(request.affected_claim_pct),
            weights=(weights.priority if weights else None),
        )
    except (MissingRiskScoreError, WeightConfigError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ScoreResponse(
        severity_result=severity_result,
        business_impact_result=business_impact_result,
        priority_result=priority_result,
    )
