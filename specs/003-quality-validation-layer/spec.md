# Feature Specification: Quality Validation Layer

**Feature Branch**: `003-quality-validation-layer`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 3 — Great Expectations quality layer (MVP_CONTEXT.md Section 5): define expectation suites per column category (completeness, uniqueness on CLM_ID, validity of amounts >= 0, dtype checks, range checks, valid code-set checks, date validity, freshness). Compute the 0-100 composite quality score using the MissingRate/DuplicateRate formulas and PASS/WARNING/CRITICAL bands from Section 3.1."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute a real, deterministic 0-100 quality score (Priority: P1)

As a reviewer of the pipeline's output, I need a single 0-100 quality score for a cleaned batch of claims, computed deterministically from real expectation-check results (never a static or assumed number), so I can immediately gauge how trustworthy this batch's data is before anything downstream (baseline, anomaly detection, risk scoring) consumes it.

**Why this priority**: The quality score is the floor every other signal (Anomaly, Risk, Severity) builds on top of (constitution Principle III: "Deterministic validation is the floor every claim must clear"). Nothing else in the pipeline is trustworthy if this isn't real.

**Independent Test**: Can be tested by running the quality layer against Phase 2's cleaned output and confirming the reported score is reproducible from the underlying MissingRate/DuplicateRate/check-pass-rate numbers using the documented formula — not a hardcoded or approximate figure.

**Acceptance Scenarios**:

1. **Given** a cleaned batch with a computed MissingRate under 2% and DuplicateRate at 0%, **When** the quality layer runs, **Then** those specific checks are marked PASS per the bands in MVP_CONTEXT.md Section 3.1, and the composite score reflects that.
2. **Given** the full set of expectation results (PASS/WARNING/CRITICAL per check), **When** the composite score is computed, **Then** it equals the documented weighted-proportion formula applied to those exact results — recomputing it from the same inputs by hand yields the same score.
3. **Given** the quality layer is run twice on the same unmodified cleaned batch, **When** scores are compared, **Then** they are identical (deterministic, no randomness or hidden state).

---

### User Story 2 - Run category-appropriate expectation suites (Priority: P1)

As the implementer, I need a distinct expectation suite per column category (identifiers, dates, amounts, categorical/codes, diagnosis/procedure codes) so each column is checked against rules appropriate to what it actually represents, rather than one generic rule set applied everywhere.

**Why this priority**: A single generic rule set would either be too weak (missing category-specific problems like negative amounts) or too strict (flagging legitimate sparse diagnosis/procedure columns as failures) — this is foundational to the score in Story 1 being meaningful, so it's equally P1.

**Independent Test**: Can be tested by confirming that `CLM_ID` has a uniqueness expectation, every `amount`-category column has a "value ≥ 0" expectation, every `date`-category column has a date-validity expectation, and no expectation type is applied to a category it doesn't make sense for (e.g., no uniqueness expectation is silently applied to a naturally-repeating categorical code column).

**Acceptance Scenarios**:

