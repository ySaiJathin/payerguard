"""Simulates Phase 14's before/after revalidation call pattern: the exact
same scoring functions are called twice, once with "pre-remediation"
input values and once with different "post-remediation" values, and both
calls must succeed independently and reproducibly (spec FR-011, SC-005).
"""

from app.baseline.schemas import Percentiles
from app.risk.scoring.business_impact import compute_business_impact
from app.risk.scoring.priority import affected_claims_score, compute_priority
from app.risk.scoring.severity import compute_severity


def _percentiles() -> Percentiles:
    return Percentiles(p25=500.0, p50=1500.0, p75=4000.0, p95=15000.0, p99=40000.0)


def _run_full_pipeline(quality_bands, anomaly_pct, claim_pct, amounts, risk):
    severity_result = compute_severity(
        quality_check_bands=quality_bands,
        anomaly_score_percentile=anomaly_pct,
        affected_claim_pct=claim_pct,
        affected_claims_amounts=amounts,
        baseline_amount_percentiles=_percentiles(),
    )
    business_impact_result = compute_business_impact(amounts, baseline_amount_percentiles=_percentiles())
    priority_result = compute_priority(
        severity=severity_result.severity,
        risk=risk,
        business_impact=business_impact_result.business_impact,
        affected_claims_score=affected_claims_score(claim_pct),
    )
    return severity_result, business_impact_result, priority_result


def test_scoring_functions_are_reusable_pre_and_post_remediation():
    # Pre-remediation: bad quality, high anomaly, several affected claims.
    pre_severity, pre_impact, pre_priority = _run_full_pipeline(
        quality_bands=["CRITICAL", "CRITICAL", "WARNING"],
        anomaly_pct=0.99,
        claim_pct=0.40,
        amounts=[5000.0, 8000.0, 12000.0],
        risk=0.75,
    )

    # Post-remediation: quality issues fixed, anomaly/affected-claim
    # exposure reduced -- same functions, different (revalidated) inputs.
    post_severity, post_impact, post_priority = _run_full_pipeline(
        quality_bands=["PASS", "PASS", "PASS"],
        anomaly_pct=0.10,
        claim_pct=0.05,
        amounts=[500.0],
        risk=0.10,
    )

    # Both calls succeed and are internally self-consistent (reproducible
    # from their own persisted inputs -- SC-001/SC-003).
    for severity_result, priority_result in ((pre_severity, pre_priority), (post_severity, post_priority)):
        expected_severity = (
            severity_result.weights_used["wq"] * severity_result.quality_failure_severity
            + severity_result.weights_used["wa"] * severity_result.anomaly_magnitude_score
            + severity_result.weights_used["wm"] * severity_result.materiality_score
        )
        assert severity_result.severity == expected_severity

    # Remediation genuinely improved the incident -- no shared mutable
    # state leaked between the two calls (the post-remediation run isn't
    # contaminated by the pre-remediation run's values).
    assert post_priority.priority < pre_priority.priority
    assert post_severity.severity < pre_severity.severity
    assert post_impact.business_impact <= pre_impact.business_impact
