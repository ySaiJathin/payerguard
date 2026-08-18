"""Severity: the magnitude of an incident itself, independent of whether
it turns out to be a true risk or what it costs (MVP_CONTEXT.md Section
3.3; spec FR-001-FR-004).

    Severity = wq * QualityFailureSeverity + wa * AnomalyMagnitudeScore + wm * MaterialityScore

**AnomalyMagnitudeScore's input**: per research.md, this module is a pure
function library that never re-fetches Phase 7's raw validation-score
distribution. So `anomaly_score_percentile` is the window's *percentile
rank* relative to that distribution (0-1 scale) -- the caller (Phase 12)
computes that rank once against Phase 7's calibration, and this function
owns only the percentile-to-0-100 mapping curve, anchored at the same
95th/99th-percentile breakpoints MVP_CONTEXT.md Section 3.1 defines for
HBOS's NORMAL/WARNING/CRITICAL bands -- continuous instead of a flat
three-way classification, so severity scales with how extreme the anomaly
actually is.
"""

from datetime import datetime, timezone

from app.baseline.schemas import Percentiles
from app.risk.scoring import weight_config
from app.risk.scoring.percentile_scaling import percentile_bucket_score
from app.risk.scoring.schemas import SeverityResult

_BAND_SCORES = {"CRITICAL": 100.0, "WARNING": 50.0, "PASS": 0.0}


def quality_failure_severity(quality_check_bands: list[str]) -> float:
    if not quality_check_bands:
        return 0.0
    return sum(_BAND_SCORES[band] for band in quality_check_bands) / len(quality_check_bands)


def anomaly_magnitude_score(anomaly_score_percentile: float) -> float:
    p = max(0.0, min(1.0, anomaly_score_percentile))
    if p < 0.95:
        return (p / 0.95) * 50.0
    if p < 0.99:
        return 50.0 + ((p - 0.95) / 0.04) * 40.0
    return 90.0 + ((p - 0.99) / 0.01) * 10.0


def materiality_score(
    affected_claim_pct: float,
    affected_claims_amounts: list[float] | None = None,
    baseline_amount_percentiles: Percentiles | None = None,
) -> float:
    claim_pct_component = max(0.0, min(100.0, affected_claim_pct * 100.0))

    valid_amounts = [a for a in (affected_claims_amounts or []) if a is not None]
    if valid_amounts and baseline_amount_percentiles is not None:
        amount_component = percentile_bucket_score(sum(valid_amounts), baseline_amount_percentiles)
        return (claim_pct_component + amount_component) / 2.0

    return claim_pct_component


def compute_severity(
    quality_check_bands: list[str],
    anomaly_score_percentile: float,
    affected_claim_pct: float,
    affected_claims_amounts: list[float] | None = None,
    baseline_amount_percentiles: Percentiles | None = None,
    weights: dict[str, float] | None = None,
) -> SeverityResult:
    weights = weights or weight_config.SEVERITY_DEFAULT_WEIGHTS
    weight_config.validate_weights(weights, {"wq", "wa", "wm"})

    qfs = quality_failure_severity(quality_check_bands)
    ams = anomaly_magnitude_score(anomaly_score_percentile)
    ms = materiality_score(affected_claim_pct, affected_claims_amounts, baseline_amount_percentiles)

    severity = weights["wq"] * qfs + weights["wa"] * ams + weights["wm"] * ms
    severity = max(0.0, min(100.0, severity))

    return SeverityResult(
        quality_failure_severity=qfs,
        anomaly_magnitude_score=ams,
        materiality_score=ms,
        weights_used=weights,
        severity=severity,
        computed_at=datetime.now(timezone.utc),
    )
