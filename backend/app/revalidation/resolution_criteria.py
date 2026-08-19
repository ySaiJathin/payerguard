"""Documented Resolved/Reopened resolution criteria (spec FR-007, FR-008;
research.md's "no CRITICAL GX checks, anomaly score in NORMAL band, risk
below the investigation threshold" decision).

Reuses the exact 95th-percentile NORMAL-band boundary and risk-band
threshold MVP_CONTEXT.md Section 3.1 already defines, rather than
inventing new resolution-specific thresholds.
"""

from app.revalidation.schemas import ResolutionDetermination, ResolutionOutcome

# The Section 3.1 NORMAL-band ceiling (below the 95th percentile) --
# same anchor `recompute_service`'s percentile conversion uses.
ANOMALY_NORMAL_BAND_CEILING = 0.95

# The investigation-worthy risk threshold on the 0-100 scale (research.md
# references Section 3.1's risk bands, LOW/below-MEDIUM) -- overridable
# by the caller, not hardcoded into the decision logic itself.
DEFAULT_RISK_THRESHOLD = 50.0


def determine_resolution(
    revalidation_id: str,
    quality_results: list[dict],
    anomaly_score_percentile: float,
    risk_score_0_100: float,
    has_outstanding_manual_actions: bool,
    risk_threshold: float = DEFAULT_RISK_THRESHOLD,
) -> ResolutionDetermination:
    no_critical_gx = not any(result.get("band") == "CRITICAL" for result in quality_results)
    anomaly_in_normal_band = anomaly_score_percentile < ANOMALY_NORMAL_BAND_CEILING
    risk_below_threshold = risk_score_0_100 < risk_threshold
    no_outstanding_manual_actions = not has_outstanding_manual_actions

    criteria_evaluated = {
        "no_critical_gx": no_critical_gx,
        "anomaly_in_normal_band": anomaly_in_normal_band,
        "risk_below_threshold": risk_below_threshold,
        "no_outstanding_manual_actions": no_outstanding_manual_actions,
    }

    all_clear = all(criteria_evaluated.values())
    outcome = ResolutionOutcome.resolved if all_clear else ResolutionOutcome.reopened

    # True only when manual actions were the *sole* reason "resolved" was
    # withheld (data-model.md's field note) -- every other criterion
    # cleared, but the outstanding manual action blocked it.
    signals_would_clear_alone = no_critical_gx and anomaly_in_normal_band and risk_below_threshold
    blocked_by_manual_actions = has_outstanding_manual_actions and signals_would_clear_alone

    return ResolutionDetermination(
        revalidation_id=revalidation_id,
        outcome=outcome,
        criteria_evaluated=criteria_evaluated,
        blocked_by_manual_actions=blocked_by_manual_actions,
    )
