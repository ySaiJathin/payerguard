"""Business Impact: dollar/operational consequence, computed only from
measurable claim-amount fields -- any non-computable component (member-
harm, provider-reputation impact) is explicitly marked `unavailable`,
never silently omitted or defaulted to 0 (MVP_CONTEXT.md Section 3.3;
spec FR-005, FR-006).

`business_impact` is the mean of only the `status=="computed"` components.
When every component is unavailable, that mean is 0.0 by construction
(a mean of zero terms) -- this is NOT the same thing as "measured zero
impact," and callers MUST check `has_unavailable_components` before
treating `business_impact == 0.0` as a genuine finding, since the two
cases are otherwise indistinguishable as plain floats (research.md's
tagged-sentinel decision exists precisely so `components` -- not the
summary float alone -- is the auditable source of truth).
"""

from datetime import datetime, timezone

from app.baseline.schemas import Percentiles
from app.risk.scoring.percentile_scaling import percentile_bucket_score
from app.risk.scoring.schemas import BusinessImpactComponent, BusinessImpactResult

MEMBER_HARM_UNAVAILABLE_REASON = (
    "No member-harm or clinical-outcome field exists in this dataset (MVP_CONTEXT.md Section 2)."
)
PROVIDER_REPUTATION_UNAVAILABLE_REASON = (
    "No provider-reputation or complaint field exists in this dataset (MVP_CONTEXT.md Section 2)."
)


def compute_business_impact(
    affected_claims_amounts: list[float],
    baseline_amount_percentiles: Percentiles | None = None,
) -> BusinessImpactResult:
    valid_amounts = [a for a in (affected_claims_amounts or []) if a is not None]

    if not valid_amounts:
        dollar_exposure = BusinessImpactComponent(
            name="dollar_exposure",
            value=None,
            status="unavailable",
            reason="No affected-claim amount data available (all amount fields missing or no affected claims).",
        )
    elif baseline_amount_percentiles is None:
        dollar_exposure = BusinessImpactComponent(
            name="dollar_exposure",
            value=None,
            status="unavailable",
            reason="No baseline amount percentiles supplied to scale the dollar exposure against.",
        )
    else:
        dollar_exposure = BusinessImpactComponent(
            name="dollar_exposure",
            value=percentile_bucket_score(sum(valid_amounts), baseline_amount_percentiles),
            status="computed",
            reason=None,
        )

    member_harm = BusinessImpactComponent(
        name="member_harm_impact", value=None, status="unavailable", reason=MEMBER_HARM_UNAVAILABLE_REASON
    )
    provider_reputation = BusinessImpactComponent(
        name="provider_reputation_impact",
        value=None,
        status="unavailable",
        reason=PROVIDER_REPUTATION_UNAVAILABLE_REASON,
    )

    components = [dollar_exposure, member_harm, provider_reputation]
    computed_values = [c.value for c in components if c.status == "computed" and c.value is not None]
    business_impact = sum(computed_values) / len(computed_values) if computed_values else 0.0

    return BusinessImpactResult(
        components=components,
        has_unavailable_components=any(c.status == "unavailable" for c in components),
        business_impact=max(0.0, min(100.0, business_impact)),
        computed_at=datetime.now(timezone.utc),
    )
