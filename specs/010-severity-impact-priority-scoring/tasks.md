---

description: "Task list for Severity, Business Impact, and Priority Scoring"
---

# Tasks: Severity, Business Impact, and Priority Scoring

**Input**: Design documents from `/specs/010-severity-impact-priority-scoring/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md — all present. Unlike Phases 8/9, this feature is a pure computation library (research.md's "take fully-resolved inputs, never fetch their own dependencies" decision) — it has no upstream file/data dependency to check at runtime, only a compile-time expectation that its callers (Phase 12/14) will eventually supply real Phase 3/4/7/8/9 values.

**Tests**: Included — plan.md's Testing section names 5 test files matching the spec's 5 Success Criteria exactly.

**Organization**: Tasks are grouped by user story. All three stories are P1. US1 (Severity) has no dependency on US2/US3. US2 (Business Impact) has no dependency on US1/US3. US3 (Priority) composes US1's and US2's *output values* (per research.md, by value — `priority()` takes `severity: float`/`business_impact: float` as plain numbers, not by calling into `severity()`/`business_impact()` itself), so it is sequenced last even though it has no hard code dependency on their internals, purely so its tests have real `SeverityResult`/`BusinessImpactResult` values to compose against.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (Severity), US2 (Business Impact), US3 (Priority, combining everything)

## Path Conventions

Backend module: `backend/app/risk/scoring/` (new sub-package inside the existing `backend/app/risk/` module, alongside Phase 8's `dataset/` and Phase 9's `benchmark/`, completing MVP_CONTEXT.md Section 3's `risk (logistic, random_forest, xgboost, benchmark, scoring)` list). Tests: `backend/tests/risk/scoring/`.

**Note on `backend/app/risk/scoring.py`**: repo scaffolding created this as a placeholder *file*. plan.md's Project Structure requires `scoring` to be a *sub-package* (directory). Setup replaces the file with the directory.

**Design note carried into every task below**: per research.md, `severity()`/`business_impact()`/`priority()` are pure functions taking already-resolved values — they never read Phase 3/4/7/8/9's persisted files themselves. This is what makes FR-011 (reusable post-remediation) and SC-001/SC-003 (reproducible from persisted values) true by construction, and it's why this feature's router endpoint is explicitly a thin manual-testing convenience wrapper, not the production call path (Phase 12 calls the functions directly, in-process).

---

## Phase 1: Setup

**Purpose**: Align the existing Phase-0 scaffold with plan.md's exact module boundary before any real code goes in.

- [x] T001 Delete the placeholder `backend/app/risk/scoring.py` and `backend/app/risk/router.py` stub files — plan.md's Project Structure places this feature's router at `backend/app/risk/scoring/router.py` instead, so the top-level `risk/router.py` stub (whose own docstring already said "Risk scoring API endpoints") is superseded, the same way Phase 8/9 deleted their now-redundant top-level placeholders
- [x] T002 Create `backend/app/risk/scoring/__init__.py`, so `scoring` becomes a sub-package per plan.md's Project Structure
- [x] T003 [P] Create `backend/tests/risk/scoring/__init__.py`

**Checkpoint**: Module skeleton matches plan.md exactly; ready for real implementation.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas, errors, weight validation, and the percentile-bucketing helper every user story's code depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Define `SeverityResult`, `BusinessImpactComponent` (`name`, `value: float | None`, `status: Literal["computed","unavailable"]`, `reason: str | None`), `BusinessImpactResult`, `PriorityResult` Pydantic models in `backend/app/risk/scoring/schemas.py` per data-model.md's field tables, plus `ScoreRequest`/`ScoreResponse` models matching contracts/api.md's `POST /risk/score` request/response shape (with an additive optional `baseline_amount_percentiles: Percentiles | None` field on `ScoreRequest`, reusing `app.baseline.schemas.Percentiles` — needed because `business_impact()`'s dollar-exposure component requires a baseline to scale against, but quickstart.md's illustrative example predates this need; documented as an additive, backward-compatible field)
- [x] T005 [P] Define `MissingRiskScoreError` (spec FR-009, SC-004) and `WeightConfigError` (spec FR-010) in `backend/app/risk/scoring/errors.py`
- [x] T006 [P] Implement `backend/app/risk/scoring/weight_config.py`: `SEVERITY_DEFAULT_WEIGHTS = {"wq": 0.4, "wa": 0.4, "wm": 0.2}`, `PRIORITY_DEFAULT_WEIGHTS = {"w_severity": 0.40, "w_risk": 0.30, "w_business_impact": 0.20, "w_affected_claims": 0.10}`, `validate_weights(weights, expected_keys)` raising `WeightConfigError` when keys don't match `expected_keys` exactly or the values don't sum to `1.0 ± 1e-6` (research.md)
- [x] T007 [P] Implement `backend/app/risk/scoring/percentile_scaling.py`: `percentile_bucket_score(value, percentiles: Percentiles) -> float` — a shared piecewise-linear mapping (0 at 0, 20 at p25, 40 at p50, 60 at p75, 80 at p95, 95 at p99, saturating to 100 beyond) reused by both `materiality_score()` (US1) and `business_impact()`'s dollar-exposure component (US2), so both "dollar amount relative to Phase 4's baseline" computations use one documented curve, not two independently-invented ones

**Checkpoint**: Foundation ready — Severity, Business Impact, and Priority work can now begin in any order.

---

## Phase 3: User Story 1 - Compute Severity as a distinct, non-overlapping signal (Priority: P1)

**Goal**: `QualityFailureSeverity` + `AnomalyMagnitudeScore` + `MaterialityScore`, combined via the documented, weighted, reproducible formula.

**Independent Test**: Compute Severity for known Phase 3/7/5 inputs and confirm the result matches hand-computing the documented formula with default weights.

### Implementation for User Story 1

- [x] T008 [US1] Implement `backend/app/risk/scoring/severity.py`: `quality_failure_severity(quality_check_bands: list[str]) -> float` (average of CRITICAL=100/WARNING=50/PASS=0 across the given bands, 0.0 for an empty list — no checks means no observed quality failure); `anomaly_magnitude_score(anomaly_score_percentile: float) -> float` (piecewise-linear through the same 95th/99th-percentile breakpoints Section 3.1/Phase 7 use — `[0, 0.95) → 0-50`, `[0.95, 0.99) → 50-90`, `[0.99, 1.0] → 90-100` — taking the window's *percentile rank* relative to Phase 7's calibration distribution as input, since a pure function per research.md cannot re-fetch Phase 7's raw validation-score array itself; the caller computes that percentile rank and passes it in); `materiality_score(affected_claim_pct, affected_claims_amounts=None, baseline_amount_percentiles=None) -> float` (claim-pct component, `affected_claim_pct * 100`, is always available per FR-003's "and/or"; when `affected_claims_amounts` and `baseline_amount_percentiles` are both supplied, averages in `percentile_scaling.percentile_bucket_score(sum(affected_claims_amounts), baseline_amount_percentiles)`, otherwise uses the claim-pct component alone); `compute_severity(quality_check_bands, anomaly_score_percentile, affected_claim_pct, affected_claims_amounts=None, baseline_amount_percentiles=None, weights=None) -> SeverityResult` (validates weights via `weight_config.validate_weights`, computes the three components, combines via `wq*qfs + wa*ams + wm*ms` clamped to [0,100])
- [x] T009 [P] [US1] `backend/tests/risk/scoring/test_severity_formula.py`: hand-computes the documented formula against a fixture set of quality-check bands/anomaly percentile/affected-claim data and asserts it matches `compute_severity`'s output exactly (SC-001), including a case with non-default weights and a case where a malformed weight set (not summing to 1.0) raises `WeightConfigError` (FR-010)

**Checkpoint**: Severity is independently computable and testable.

---

## Phase 4: User Story 2 - Compute Business Impact only from measurable fields, marking the rest explicitly unavailable (Priority: P1)

**Goal**: A dollar-exposure component computed from real claim amounts, with every non-computable component (member-harm, provider-reputation) structurally and visibly marked `unavailable` — never silently coerced into 0.

**Independent Test**: Compute Business Impact and confirm the output explicitly lists computed vs. `unavailable` components, with the computed portion traceable to real dollar figures.

### Implementation for User Story 2

- [x] T010 [US2] Implement `backend/app/risk/scoring/business_impact.py`: `compute_business_impact(affected_claims_amounts: list[float], baseline_amount_percentiles: Percentiles | None = None) -> BusinessImpactResult` — a `dollar_exposure` component with `status="computed"` (value = `percentile_scaling.percentile_bucket_score(sum(affected_claims_amounts), baseline_amount_percentiles)`) only when `affected_claims_amounts` contains at least one real amount *and* `baseline_amount_percentiles` is supplied; otherwise `status="unavailable"` with a reason naming which precondition was missing (spec Edge Cases: "ALL amount fields missing" → unavailable, not defaulted to 0); a `member_harm_impact` component and a `provider_reputation_impact` component always present with `status="unavailable"` and a reason citing MVP_CONTEXT.md Section 2 (no such field exists in this dataset); `business_impact_result.business_impact` = the mean of only the `status=="computed"` components' values (0.0, by construction of an empty mean, when nothing was computable — `has_unavailable_components` is the field callers must check before treating that 0.0 as a genuine "no impact" measurement, since a mean-of-nothing and a real computed zero are otherwise indistinguishable as floats; documented explicitly in the docstring)
- [x] T011 [P] [US2] `backend/tests/risk/scoring/test_business_impact_unavailable.py`: asserts `member_harm_impact` is always present with `status="unavailable"` (spec Acceptance Scenario 2); asserts `dollar_exposure` is `status="computed"` and traceable to the real sum of supplied amounts when a baseline is given (Acceptance Scenario 1); asserts `business_impact` never silently includes an unavailable component as a numeric 0 by comparing against a hand-computed mean of only the computed components (SC-002); asserts `dollar_exposure` becomes `status="unavailable"` (not 0) when all supplied amounts are empty/missing (Edge Cases)

**Checkpoint**: Business Impact is independently computable and testable, structurally distinguishing unavailable from zero.

---

## Phase 5: User Story 3 - Combine everything into Final Incident Priority (Priority: P1)

**Goal**: A single, documented, reproducible Priority score combining Severity, Phase 9's Risk Score, Business Impact, and Affected Claims Score — failing fast rather than defaulting when Risk is missing — plus the `POST /risk/score` convenience endpoint.

**Independent Test**: Compute Priority for known Severity/Risk/Business-Impact/Affected-Claims-Score values and confirm it equals the documented weighted formula.

### Implementation for User Story 3

- [x] T012 [US3] Implement `backend/app/risk/scoring/priority.py`: `affected_claims_score(affected_claim_pct: float) -> float` (`affected_claim_pct * 100`, clamped [0,100] — reuses Phase 8's `RiskDatasetRow.affected_claim_pct` concept per spec Assumptions, taken as a plain float input, not fetched); `compute_priority(severity: float, risk: float | None, business_impact: float, affected_claims_score: float, weights=None) -> PriorityResult` — raises `MissingRiskScoreError` immediately if `risk is None` (FR-009, SC-004, *before* touching weight validation or arithmetic), otherwise validates weights via `weight_config.validate_weights` and computes `w_severity*severity + w_risk*risk + w_business_impact*business_impact + w_affected_claims*affected_claims_score`, clamped [0,100]
- [x] T013 [US3] Implement `backend/app/risk/scoring/router.py`: `POST /risk/score` — parses `ScoreRequest`, calls `severity.compute_severity`, `business_impact.compute_business_impact`, `priority.affected_claims_score` + `priority.compute_priority` in sequence, returns `ScoreResponse` (`severity_result`, `business_impact_result`, `priority_result`); catches `MissingRiskScoreError`/`WeightConfigError` and returns `422` per contracts/api.md
- [x] T014 [US3] Register the new `backend/app/risk/scoring/router.py` router in `backend/app/main.py`, updating the "still placeholders" comment
- [x] T015 [P] [US3] `backend/tests/risk/scoring/test_priority_formula.py`: hand-computes the documented weighted formula against fixture Severity/Risk/BusinessImpact/AffectedClaimsScore values and asserts it matches `compute_priority`'s output exactly, including a non-default-weights case with the weights actually used recorded in the result (SC-003, spec Acceptance Scenario 2), and a malformed-weight-set case raising `WeightConfigError`
- [x] T016 [P] [US3] `backend/tests/risk/scoring/test_missing_risk_input.py`: asserts `compute_priority(risk=None, ...)` raises `MissingRiskScoreError` rather than substituting a default, and that `POST /risk/score` with no `risk_score` in the request body returns `422` (SC-004)
- [x] T017 [P] [US3] `backend/tests/risk/scoring/test_reusability_post_remediation.py`: calls `compute_severity`/`compute_business_impact`/`compute_priority` once with "pre-remediation" fixture inputs and again with different "post-remediation" fixture inputs (simulating Phase 14's before/after call), asserting both calls succeed independently, produce internally self-consistent results (reproducible per SC-001/SC-003), and that no shared mutable state leaks between the two calls (SC-005, FR-011)

**Checkpoint**: All three user stories independently functional; `POST /risk/score` runs end-to-end. Phase 12 can now build incident creation on top of these scoring functions.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T018 Run quickstart.md's manual verification steps end-to-end against a running backend (score a sample incident → verify Business Impact unavailable≠0 → verify missing-Risk 422 → verify Priority reproducibility → run the reusability test) and fix any drift between the contracts and the implementation
- [x] T019 [P] Review all `backend/app/risk/scoring/*.py` docstrings for consistency with the repo's per-file rationale-comment convention

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational only — independent of User Story 1 (different files, no shared runtime state)
- **User Story 3 (Phase 5)**: Depends on Foundational only for its own code (`priority.py` takes plain floats), but its *tests* (T015-T017) and its *router* (T013) are far more meaningful once US1/US2 exist to supply real `SeverityResult`/`BusinessImpactResult` values, so it is sequenced last
- **Polish (Phase 6)**: Depends on all three user stories

### Parallel Opportunities

- T003 alongside T001/T002
- T005, T006, T007 in parallel once T004 lands
- T008 (US1) and T010 (US2) in parallel once Foundational is done — different files, no shared state
- T009 alongside T008 completion; T011 alongside T010 completion
- T015, T016, T017 in parallel once T012-T014 land
- T019 alongside T018

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2 (setup + foundational)
2. Phase 3 (US1 — Severity) and Phase 4 (US2 — Business Impact) can proceed in parallel — both are P1 and structurally independent
3. Phase 5 (US3 — Priority + endpoint) — **this is the feature's MVP-completing phase**: with all three in place, Phase 12 has everything it needs
4. Phase 6 (Polish)

### Incremental Delivery

Setup + Foundational → US1 + US2 in parallel (each independently testable alone) → US3 (composes them into Priority, ships the endpoint) → Polish.
