# Feature Specification: Severity, Business Impact, and Priority Scoring

**Feature Branch**: `010-severity-impact-priority-scoring`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 10 — Severity, Business Impact, and Priority scoring (MVP_CONTEXT.md Section 5/3.3): compute Severity using the formula in Section 3.3 (quality-failure severity + anomaly magnitude + materiality). Compute Business Impact only from measurable claim-amount fields, explicitly marking any non-computable component (e.g. member-harm impact) as unavailable. Combine Quality + Anomaly + Risk + Severity + Business Impact into Final Incident Priority (0.40×Severity + 0.30×Risk + 0.20×Business Impact + 0.10×Affected Claims Score, weights configurable)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute Severity as a distinct, non-overlapping signal (Priority: P1)

As the implementer of incident creation (Phase 12), I need Severity computed via the documented three-component formula (quality-failure severity + anomaly magnitude + materiality), so incidents carry a real measure of "how bad is this specific finding" that is distinct from Quality, Anomaly, and Risk scores rather than double-counting the same evidence.

**Why this priority**: Severity is the largest weight (0.40) in the Priority formula and the newest, most-detailed formula MVP_CONTEXT.md defines (Section 3.3) — getting it right is foundational to everything else in this phase.

**Independent Test**: Can be tested by computing Severity for a window/incident with known Phase 3 GX results, Phase 7 anomaly score, and Phase 5 materiality-relevant data, and confirming the result matches hand-computing the documented formula with the default weights (wq=0.4, wa=0.4, wm=0.2).

**Acceptance Scenarios**:

1. **Given** a window's Phase 3 GX check results (CRITICAL/WARNING/PASS per check), **When** `QualityFailureSeverity` is computed, **Then** it equals the documented per-check scoring (CRITICAL=100, WARNING=50, PASS=0) averaged across the window's checks.
2. **Given** the window's Phase 7-benchmarked anomaly score (HBOS or whichever model won), **When** `AnomalyMagnitudeScore` is computed, **Then** it maps the anomaly score's percentile onto 0-100 using the same 95th/99th-percentile calibration established in Section 3.1/Phase 7.
3. **Given** the window's affected-claim % and claim-amount percentile data, **When** `MaterialityScore` is computed, **Then** it reflects the real percentage of claims affected and/or the dollar-amount percentile of affected claims relative to Phase 4's baseline.
4. **Given** all three components, **When** Severity is computed, **Then** it equals `0.40×QualityFailureSeverity + 0.40×AnomalyMagnitudeScore + 0.20×MaterialityScore` (default weights, configurable) — reproducible by hand from the persisted component values.

---

### User Story 2 - Compute Business Impact only from measurable fields, marking the rest explicitly unavailable (Priority: P1)

As someone accountable for the no-fabrication principle, I need Business Impact computed strictly from measurable claim-amount fields (total charge, payment amount, affected-claim dollar exposure), with any non-computable component (e.g., member-harm, provider-reputation impact) explicitly and visibly marked as unavailable rather than omitted or defaulted to zero, so the score never implies a false precision.

**Why this priority**: Equal priority to Story 1 — this is a specific, named non-fabrication requirement in MVP_CONTEXT.md Section 3.3, and Business Impact feeds directly into the Priority formula, so getting the "unavailable, not zero" distinction wrong would misrepresent every downstream Priority score.

**Independent Test**: Can be tested by computing Business Impact for an incident and confirming the output explicitly lists which components were computed (from real claim-amount data) versus explicitly marked unavailable, with the computed portion traceable to real dollar figures.

**Acceptance Scenarios**:

1. **Given** an incident's affected claims with known `CLM_PMT_AMT`/`CLM_TOT_CHRG_AMT`, **When** Business Impact is computed, **Then** the dollar-exposure component reflects the real sum/percentile of those affected claims' amounts.
2. **Given** no member-harm data exists anywhere in this dataset, **When** Business Impact is computed, **Then** the output explicitly marks a member-harm component as `unavailable` (a distinct, visible state) — it is never silently omitted or defaulted to 0, which would be indistinguishable from "measured zero impact."
3. **Given** the Business Impact output, **When** it's consumed by the Priority formula, **Then** only the computed (available) components contribute numerically — the "unavailable" marking is informational/auditable, not silently coerced into a numeric value.

---

### User Story 3 - Combine everything into Final Incident Priority (Priority: P1)

As the implementer of incident creation and the HITL review queue (Phase 12), I need a single Priority score combining Severity, Risk, Business Impact, and Affected Claims Score via the documented weighted formula, so incidents can be ranked and triaged consistently.

**Why this priority**: Equal priority — Priority is the score human reviewers actually see first; without it, Phases 12+ have no way to rank incidents.

**Independent Test**: Can be tested by computing Priority for an incident with known Severity, Risk (Phase 9), Business Impact, and Affected Claims Score values, and confirming it equals `0.40×Severity + 0.30×Risk + 0.20×BusinessImpact + 0.10×AffectedClaimsScore` with the default weights.

**Acceptance Scenarios**:

