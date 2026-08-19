---

description: "Task list template for feature implementation"
---

# Tasks: Testing Suite

**Input**: Design documents from `/specs/015-testing-suite/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md (not applicable — no new backend module), quickstart.md

**Tests**: This feature *is* tests — every task below either adds a test or the coverage-map artifact that proves test completeness. There is no separate "tests vs implementation" split.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Backend tests: `backend/tests/`
- Documentation artifact: `docs/testing/phase15_coverage_map.md`
- No `backend/app/` changes — this feature adds zero production code (plan.md's Structure Decision, spec.md's Assumptions)

## Pre-Implementation Finding: the Ingestion category's underlying pipeline was descoped

Before task generation, a real conflict was found and resolved with the user (not assumed): FR-005/User Story 2's acceptance scenario 3 and plan.md's original file list call for integration tests against "the real ingestion pipeline" (large file / malformed batch / repeated-upload scenarios). But `015-continuous-ingestion` — the feature that would have built that pipeline (watched-folder pattern, repeated batches through the historical-baseline windowing logic) — was deleted in commit `6dd9ad2` ("live pipeline out of scope") before this feature was renumbered into its old `015` slot; `backend/app/ingestion/` remains the untouched Phase-0 placeholder (no router, no service, no watcher logic), and no benchmark/model artifacts of any kind exist on disk in this environment. There is nothing real to integration-test.

**Resolution (user-confirmed)**: the three Ingestion scenarios are recorded in the coverage map as `limitation_documented` — citing the descoping decision — rather than building integration tests against a pipeline that doesn't exist (which would require either fabricating production code this feature explicitly must not add, or mocking the very module boundary these tests are supposed to prove is real). This is consistent with FR-008/FR-009's honest-reporting mandate and the Edge Cases section's own principle: a scenario that can't be meaningfully tested must be reported honestly, not silently skipped or faked. **This is a deliberate, documented deviation from plan.md's originally sketched file list** (which predates this discovery) — no `backend/tests/integration/test_ingestion_*.py` files are created by this task list.

## Pre-Implementation Finding: one of the two required HITL round-trips already exists

Cross-referencing FR-004's second round-trip ("reject → feedback → recalculate → re-review") against Phase 12's own test suite found it is **already fully exercised**, end-to-end, over real HTTP, by `backend/tests/hitl/test_router_hitl_flow.py::test_full_create_reject_recalculate_accept_flow` (create → reject-with-feedback → recalculate → accept, i.e. re-review). Per FR-009 ("must not duplicate test logic already correctly covering a named scenario"), this feature does **not** add a second `backend/tests/integration/test_hitl_reject_feedback_recalculate.py` — Phase 12's existing test is cited in the coverage map instead. Only the genuinely missing round-trip — **accept → remediate → revalidate**, which no existing test chains across all three of Phases 12/13/14 — gets a new integration test.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Clear the two mismatched Phase-0 placeholder stubs this feature supersedes, and scaffold the new test packages plan.md's structure requires.

- [X] T001 [P] Delete `backend/tests/data/test_placeholder.py` and the now-empty `backend/tests/data/` directory — plan.md's structure places the consolidated Data-category suite at `backend/tests/data_suite/test_data_category_suite.py` instead, mirroring the mismatched-Phase-0-stub cleanup precedent set by 014's T001.
- [X] T002 [P] Rewrite `backend/tests/ingestion/test_placeholder.py`'s docstring: remove "STATUS: not implemented yet," replace with a permanent record that `015-continuous-ingestion` was removed as out-of-scope (commit `6dd9ad2`), `app/ingestion/` remains an unimplemented Phase-0 placeholder, and the Ingestion category's three Phase 15 scenarios are recorded as `limitation_documented` in `docs/testing/phase15_coverage_map.md` (FR-008/FR-009) rather than tested against a nonexistent pipeline — cite that file path so a reader lands on the authoritative explanation. Leave the file test-free (no fabricated/mocked-pipeline test), consistent with the Pre-Implementation Finding above.
- [X] T003 [P] Create `backend/tests/coverage_map/__init__.py` (empty — mirrors existing `backend/tests/<module>/__init__.py` convention).
- [X] T004 [P] Create `backend/tests/integration/__init__.py` (empty).
- [X] T005 [P] Create `backend/tests/data_suite/__init__.py` (empty).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The coverage-map artifact and its completeness check — every user story's new test needs to land a row in this same document, so its skeleton (with the 16 already-covered scenarios' citations filled in immediately) must exist before any story-specific work starts.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 Create `docs/testing/phase15_coverage_map.md` with a `Category | Scenario | Status | Reference` Markdown table containing all 24 MVP_CONTEXT.md Phase 15 named scenarios (5 Data + 5 Anomaly + 5 Risk + 4 LLM + 2 HITL + 3 Ingestion), per data-model.md's `CoverageMapEntry` shape. Populate the 16 rows already verifiably covered by prior phases immediately, with real citations (verified during this task, not invented):
  - **Data** (5): missing values → Phase 2 SC-005 / `backend/tests/data_engineering/test_cleaning_service.py`; duplicates → Phase 1 SC-003 / `test_duplicate_detection.py`; invalid types/values/dates → Phase 2 `test_invalid_value_detection.py` + `test_date_standardization.py`; missing columns → `test_profiling_service.py`/`test_categorization.py` (confirm exact covering test during this task); empty files → `test_profiling_service.py`/`test_cleaning_service.py`'s empty-input handling (confirm exact covering test during this task).
  - **Anomaly** (3 of 5): injected-anomaly detection accuracy → Phase 7 SC-002/SC-003 / `backend/tests/anomaly/test_injection_harness.py` + `test_benchmark_metrics.py`; false positives → Phase 7 `BenchmarkResult.false_positive_rate` field / `test_benchmark_metrics.py`; false negatives → same file's recall/confusion-matrix coverage. (Detection latency and model stability are the two remaining Anomaly rows — detection latency is also already covered by `MeasurementContext`/`BenchmarkResult.execution_time_seconds` in the same files; model stability is genuinely new — leave both of the not-yet-covered rows, if any, as `status: new_test_added` with `reference` = the not-yet-existing file path, to be finalized by T011.)
  - **Risk** (3 of 5): data-leakage test → Phase 9 SC-001 / `backend/tests/risk/benchmark/test_leakage_isolation.py`; temporal-split-correctness test → Phase 9 SC-006 / `test_split_consistency.py`; model calibration → Phase 9 SC-005 / `test_calibration_reported.py`. (False negatives is also already covered — via the recall component of Phase 9's ranking rule, SC-003, in `test_model_selection.py` — leave drift sensitivity as `status: new_test_added` with a placeholder reference, finalized by T011.)
  - **LLM** (1 of 4): insufficient-evidence handling → Phase 11 SC-002 / `backend/tests/llm/test_insufficient_evidence.py`. Leave hallucination, unsupported claims, and incorrect-recommendation detection as `status: new_test_added` with a placeholder reference (finalized by T011) — per spec Assumptions, document explicitly that "hallucination detection" here means fixture-based evidence-grounding checks, not a general-purpose classifier.
  - **HITL** (1 of 2): reject → feedback → recalculate → re-review → `status: covered_by_prior_phase`, reference `backend/tests/hitl/test_router_hitl_flow.py::test_full_create_reject_recalculate_accept_flow` (Phase 12), per the Pre-Implementation Finding above. Leave accept → fix → revalidate as `status: new_test_added` with a placeholder reference (finalized by T014).
  - **Ingestion** (3 of 3): all three (large files, malformed batches, repeated/continuous uploads) → `status: limitation_documented`, reference explaining the `015-continuous-ingestion` descoping (commit `6dd9ad2`) per the Pre-Implementation Finding above — these rows are already final, no later task revisits them.
- [X] T007 Create `backend/tests/coverage_map/test_coverage_map_completeness.py`: hardcode the same 24-scenario expected list (`category`, `scenario`) sourced directly from MVP_CONTEXT.md Phase 15's description (per research.md's documented decision — a checked-in list, not a dynamic spec-file scan); parse `docs/testing/phase15_coverage_map.md`'s table and assert (a) every hardcoded scenario appears in the parsed table exactly once (SC-001 — zero unaccounted-for scenarios), (b) every row has a non-empty `Reference`, and (c) every row with `status: limitation_documented` has a `Reference` that reads as an actual explanation, not a placeholder (FR-008). This test will fail on the placeholder `new_test_added` rows until T011/T014/T016 fill in real references — that's intentional; it's the mechanism that keeps this feature honest about what's actually done. Depends on T006.

**Checkpoint**: Coverage map skeleton and its completeness check exist — user story implementation can now begin, each filling in its own remaining placeholder rows.

---

## Phase 3: User Story 1 - Close specific test-coverage gaps not already guaranteed by Phases 1-14's own specs (Priority: P1) 🎯 MVP

**Goal**: Implement the three genuinely new tests this feature's own gap analysis found (Anomaly model stability, Risk drift sensitivity, LLM evidence-grounding/hallucination/unsupported-claims/incorrect-recommendation-detection) — none of which duplicate existing Phase 1-14 coverage.

**Independent Test**: Run `pytest backend/tests/anomaly/test_model_stability.py backend/tests/risk/test_drift_sensitivity.py backend/tests/llm/test_evidence_grounding.py backend/tests/coverage_map/test_coverage_map_completeness.py -v` and confirm all pass, with the coverage map showing zero remaining placeholder rows for these three scenarios.

### Implementation for User Story 1

- [X] T008 [P] [US1] Create `backend/tests/anomaly/test_model_stability.py` (FR-002, SC-002): reuse `backend/tests/anomaly/test_leakage_isolation.py`'s `_matrix()`/`compute_temporal_split` fixture pattern (a small synthetic ~300-day feature matrix — no real persisted benchmark artifacts exist in this environment, confirmed absent from `data/`) to build a train/test split; determine the model type to test the same way `app.anomaly.benchmark._DETECTOR_FACTORIES` maps `ModelType` to a detector class (default to `ModelType.hbos` if no real `read_benchmark_run_result()` selection is available, documenting that choice); fit+score the corresponding detector (`HBOSDetector`/`IQRDetector`/`IsolationForestDetector`/`LOFDetector`, all with fixed `random_state` where applicable — confirmed no unseeded randomness in any of the four) 5 independent times against the *same unchanged* train/test data; assert the resulting test-set anomaly scores vary by less than a documented tolerance (e.g., relative std dev < 5%) across the 5 cycles. Document per FR-008: if the selected model type has inherent randomness requiring a wider tolerance than a fully deterministic model, state that explicitly in the test's docstring rather than silently loosening the assertion.
- [X] T009 [P] [US1] Create `backend/tests/risk/test_drift_sensitivity.py` (FR-003, SC-002): reuse `backend/tests/risk/benchmark/_fixtures.py`'s `make_rows()`/`make_split()` pattern to build a small separable risk-dataset fixture; fit a production-representative model (e.g., `app.risk.benchmark.logistic` or `xgboost_model`, matching whichever `_fixtures.py` pattern other risk-benchmark tests already use) on the undrifted rows; construct a deliberately drifted copy of the test window with `anomaly_frequency`/`volume_deviation` shifted well outside the fixture's historical range (reusing the "distribution shift" concept from Phase 7's injection harness, per research.md); score both the drifted and undrifted windows with the same fitted model; assert the resulting risk scores differ by more than a documented minimum delta, confirming the model is measurably sensitive to genuine distributional change rather than frozen/insensitive. Document any current-data-scale limitation per FR-008 if the fixture's small window count constrains how confidently "measurable" can be defined.
- [X] T010 [US1] Create `backend/tests/llm/test_evidence_grounding.py` (FR-007): reuse `backend/tests/llm/_fixtures.py`'s `make_payload()` (which seeds `affected_claims_sample=[{"claim_id": "C1", "amount": 1200.5}]`) and construct `InvestigationDraft` fixtures directly (not `make_draft()`, which doesn't expose `evidence`/`recommended_fix` overrides) covering three cases: (1) a grounded case whose `evidence` cites `"C1"` and `1200.5` — asserts every cited claim ID/numeric value traces back to `StructuredIncidentPayload.affected_claims_sample` within reasonable rounding tolerance; (2) an ungrounded/hallucinated case whose `evidence` cites a claim ID (e.g. `"C99"`) or dollar figure absent from the payload — asserts the grounding check flags it (per research.md, "flag, not fail outright" — the assertion is on the flag being raised, not on `investigate()` itself raising); (3) an ungrounded case in `recommended_fix`/`prevention_recommendation` citing an unsupported claim ID — applying the same citation-tracing mechanism to those fields, covering FR-007's "incorrect-recommendation detection (distinct from hallucination)" scenario. Document in the module docstring, per spec Assumptions, that this is a best-effort citation-tracing proxy, not a general-purpose hallucination classifier.
- [X] T011 [US1] Update `docs/testing/phase15_coverage_map.md`'s remaining Anomaly/Risk/LLM placeholder rows (model stability, drift sensitivity, hallucination, unsupported claims, incorrect-recommendation detection — and detection-latency/false-negatives rows if T006 left any as placeholders) from `new_test_added` placeholders to their final references pointing at T008/T009/T010's actual file paths; re-run `pytest backend/tests/coverage_map/test_coverage_map_completeness.py` to confirm it now passes for these rows. Depends on T008, T009, T010.

**Checkpoint**: At this point, every genuinely new gap-filling test this feature identified is implemented, passing, and reflected in the coverage map — independently deliverable as the MVP.

---

## Phase 4: User Story 2 - Provide full cross-module round-trip integration tests (Priority: P1)

**Goal**: Prove the one HITL round-trip no existing test chains across all three modules — accept (Phase 12) → remediate (Phase 13) → revalidate (Phase 14) — actually composes correctly over real HTTP, real module boundaries, no mocks.

**Independent Test**: Run `pytest backend/tests/integration/test_hitl_accept_remediate_revalidate.py -v` and confirm it passes end-to-end through the real Phase 12/13/14 router boundaries.

### Implementation for User Story 2

- [X] T012 [US2] Create `backend/tests/integration/test_hitl_accept_remediate_revalidate.py` (FR-004, SC-003): mirror `backend/tests/remediation/test_router_remediation_flow.py`'s `_app_and_client()` pattern but mount `hitl_router` + `remediation_router` + `revalidation_router` together on one `FastAPI()` app sharing one `make_test_session()` db. Seed the incident via `tests.revalidation._fixtures.make_incident(db, status="ready_for_review", ...)` (its fuller `evidence_snapshot` — `affected_claim_pct`/`affected_claims_amounts`/`baseline_amount_percentiles` — is required by `recompute_service.recompute`, unlike `tests.remediation._fixtures.make_incident`'s empty one). Sequence: (1) `POST /hitl/{id}/accept` → assert `200`/`"accepted"`; (2) `POST /remediation/{id}/run` with a real `affected_claims` payload (reuse the 4-claim duplicate/status/impute/unhandled example from `test_router_remediation_flow.py`) → assert `200`, capture the real `run_id` from the response body (confirmed the real engine always sets `completed_at` synchronously before returning, so the run is immediately usable by revalidation); (3) apply `tests.revalidation._fixtures.patch_recompute_dependencies(monkeypatch, ...)` and `POST /revalidation/{id}/run` with `tests.revalidation._fixtures.make_revalidation_request(run_id)`'s body → assert `200` and that `incident_status` in the response is `"resolved"` or `"reopened"` (whichever the fixture's recomputed signals produce — assert on whichever it genuinely is, not a fixed expectation, consistent with 014's own no-forced-outcome precedent). Assert all three real modules were actually invoked (e.g., spy on `app.remediation.remediation_service.run_remediation` and `app.revalidation.revalidation_service.run_revalidation`), not mocked at the module boundary (FR-004's "real (not mocked) cross-module calls" requirement).
- [X] T013 [US2] Run `pytest backend/tests/hitl/test_router_hitl_flow.py::test_full_create_reject_recalculate_accept_flow -v` and confirm it still passes as-is — per the Pre-Implementation Finding above, this existing Phase 12 test already satisfies FR-004's reject → feedback → recalculate → re-review round-trip requirement; no new file is created for it (FR-009 — no duplication).
- [X] T014 [US2] Update `docs/testing/phase15_coverage_map.md`'s two HITL rows: accept → fix → revalidate → `status: new_test_added`, reference `backend/tests/integration/test_hitl_accept_remediate_revalidate.py`; reject → feedback → recalculate → re-review → confirm it's already recorded as `status: covered_by_prior_phase` referencing `backend/tests/hitl/test_router_hitl_flow.py::test_full_create_reject_recalculate_accept_flow` (Phase 12) from T006. Depends on T012, T013.

**Checkpoint**: Both HITL round-trips are now proven end-to-end (one newly, one by citation) — SC-003 satisfied.

---

## Phase 5: User Story 3 - Consolidate the Data category's cross-phase checks into one explicit test suite (Priority: P2)

**Goal**: Make "run the data-quality tests" a single discoverable command, by reference to Phases 1-3's already-passing tests — zero duplicated logic.

**Independent Test**: Run `pytest backend/tests/data_suite/test_data_category_suite.py -v` and confirm it executes (not re-implements) the referenced Phase 1/2/3 tests, and that a regression introduced into any referenced test is visible as a failure at this suite's level too.

### Implementation for User Story 3

- [X] T015 [US3] Create `backend/tests/data_suite/test_data_category_suite.py` (FR-006, SC-005): reference — via `from tests.data_engineering.test_cleaning_service import *` / explicit named imports of the relevant `test_*` functions, or `pytest_plugins`-style collection, whichever keeps pytest actually re-executing the original test functions rather than copy-pasting their bodies — the tests covering: missing values (`test_cleaning_service.py`), duplicates (`test_duplicate_detection.py`), invalid types/values/dates (`test_invalid_value_detection.py`, `test_date_standardization.py`), missing columns and empty files (whichever `test_profiling_service.py`/`test_categorization.py` tests T006 confirmed cover these). Add a short module-level docstring stating explicitly that this file imports, not duplicates, Phase 1/2/3's test logic (FR-009) so a reviewer scanning the file immediately understands why it has few or no test bodies of its own. Confirm via a quick code read that no test body here re-implements assertions already made in the referenced files.
- [X] T016 [US3] Update `docs/testing/phase15_coverage_map.md`'s five Data-category rows' `Reference` column to also point at `backend/tests/data_suite/test_data_category_suite.py` alongside each row's original Phase 1/2/3 citation from T006, satisfying FR-006's "single discoverable command" goal without replacing the original citation. Depends on T015.

**Checkpoint**: All three user stories are now independently functional; the coverage map has zero remaining placeholder rows.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across the whole feature.

- [X] T017 [P] Run `pytest backend/tests/coverage_map/ backend/tests/anomaly/test_model_stability.py backend/tests/risk/test_drift_sensitivity.py backend/tests/llm/test_evidence_grounding.py backend/tests/integration/ backend/tests/data_suite/ -v` and then the full backend suite (`pytest backend/tests/ -q`), fixing any regressions surfaced by cross-file integration between the phases above.
- [X] T018 [P] Manually validate every command in `specs/015-testing-suite/quickstart.md` against this implementation's actual behavior (file paths, expected pass/fail/limitation outcomes); update quickstart.md if any command no longer matches what was actually built (e.g., there is no ingestion-integration-test command to validate — quickstart.md doesn't currently list one, confirm it still doesn't need one).
- [X] T019 Audit every new test file from T008-T016 for `pytest.skip()`/`xfail`/silent `except: pass` patterns; confirm each one either doesn't exist or carries an explicit, documented reason inline (SC-006 — zero silent skips of a named scenario). Cross-check this audit's outcome against `docs/testing/phase15_coverage_map.md`'s `limitation_documented` rows to confirm every such row traces to a real, findable explanation, not just a table entry.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion (T001/T002's cleanup doesn't block T006/T007, but both should land before story work starts to avoid file-path confusion) — BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational (T006/T007) completion. US1/US2/US3 are otherwise independent of each other and can proceed in any order or in parallel.
- **Polish (Phase 6)**: Depends on all three user stories being complete (T011, T014, T016 each need to have landed their final coverage-map references before T017-T019's full-suite/full-audit pass).

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) completes. No dependency on US2/US3.
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) completes. No dependency on US1/US3 (T012's fixtures come from existing `tests.revalidation._fixtures`/`tests.remediation._fixtures`, not from anything US1 adds).
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) completes. No dependency on US1/US2.

### Within Each User Story

- T008/T009 (US1) are parallel — different files, no shared state.
- T010 (US1) is independent of T008/T009 but not marked [P] alongside them only because all three commonly get reviewed as one PR; there's no file conflict.
- T011 depends on T008-T010 (needs their final file paths to cite).
- T012 (US2) has no test-file dependency within its own phase; T013 is a verification-only task (no new file); T014 depends on both.
- T015 (US3) stands alone; T016 depends on it.

### Parallel Opportunities

- All Setup tasks (T001-T005) marked [P] can run in parallel — five independent files.
- T008 and T009 (US1) can run in parallel — different modules (anomaly vs risk), no shared fixtures.
- Once Foundational (T006-T007) completes, all three user stories (Phase 3, 4, 5) can proceed in parallel if staffed, since none of their implementation tasks depend on another story's output — only each story's own final coverage-map-update task (T011/T014/T016) needs that story's own new tests to exist first.
- T017/T018 (Polish) can run in parallel — one is test execution, the other is documentation validation.

---

## Parallel Example: Phase 3 (User Story 1)

```bash
# Launch the two independent new-gap tests together:
Task: "Create backend/tests/anomaly/test_model_stability.py"
Task: "Create backend/tests/risk/test_drift_sensitivity.py"
```

## Parallel Example: Phase 1 (Setup)

```bash
Task: "Delete backend/tests/data/test_placeholder.py"
Task: "Rewrite backend/tests/ingestion/test_placeholder.py's docstring"
Task: "Create backend/tests/coverage_map/__init__.py"
Task: "Create backend/tests/integration/__init__.py"
Task: "Create backend/tests/data_suite/__init__.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — the coverage map skeleton and its completeness test)
3. Complete Phase 3: User Story 1 (model stability, drift sensitivity, evidence grounding)
4. **STOP and VALIDATE**: `pytest backend/tests/coverage_map/ backend/tests/anomaly/test_model_stability.py backend/tests/risk/test_drift_sensitivity.py backend/tests/llm/test_evidence_grounding.py -v` all pass.

