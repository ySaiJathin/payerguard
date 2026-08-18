# Feature Specification: Testing Suite

**Feature Branch**: `016-testing-suite`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 16 — Testing (MVP_CONTEXT.md Section 5): broken out explicitly per category — Data (missing values, duplicates, invalid types/values/dates, missing columns, empty files); Anomaly (injected-anomaly detection accuracy, false positives, false negatives, detection latency, model stability); Risk (data-leakage test, temporal-split-correctness test, false negatives, model calibration, drift sensitivity); LLM (hallucination, unsupported claims, insufficient-evidence handling, incorrect-recommendation detection); HITL (accept -> fix -> revalidate; reject -> feedback -> recalculate -> re-review); Ingestion (large files, malformed batches, repeated/continuous uploads)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Close specific test-coverage gaps not already guaranteed by Phases 1-15's own specs (Priority: P1)

As the person responsible for this project's overall test coverage, I need the specific test scenarios MVP_CONTEXT.md names in Phase 16 — but which Phases 1-15's individual specs didn't already require — implemented and passing, so the six named categories (Data, Anomaly, Risk, LLM, HITL, Ingestion) are comprehensively covered, not just incidentally covered by whatever each phase happened to test for its own success criteria.

**Why this priority**: Per constitution "Development Workflow," tests belonging to a phase are written alongside that phase's implementation, not deferred to the end — so this feature's job is specifically to identify and fill the remaining named gaps (e.g., "model stability," "drift sensitivity," full HITL round-trip flows spanning multiple modules), not to duplicate what Phases 1-15 already specified.

**Independent Test**: Can be tested by cross-referencing MVP_CONTEXT.md Phase 16's named scenarios against every prior phase's spec.md Success Criteria, confirming each named scenario is either already covered (with a citation to which phase's SC it maps to) or newly implemented by this feature.

**Acceptance Scenarios**:

1. **Given** MVP_CONTEXT.md Phase 16's full list of named test scenarios, **When** a coverage audit is performed, **Then** every scenario is mapped to either an existing Phase 1-15 success criterion or a new test this feature adds — none are left unaccounted for.
2. **Given** the Anomaly category's "model stability" scenario (not explicitly required by Phase 7's own spec), **When** this feature runs, **Then** a new test verifies the selected production anomaly model produces consistent results across repeated runs on the same data (extending Phase 7's existing determinism guarantees to an explicit stability check across multiple independent fit/score cycles).
3. **Given** the Risk category's "drift sensitivity" scenario (not explicitly required by Phase 9's own spec), **When** this feature runs, **Then** a new test verifies the production risk model's scores shift measurably when evaluated against a deliberately drifted fixture (e.g., shifted amount distribution), confirming the model is sensitive to real distributional change rather than insensitive/frozen.

---

### User Story 2 - Provide full cross-module round-trip integration tests (Priority: P1)

As the person responsible for confidence in the end-to-end system, I need integration tests that exercise complete HITL and ingestion round-trips spanning multiple modules (accept → remediate → revalidate; reject → feedback → recalculate → re-review; large-file/malformed-batch/repeated-upload ingestion), so the individual per-module unit tests from Phases 12-15 are proven to compose correctly together, not just correct in isolation.

**Why this priority**: Equal priority — individual module correctness (already covered by Phases 12-15) doesn't guarantee the modules integrate correctly; this is exactly the kind of cross-cutting scenario a dedicated integration-testing phase exists to catch.

**Independent Test**: Can be tested by running the full accept→remediate→revalidate integration test against a fixture incident and confirming it passes end-to-end through the real Phase 12→13→14 module boundaries (not mocked at the module boundary).

**Acceptance Scenarios**:

1. **Given** a fixture incident with a remediable condition, **When** the accept→remediate→revalidate integration test runs, **Then** it exercises the real Phase 12 accept endpoint, the real Phase 13 remediation execution, and the real Phase 14 revalidation, asserting the incident reaches "Resolved" through genuine cross-module calls.
2. **Given** a fixture incident, **When** the reject→feedback→recalculate→re-review integration test runs, **Then** it exercises the real Phase 12 reject/feedback/recalculate endpoints in sequence, confirming a reviewer can re-review the recalculated investigation.
3. **Given** the ingestion category, **When** the large-file/malformed-batch/repeated-upload integration tests run, **Then** each exercises the real Phase 15 ingestion pipeline end-to-end (not a mocked pipeline), consistent with Phase 15's own SC-001 reuse guarantee.

---

### User Story 3 - Consolidate the Data category's cross-phase checks into one explicit test suite (Priority: P2)

As the person responsible for data-quality confidence, I need the Data category's scenarios (missing values, duplicates, invalid types/values/dates, missing columns, empty files) — already individually covered across Phase 1/2/3's specs — consolidated into one explicitly-named, easy-to-run test suite, so "run the data-quality tests" is a single, discoverable command rather than scattered across three phases' test directories.

**Why this priority**: This is an organizational/discoverability improvement over already-existing coverage (Phases 1-3 already require these behaviors), so it's lower priority than Stories 1-2's genuinely new coverage.

**Independent Test**: Can be tested by running the consolidated Data-category test suite and confirming it executes (by reference, not duplication) the relevant Phase 1/2/3 tests already passing.

**Acceptance Scenarios**:

