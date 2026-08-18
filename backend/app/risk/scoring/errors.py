"""Error types for Severity/Business Impact/Priority scoring."""


class MissingRiskScoreError(ValueError):
    """Raised when `compute_priority` is called without a Risk Score
    (spec FR-009, SC-004) -- Priority MUST fail fast rather than
    substituting a fabricated default (e.g. 0 or 50) for a missing Phase 9
    production risk model score."""


class WeightConfigError(ValueError):
    """Raised when a supplied Severity or Priority weight set doesn't
    match its expected keys or doesn't sum to 1.0 within tolerance
    (spec FR-010) -- surfaced explicitly rather than silently producing a
    score outside the intended [0, 100] range."""
