"""Default, validated weight sets for Severity and Priority (MVP_CONTEXT.md
Section 3.3; spec FR-004, FR-007, FR-010; research.md).

Both formulas' default weights sum to 1.0 exactly, which is the
"well-formed" convention FR-010 requires validating -- a configured
weight set that doesn't match its expected keys, or doesn't sum to
1.0 within a small floating-point tolerance, is a configuration error
surfaced immediately, not normalized or silently accepted (research.md:
"silently 'fixing' a misconfiguration is worse than surfacing it").
"""

from app.risk.scoring.errors import WeightConfigError

SEVERITY_DEFAULT_WEIGHTS: dict[str, float] = {"wq": 0.4, "wa": 0.4, "wm": 0.2}
PRIORITY_DEFAULT_WEIGHTS: dict[str, float] = {
    "w_severity": 0.40,
    "w_risk": 0.30,
    "w_business_impact": 0.20,
    "w_affected_claims": 0.10,
}

_SUM_TOLERANCE = 1e-6


def validate_weights(weights: dict[str, float], expected_keys: set[str]) -> None:
    actual_keys = set(weights.keys())
    if actual_keys != expected_keys:
        raise WeightConfigError(
            f"Weight set keys {sorted(actual_keys)} do not match the expected keys {sorted(expected_keys)}."
        )
    total = sum(weights.values())
    if abs(total - 1.0) > _SUM_TOLERANCE:
        raise WeightConfigError(f"Weights {weights} sum to {total}, expected 1.0 (±{_SUM_TOLERANCE}).")