1. **Given** an incident's Severity (Story 1), Risk (Phase 9's production model score), Business Impact (Story 2), and Affected Claims Score (derived from affected-claim %), **When** Priority is computed, **Then** it equals the documented weighted formula applied to those exact persisted component values.
2. **Given** the weights are configurable (per Section 3.3), **When** a non-default weight set is supplied, **Then** Priority recomputes correctly using the supplied weights, and the weights actually used are recorded alongside the result.
3. **Given** Quality, Anomaly, Risk, Severity, and Business Impact are each distinct signals (per Section 3.3's explicit "non-overlapping" framing), **When** Priority is computed, **Then** no single upstream measurement (e.g., a GX failure) is double-counted across more than one of Severity's sub-components and the Priority formula's own inputs.

### Edge Cases

- What happens when Phase 9's Risk Score isn't yet available for a window/incident (e.g., the risk model hasn't scored it)? Priority computation MUST fail fast or explicitly flag the missing input rather than defaulting Risk to a fabricated value (e.g., 0 or 50).
- What happens when a window has zero affected claims (materiality/affected-claims score would be trivially zero)? This MUST be a genuine computed zero (not confused with "unavailable") since claim data does exist for the window, just with none affected.
- What happens if the configured weights for Severity or Priority don't sum to 1.0 (or another documented convention)? The system MUST validate this and surface a configuration error rather than silently producing a score outside the intended 0-100 range.
- What happens to Business Impact when an incident has affected claims but ALL of their amount fields are missing? The dollar-exposure component MUST be marked unavailable for that incident (not defaulted to 0, which would misrepresent "no impact" versus "impact unknown").
- What happens when this scoring is recomputed after remediation (Phase 14's revalidation)? The formula and component logic MUST be identical/reusable for a before/after comparison — this feature's scoring functions MUST be callable again post-remediation without duplicating logic.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute `QualityFailureSeverity` as the average of per-check severity values (CRITICAL=100, WARNING=50, PASS=0) across a window/incident's Phase 3 GX check results.
- **FR-002**: System MUST compute `AnomalyMagnitudeScore` by mapping the Phase 7-selected production model's anomaly score onto 0-100 using the same percentile calibration established in Section 3.1/Phase 7.
- **FR-003**: System MUST compute `MaterialityScore` from the real affected-claim percentage and/or claim-amount percentile of affected claims relative to Phase 4's baseline.
- **FR-004**: System MUST compute Severity as `wq×QualityFailureSeverity + wa×AnomalyMagnitudeScore + wm×MaterialityScore`, with default weights `wq=0.4, wa=0.4, wm=0.2`, configurable, and MUST persist the weights actually used alongside every computed Severity.
- **FR-005**: System MUST compute Business Impact's dollar-exposure component only from measurable claim-amount fields (`CLM_PMT_AMT`, `CLM_TOT_CHRG_AMT`, and related affected-claim dollar exposure).
- **FR-006**: System MUST explicitly mark any Business Impact component that cannot be computed from this dataset (e.g., member-harm, provider-reputation impact) as `unavailable` — a distinct state from a computed zero — and MUST NOT include unavailable components as a numeric 0 in any downstream sum.
- **FR-007**: System MUST compute Final Incident Priority as `0.40×Severity + 0.30×Risk + 0.20×BusinessImpact + 0.10×AffectedClaimsScore`, with weights configurable, using Phase 9's production risk model score as the Risk input.
- **FR-008**: System MUST persist the weights actually used for every Priority computation alongside the result.
- **FR-009**: System MUST fail fast or explicitly flag a missing required input (e.g., Risk Score not yet available) rather than substituting a fabricated default value.
- **FR-010**: System MUST validate that configured weight sets are well-formed (e.g., sum to the documented convention) and surface a configuration error otherwise, rather than silently producing an out-of-range score.
- **FR-011**: System MUST expose Severity/Business Impact/Priority computation as reusable, idempotent functions callable again after remediation (Phase 14) for before/after comparison, without duplicated logic.
- **FR-012**: System MUST NOT fabricate any component value — every numeric input is either a real computed value or explicitly marked unavailable (constitution Principle II).

### Key Entities

- **SeverityResult**: `quality_failure_severity`, `anomaly_magnitude_score`, `materiality_score`, weights used, and the computed `severity` (0-100).
- **BusinessImpactResult**: computed dollar-exposure component(s), a list of components explicitly marked `unavailable` with reasons, and the resulting numeric Business Impact (0-100) derived only from available components.
- **PriorityResult**: Severity, Risk, Business Impact, Affected Claims Score inputs, weights used, and the computed Priority (0-100).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every `SeverityResult.severity` is exactly reproducible by re-applying the documented formula to its own persisted component values and weights.
- **SC-002**: 100% of `BusinessImpactResult` outputs explicitly distinguish computed components from `unavailable` components — zero instances where an unavailable component is silently treated as 0 in the final Business Impact number.
- **SC-003**: Every `PriorityResult.priority` (a) is exactly reproducible by re-applying the documented formula to its own persisted component values and weights, and (b) falls within [0, 100].
- **SC-004**: Zero Priority computations proceed with a fabricated/defaulted Risk Score when the real one is unavailable — verified by a test that omits the Risk input and confirms an explicit failure/flag, not a default value.
- **SC-005**: Severity/Business Impact/Priority computation functions are successfully re-invoked in a post-remediation (Phase 14-style) test scenario without modification, confirming reusability (FR-011).

## Assumptions

- "Affected Claims Score" (the Priority formula's fourth input) is derived from the same affected-claim % concept already established in Phase 8's `RiskDatasetRow.affected_claim_pct`, scaled to 0-100 — this spec reuses that existing, real signal rather than defining a new one from scratch.
- The default weight convention (Severity weights summing to 1.0; Priority weights summing to 1.0) is validated as the "well-formed" convention referenced in FR-010; this mirrors the default weights MVP_CONTEXT.md Section 3.3 itself documents summing to 1.0 in both formulas.
- This feature computes Severity/Business Impact/Priority as reusable scoring functions; it does not itself create or persist `Incident` records (that's Phase 12) — Phase 12 calls into this feature's scoring functions when an incident is created or revalidated.