1. **Given** the consolidated Data-category suite, **When** run, **Then** it includes (by reference/import, not copy-paste duplication) Phase 1's schema-validation tests, Phase 2's missing-value/duplicate/invalid-value/date-standardization tests, and Phase 3's completeness/uniqueness/validity expectation tests.
2. **Given** a regression in any referenced Phase 1/2/3 test, **When** the consolidated suite runs, **Then** the failure is visible at the consolidated-suite level too — this feature doesn't hide or swallow failures from the tests it references.

### Edge Cases

- What happens if a named MVP_CONTEXT.md Phase 16 scenario turns out to already be fully covered by an earlier phase's spec (e.g., LLM's "insufficient-evidence handling" is already Phase 11's own SC-002)? This feature MUST document that mapping explicitly (per Story 1) rather than re-implementing a redundant duplicate test.
- What happens if a named scenario can't be meaningfully tested at the current data scale (e.g., "drift sensitivity" with only a handful of historical windows)? This MUST be reported honestly as a data-scale limitation (consistent with Phase 9's own Assumptions) with the test still implemented and passing on a constructed fixture, rather than skipped silently.
- What happens when this feature's integration tests reveal an actual cross-module bug (not a test-authoring gap)? This feature's own scope is to surface such a bug via a failing test — fixing the underlying bug belongs to whichever phase's module owns the defect, not to this feature.
- What happens to the "repeated/continuous uploads" ingestion scenario given Phase 15 already covers duplicate detection? This feature's test specifically verifies the *repeated, non-duplicate* case (multiple distinct batches uploaded in sequence over time) composes correctly, distinct from Phase 15's single-duplicate-detection unit test.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST produce a documented coverage map from every MVP_CONTEXT.md Phase 16 named scenario to either an existing Phase 1-15 success criterion (by citation) or a new test this feature adds.
- **FR-002**: System MUST implement a new "model stability" test for the Anomaly category, verifying the selected production anomaly model produces consistent results across repeated independent fit/score cycles on unchanged data.
- **FR-003**: System MUST implement a new "drift sensitivity" test for the Risk category, verifying the selected production risk model's scores shift measurably in response to a deliberately drifted fixture.
- **FR-004**: System MUST implement full integration tests for both HITL round-trips: accept → remediate → revalidate, and reject → feedback → recalculate → re-review, each exercising real (not mocked) cross-module calls through Phases 12-14.
- **FR-005**: System MUST implement integration tests for the Ingestion category's large-file, malformed-batch, and repeated/continuous (multi-batch, non-duplicate) upload scenarios, exercising the real Phase 15 pipeline end-to-end.
- **FR-006**: System MUST consolidate the Data category's already-existing Phase 1/2/3 test coverage into one discoverable, explicitly-named test suite, referencing (not duplicating) the underlying tests.
- **FR-007**: System MUST implement the LLM category's hallucination, unsupported-claims, and incorrect-recommendation-detection scenarios not already covered by Phase 11's own spec (Phase 11 already covers insufficient-evidence handling explicitly) — these MUST use fixture-based checks against known evidence (e.g., asserting the LLM's cited evidence references actually exist in the structured payload) since true hallucination detection can't be perfectly automated, and this limitation MUST be documented, not hidden.
- **FR-008**: System MUST report honestly when a named scenario's test is constrained by current data scale (e.g., limited historical windows for drift/stability testing), rather than silently skipping or overstating confidence.
- **FR-009**: System MUST NOT duplicate test logic already correctly covering a named scenario in an earlier phase — new tests are added only where a genuine coverage gap exists, per the FR-001 coverage map.

### Key Entities

- **CoverageMapEntry**: One MVP_CONTEXT.md Phase 16 named scenario, its category, and either a citation to the covering Phase 1-15 success criterion or a reference to the new test this feature adds.
- **IntegrationTestScenario**: One cross-module round-trip test (HITL or Ingestion category) — the real modules/endpoints it exercises, and its pass/fail outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of MVP_CONTEXT.md Phase 16's named scenarios appear in the `CoverageMapEntry` list with a valid citation or new-test reference — zero unaccounted-for scenarios.
- **SC-002**: The new model-stability (Anomaly) and drift-sensitivity (Risk) tests both exist, run, and pass (or honestly report a data-scale limitation per FR-008) — verified directly by executing them.
- **SC-003**: Both HITL integration tests (accept→remediate→revalidate; reject→feedback→recalculate→re-review) pass end-to-end against real module boundaries, not mocks.
- **SC-004**: All three Ingestion integration scenarios (large file, malformed batch, repeated/continuous uploads) pass against the real Phase 15 pipeline.
- **SC-005**: The consolidated Data-category suite runs Phase 1/2/3's existing tests by reference and reports zero duplicated test logic (verified by a code-audit check).
- **SC-006**: Zero test in this feature silently skips a named scenario without an explicit, documented reason (FR-008/FR-009 enforcement).

## Assumptions

- "Hallucination detection" (LLM category) is scoped, per FR-007, to fixture-based evidence-grounding checks (does the LLM's cited evidence trace back to real structured-payload content) rather than a general-purpose hallucination classifier, since no such general classifier is in scope for this MVP — this limitation is documented explicitly in the coverage map, not silently understated.
- This feature does not introduce new production functionality — it is purely a testing/coverage feature, consuming and exercising Phases 1-15's already-specified capabilities.
- The coverage map (FR-001) is maintained as a living artifact; as later phases (17+) or future iterations add capabilities, extending the map is expected but not itself required by this specific feature's completion criteria.