### Incremental Delivery

1. Setup + Foundational → coverage map skeleton exists, completeness test running (and failing on the still-placeholder rows — expected).
2. Add User Story 1 → three new gap tests pass, three coverage-map rows finalized → MVP.
3. Add User Story 2 → the one genuinely missing HITL round-trip is proven, the other cited → coverage map fully finalized for HITL.
4. Add User Story 3 → Data category consolidated, coverage map fully finalized for Data.
5. Polish → full-suite regression pass, quickstart validation, silent-skip audit.

### Parallel Team Strategy

With multiple developers, once Foundational is done: Developer A takes US1 (T008-T011), Developer B takes US2 (T012-T014), Developer C takes US3 (T015-T016) — all three land independently in the shared `docs/testing/phase15_coverage_map.md`, so the only real coordination point is avoiding simultaneous edits to that one file's remaining placeholder rows.

---

## Notes

- **[P] tasks** = different files, no dependencies.
- **[Story] label** maps task to specific user story for traceability.
- This feature adds **zero files under `backend/app/`** — every task above touches only `backend/tests/`, `docs/testing/`, or (T002) rewrites an existing test-package docstring.
- The Ingestion category (3 scenarios) and one of the two HITL round-trips are **deliberately not built** as new test files — both are documented, user-confirmed deviations from plan.md's original file sketch, recorded above and in the coverage map itself (not silently dropped).
- Every `new_test_added`/`limitation_documented` coverage-map row must trace to something a reader can actually open and verify — the completeness test (T007) enforces presence and non-empty references, but the *honesty* of each reference is a human-reviewable property this task list keeps visible rather than automating away.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
