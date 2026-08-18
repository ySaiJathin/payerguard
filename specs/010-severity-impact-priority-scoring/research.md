# Phase 0 Research: Severity, Business Impact, and Priority Scoring

## Decision: `unavailable` represented as a tagged sentinel, structurally excluded from sums

**Decision**: `BusinessImpactResult.components` is a list of `{name, value: float | null, status: "computed" | "unavailable", reason}` entries; the final `business_impact` numeric score sums only entries with `status == "computed"`, and the presence of any `unavailable` entry is surfaced as a top-level `has_unavailable_components: true` flag.

**Rationale**: FR-006/SC-002 require "unavailable" to be structurally distinct from a computed zero, not just a documentation convention that a future refactor could accidentally violate by defaulting a missing field to `0.0`. A tagged sentinel with an explicit status field, combined with a sum that filters by status, makes the distinction enforced by the data structure itself rather than by programmer discipline alone.

**Alternatives considered**: Using `null` alone without a `status` field (rejected — `null` could be ambiguous with "not yet computed" versus "genuinely unavailable in this dataset"; the explicit `status` + `reason` pair is more auditable and self-documenting).

## Decision: `AnomalyMagnitudeScore` reuses Phase 7's exact percentile calibration, not a new mapping

**Decision**: `severity.py` calls into Phase 7's `hbos.py` (or whichever model was selected) percentile-to-band calibration function directly, rather than reimplementing a 0-100 mapping from anomaly scores.

**Rationale**: Spec Acceptance Scenario 2 for User Story 1 requires "the same 95th/99th-percentile calibration established in Section 3.1/Phase 7" — reusing the exact function guarantees consistency and avoids a second, potentially-diverging calibration curve.

**Alternatives considered**: An independent linear rescaling of raw anomaly scores to 0-100 (rejected — would not match Phase 7's percentile-based calibration, and the spec explicitly requires "the same" calibration, not merely a similar one).

## Decision: Weight validation requires each formula's weights to sum to 1.0 within a small floating-point tolerance

**Decision**: `weight_config.py` validates that Severity's `{wq, wa, wm}` and Priority's `{w_severity, w_risk, w_business_impact, w_affected_claims}` each sum to `1.0 ± 1e-6`; a configuration outside that tolerance raises a typed configuration error before any score is computed.

**Rationale**: FR-010 requires validating "the documented convention" — MVP_CONTEXT.md Section 3.3 documents both formulas' default weights summing to 1.0 (`0.4+0.4+0.2` and `0.40+0.30+0.20+0.10`), so this is the natural, already-established convention to enforce, keeping every score within the intended [0, 100] range.

**Alternatives considered**: No validation, trusting configuration (rejected — directly risks FR-010's "surface a configuration error... rather than silently producing an out-of-range score" requirement being violated); allowing weights to sum to any positive total and normalizing at compute time (rejected — silently "fixing" a misconfiguration is worse than surfacing it, since it would hide a real config mistake from whoever set the weights).

## Decision: Scoring functions take fully-resolved inputs, never fetch their own dependencies

**Decision**: `severity()`, `business_impact()`, and `priority()` are pure functions accepting already-resolved input values (e.g., `severity(quality_failure_severity, anomaly_magnitude_score, materiality_score, weights)`), not functions that reach into Phase 3/4/7/9's stores themselves.

**Rationale**: This is what makes FR-011's reusability requirement (callable again after remediation, Phase 14) trivial to satisfy — a pure function with no hidden data-fetching has no reason to behave differently pre- vs. post-remediation beyond the caller supplying different (revalidated) input values. It also makes SC-001/SC-003's "reproducible by re-applying the formula to persisted values" trivially true by construction.

**Alternatives considered**: Scoring functions that internally query Phase 3/7/9's latest results (rejected — couples this feature to every upstream module's storage/API details, and makes "recompute Severity for the same window before and after remediation" ambiguous about which data snapshot is used unless the caller explicitly controls the inputs).