1. **Given** the `identifier` category, **When** suites are defined, **Then** `CLM_ID` carries a uniqueness-at-claim-grain expectation and `BENE_ID`/`PRVDR_NUM`/NPI columns carry completeness/format expectations appropriate to identifiers.
2. **Given** the `amount` category, **When** suites are defined, **Then** every amount column (`CLM_PMT_AMT`, `CLM_TOT_CHRG_AMT`, etc.) carries a "value ≥ 0" validity expectation and a dtype (numeric) expectation.
3. **Given** the `date` category, **When** suites are defined, **Then** every date column carries an expectation that the value is a valid, standardized (ISO) date within the plausible range established in Phase 2.
4. **Given** the `categorical_code`/`diagnosis_procedure_code` categories, **When** suites are defined, **Then** columns carry a valid-code-set expectation (per Phase 2's observed-set definition) and a completeness expectation calibrated to that column's known-legitimate missingness (e.g., `ADMTG_DGNS_CD`'s 72.2% missingness is not itself treated as a failure, since it's a documented, expected characteristic of this data).

---

### User Story 3 - Persist per-check results for downstream consumption (Priority: P2)

As the implementer of Phase 4 (baseline) and Phase 8 (risk dataset), I need every individual expectation check's result (not just the final composite score) persisted in a queryable form, so later phases can reference specific failure rates (e.g., "GX failure count" feeding the risk dataset) rather than re-running Great Expectations themselves.

**Why this priority**: This unlocks Phases 4 and 8 but isn't needed for Story 1's headline score to work standalone, so it ranks P2.

**Independent Test**: Can be tested by running the quality layer once and confirming each individual check (completeness, uniqueness, validity, dtype, range, code-set, date validity, freshness) appears as its own persisted record with a PASS/WARNING/CRITICAL result, separately from the aggregate score.

**Acceptance Scenarios**:

1. **Given** a completed quality run, **When** results are queried, **Then** each individual expectation's result (check name, column, band, and the underlying computed rate/count) is available as a distinct record.
2. **Given** a later phase needs "GX failure count" for a window, **When** it queries this feature's persisted results, **Then** it can count CRITICAL (and, if configured, WARNING) results for that window without re-running any expectation.

### Edge Cases

- What happens when a column category has zero expectations that make sense for it (hypothetically)? The suite generator MUST NOT silently produce an empty suite without recording that explicitly — every category must have at least a completeness/dtype expectation.
- How does the layer handle a column with legitimately high, expected missingness (e.g., `ADMTG_DGNS_CD` at 72.2%, or the fully-null columns from MVP_CONTEXT.md 2.2)? Completeness expectations MUST be calibrated per-column (or per documented exception list) rather than applying one universal missingness threshold that would flag known-sparse columns as failing every run.
- What happens when Phase 2's cleaned input is missing entirely (quality layer run before cleaning)? The layer MUST fail fast with a clear error rather than running against stale or absent data.
- What happens when a new expectation result would push the composite score negative or above 100 due to a weighting misconfiguration? The score MUST be clamped/validated to the 0-100 range and a configuration error surfaced if the weights don't sum sensibly.
- What happens on the real `inpatient.csv`, where several columns are 100% missing by design (e.g., `OT_PHYSN_UPIN`)? These columns MUST be excluded from (or explicitly exempted within) the completeness suite rather than dragging the composite score toward CRITICAL for a known, structural characteristic of the source data — the exemption itself must be documented, not silent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define an expectation suite per column category (identifier, date, amount, utilization/duration, categorical/code, diagnosis/procedure code), built from Phase 1's categorization output.
- **FR-002**: System MUST include a uniqueness expectation on `CLM_ID` at the claim grain (each claim's identifier appears consistently across its line items, and the set of distinct `CLM_ID` values matches Phase 1's measured unique-claim count for the input batch).
- **FR-003**: System MUST include a "value ≥ 0" validity expectation for every `amount`-category column.
- **FR-004**: System MUST include dtype-conformance expectations matching Phase 2's category-implied dtypes (numeric for amounts/utilization, valid ISO date for dates, string for identifiers/codes).
- **FR-005**: System MUST include range expectations for date columns (values fall within the plausible range established in Phase 2) and for utilization/duration columns (non-negative, within an observed-data-derived upper bound).
- **FR-006**: System MUST include valid-code-set expectations for categorical/code and diagnosis/procedure-code columns, using Phase 2's observed-value-set definition.
- **FR-007**: System MUST include completeness (missingness) expectations calibrated per column — columns with documented, structurally-expected high missingness (e.g., the fully-null columns and `ADMTG_DGNS_CD` identified in MVP_CONTEXT.md Section 2.2) MUST be evaluated against a threshold appropriate to their known baseline, not a single universal threshold that would misclassify them as failing every run.
- **FR-008**: System MUST include a freshness expectation on batch-level recency (e.g., that a batch's data falls within the expected ingestion window), scoped to what Phase 15's continuous-ingestion batching actually provides — not fabricated from a field that doesn't represent true processing freshness (see MVP_CONTEXT.md Section 2.4 on `NCH_WKLY_PROC_DT` not being a real operational timestamp).
- **FR-009**: System MUST compute MissingRate and DuplicateRate using the exact formulas in MVP_CONTEXT.md Section 3.1 and classify each into PASS/WARNING/CRITICAL using the documented bands (MissingRate: <2% PASS, 2-5% WARNING, >5% CRITICAL; DuplicateRate: 0% PASS, 0-1% WARNING, >1% CRITICAL).
- **FR-010**: System MUST compute a single composite Quality Score (0-100) as a configurable weighted proportion of PASS/WARNING/CRITICAL results across all expectation checks, per MVP_CONTEXT.md Section 3.1 — the score MUST be recomputable from the persisted individual check results, never asserted independently of them.
- **FR-011**: System MUST persist every individual expectation check's result (check identity, column, band, underlying computed rate/count) as its own queryable record, separate from the composite score.
- **FR-012**: System MUST fail fast with a clear error if run against input that hasn't passed Phase 2 cleaning (or is otherwise absent).
- **FR-013**: System MUST NOT hardcode the composite score, any individual check's pass/fail outcome, or any underlying rate — every value is computed from the current batch's actual cleaned data (constitution Principle II).

### Key Entities

- **ExpectationSuite**: A named, category-scoped collection of expectations (completeness, uniqueness, validity, dtype, range, code-set, date-validity, freshness) applied to one column category.
- **ExpectationCheckResult**: One persisted outcome — check name/type, column, computed rate or count, PASS/WARNING/CRITICAL band, timestamp.
- **QualityScoreResult**: The composite 0-100 score for a batch, the weights used to compute it, and a reference to the full set of contributing `ExpectationCheckResult` entries it was derived from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The composite Quality Score for any batch is exactly reproducible by re-applying the documented formula to that batch's persisted `ExpectationCheckResult` set — 100% match, zero drift.
- **SC-002**: 100% of the six column categories have at least one category-appropriate expectation suite defined and executed.
- **SC-003**: On the real cleaned `inpatient.csv` batch, known-structural high-missingness columns (fully-null columns, `ADMTG_DGNS_CD`) do not, by themselves, drive the composite score into CRITICAL territory purely from being flagged against a mismatched universal threshold — their completeness checks reflect the calibrated, documented expectation instead.
- **SC-004**: Running the quality layer twice on the same unmodified cleaned batch produces an identical composite score and an identical set of individual check results both times.
- **SC-005**: Every `ExpectationCheckResult` persisted is independently queryable and traceable to the specific column/category and formula that produced it, with zero orphaned or unexplained results contributing to the composite score.

## Assumptions

- Great Expectations (the library referenced by this phase's name in MVP_CONTEXT.md) is the implementation vehicle assumed for expectation suites and checks; this spec describes required behavior, not the library's API, so the plan phase is free to confirm/adjust the concrete integration.
- Default composite-score weights are equal-weighted across check categories unless/until Phase 8+ incident data suggests recalibration — exact default weight values are a tuning/implementation detail, not fixed by this spec (MVP_CONTEXT.md Section 3.1 states weights are "configurable").
- The freshness expectation (FR-008) is scoped narrowly (batch arrived within an expected/configured window) precisely because MVP_CONTEXT.md Section 2.4 rules out treating `NCH_WKLY_PROC_DT` as a genuine operational-timestamp signal — freshness here means ingestion recency, not claims-processing turnaround.
- This feature does not itself create baseline statistics (Phase 4) or incidents (Phase 8/12) — it produces the quality signal those phases consume.
