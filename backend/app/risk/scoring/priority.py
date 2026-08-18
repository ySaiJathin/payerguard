"""Final Incident Priority: combines Severity, Risk, Business Impact, and
Affected Claims Score -- the four distinct signals -- into the one score
human reviewers see first (MVP_CONTEXT.md Section 3.3; spec FR-007,
FR-008, FR-009).

    Priority = w_severity*Severity + w_risk*Risk + w_business_impact*BusinessImpact + w_affected_claims*AffectedClaimsScore

Risk has no safe default: unlike a genuinely-zero-affected-claims window
(a real computed 0), a *missing* Risk Score means Phase 9's production
model simply hasn't scored this window yet -- substituting 0 or any other
value would fabricate evidence a human reviewer would treat as real
(spec FR-009, SC-004), so `compute_priority` raises immediately instead.
"""

from datetime import datetime, timezone

from app.risk.scoring import weight_config
from app.risk.scoring.errors import MissingRiskScoreError
from app.risk.scoring.schemas import PriorityResult


def affected_claims_score(affected_claim_pct: float) -> float:
    """Scales Phase 8's `RiskDatasetRow.affected_claim_pct` concept (a 0-1
    fraction) onto 0-100 (spec Assumptions -- reuses the existing signal
    rather than defining a new one)."""
    return max(0.0, min(100.0, affected_claim_pct * 100.0))


def compute_priority(
    severity: float,
    risk: float | None,
    business_impact: float,
    affected_claims_score: float,
    weights: dict[str, float] | None = None,
) -> PriorityResult:
    if risk is None:
        raise MissingRiskScoreError(
            "Priority cannot be computed without a Risk Score -- run Phase 9's production risk model "
            "against this window first rather than substituting a default value."
        )

    weights = weights or weight_config.PRIORITY_DEFAULT_WEIGHTS
    weight_config.validate_weights(
        weights, {"w_severity", "w_risk", "w_business_impact", "w_affected_claims"}
    )

    priority = (
        weights["w_severity"] * severity
        + weights["w_risk"] * risk
        + weights["w_business_impact"] * business_impact
        + weights["w_affected_claims"] * affected_claims_score
    )
    priority = max(0.0, min(100.0, priority))

    return PriorityResult(
        severity=severity,
        risk=risk,
        business_impact=business_impact,
        affected_claims_score=affected_claims_score,
        weights_used=weights,
        priority=priority,
        computed_at=datetime.now(timezone.utc),
    )
