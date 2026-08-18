---

description: "Task list for Anomaly Detection Benchmark"
---

# Tasks: Anomaly Detection Benchmark

**Input**: Design documents from `/specs/007-anomaly-detection-benchmark/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md — all present. Depends on Phase 5 (`features` module: `ClaimFeatures`/`WindowFeatures`, deferred `anomaly_count`) and Phase 6 (`features/selection` module: `TemporalSplit`, `SelectedFeatureSet`) already being implemented, which they are.

**Tests**: Included — plan.md's Testing section explicitly names three required test files (leakage isolation, injection harness, enrichment idempotency); a fourth (model selection reproducibility) and a data-loading test are added for the same reason: every Success Criterion needs a machine-checkable assertion, not just a manual quickstart step.

**Organization**: Tasks are grouped by user story. User Story 2 (injection harness) is implemented before User Story 1 (full benchmark) despite spec.md listing US1 first, because spec.md's own "Why this priority" note for US2 states it is "a direct, non-optional prerequisite" for US1's precision/recall/F1 metrics — US1's benchmark.py calls US2's injection_harness.py. Both are P1; this is a within-priority ordering by hard dependency, not a priority change.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (benchmark all 4 detectors, leakage-free), US2 (injection harness), US3 (populate `anomaly_count`)

## Path Conventions

Backend module: `backend/app/anomaly/`. Tests: `backend/tests/anomaly/`. Reuses `backend/app/features/` (Phase 5) and `backend/app/features/selection/` (Phase 6).

---

## Phase 1: Setup

**Purpose**: Align the existing Phase-0 scaffold with plan.md's exact module boundary before any real code goes in.

- [x] T001 Add `models_dir()` to `backend/app/data_engineering/paths.py` (returns `find_data_dir() / "models"`), for `data/models/anomaly/*.pkl` artifact storage per plan.md's Storage section
- [x] T002 [P] Delete the mismatched Phase-0 scaffold stub files in `backend/app/anomaly/` (`hbos_model.py`, `iqr_baseline.py`, `isolation_forest_model.py`, `lof_model.py`, `injection.py`) — plan.md's Project Structure fixes the real filenames as `hbos.py`, `iqr.py`, `isolation_forest.py`, `lof.py`, `injection_harness.py`
- [x] T003 [P] Create `backend/tests/anomaly/__init__.py`

**Checkpoint**: Module skeleton matches plan.md exactly; ready for real implementation.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas and the per-claim feature matrix builder every user story's code depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Define `AnomalyModelCandidate`, `InjectedAnomalyInstance`, `MeasurementContext`, `BenchmarkResult`, `ProductionModelSelection`, `WindowAnomalyEnrichment`, `BenchmarkRunResult`, `EnrichWindowsResult` Pydantic models in `backend/app/anomaly/schemas.py` per data-model.md's field tables
- [x] T005 Implement `backend/app/anomaly/data_loading.py`: `load_benchmark_inputs()` builds one per-claim numeric feature matrix (indexed by `CLM_ID`, `CLM_FROM_DT` retained) by reusing Phase 6's `build_claim_candidate_frame`/`build_window_candidate_frame` (joining each claim to its window's flattened columns) and restricting to `SelectedFeatureSet.features` columns that are numeric; raises `AnomalyInputUnavailableError` (409) when Phase 1/2/5/6 prerequisites are missing
- [x] T006 [P] `backend/tests/anomaly/test_data_loading.py`: asserts the built matrix's columns are exactly the numeric subset of a fixture `SelectedFeatureSet.features`, and that `AnomalyInputUnavailableError` is raised when no `TemporalSplit`/`SelectedFeatureSet` exists

**Checkpoint**: Foundation ready — injection harness and benchmark work can now begin.

---

## Phase 3: User Story 2 - Inject synthetic anomalies into validation/test copies only (Priority: P1)

**Goal**: A harness that injects 5 disjoint, ground-truth-labeled synthetic anomaly types into copies of validation/test data, never touching training data.

**Independent Test**: Confirm training data passed to model fitting is byte-identical to Phase 6's train portion, while validation/test copies contain injected anomalies with ground-truth labels traceable to their injection type.

### Implementation for User Story 2

- [x] T007 [US2] Implement `inject_missing_value_spike` in `backend/app/anomaly/injection_harness.py`: nulls out a random subset of feature values on a random row subset; ground truth = anomaly
- [x] T008 [US2] Implement `inject_amount_spike` in `backend/app/anomaly/injection_harness.py`: multiplies an amount-like numeric feature by a large factor on a random row subset
- [x] T009 [US2] Implement `inject_duplicate_spike` in `backend/app/anomaly/injection_harness.py`: appends near-duplicate rows (new synthetic `CLM_ID`, copied feature values) — the duplicate is the labeled anomaly, the original stays normal
- [x] T010 [US2] Implement `inject_volume_drop` in `backend/app/anomaly/injection_harness.py`: drives a random row's feature values to an extreme outlier of the train distribution (simulating an isolated claim characteristic of an abrupt local volume collapse), documented as a per-row proxy for what is naturally a window-level phenomenon
- [x] T011 [US2] Implement `inject_distribution_shift` in `backend/app/anomaly/injection_harness.py`: shifts several numeric features by several train-standard-deviations in a consistent direction on a random row subset
- [x] T012 [US2] Implement `inject_all(matrix, feature_columns, split_name, rng)` orchestrator in `backend/app/anomaly/injection_harness.py`: applies all 5 injectors to disjoint row subsets of one copy of the given split's matrix, returns `(injected_df, ground_truth_labels, list[InjectedAnomalyInstance])`; only ever called with validation/test matrices, never train (FR-004, FR-005, FR-006, research.md's combined-copy decision)
- [x] T013 [P] [US2] `backend/tests/anomaly/test_injection_harness.py`: all 5 injection types each produce ≥1 `InjectedAnomalyInstance` (SC-002), injected row sets are pairwise disjoint, and a train-portion matrix passed through `inject_all` is rejected/never called (structural check that the harness is only invoked on validation/test copies, FR-005)

**Checkpoint**: Injection harness is independently testable and ready for the benchmark to consume.

---

## Phase 4: User Story 1 - Benchmark all four anomaly detectors under identical, leakage-free conditions (Priority: P1) 🎯 MVP

**Goal**: IQR, HBOS, Isolation Forest, and LOF each fit on train only, calibrated on validation only, evaluated on test exactly once, with an empirical production-model selection.

**Independent Test**: Run the benchmark and confirm all four models were fit using only the train portion, calibrated only on validation, and scored on test exactly once.

### Implementation for User Story 1

- [x] T014 [P] [US1] Implement `backend/app/anomaly/iqr.py`: hand-rolled IQR baseline — `fit` computes per-feature Q1/Q3/1.5×IQR bounds on train, `score` returns a per-row anomaly score (magnitude of out-of-bound distance summed across features), `parameters` returns the fitted bounds
- [x] T015 [P] [US1] Implement `backend/app/anomaly/hbos.py`: wraps `pyod.models.hbos.HBOS`, `fit`/`score`/`parameters` matching `iqr.py`'s interface
- [x] T016 [P] [US1] Implement `backend/app/anomaly/isolation_forest.py`: wraps `sklearn.ensemble.IsolationForest`, `fit`/`score` (`-model.score_samples`, higher = more anomalous)/`parameters`
- [x] T017 [P] [US1] Implement `backend/app/anomaly/lof.py`: wraps `sklearn.neighbors.LocalOutlierFactor` with `novelty=True` (required to score data outside the fit set), `fit`/`score`/`parameters`
- [x] T018 [US1] Implement `backend/app/anomaly/benchmark.py`: `run_benchmark()` — loads inputs via `data_loading.py`, splits the matrix train/validation/test (`assign_split` on `CLM_FROM_DT`), imputes NaNs with train-column medians only, injects anomalies into validation/test copies via `injection_harness.inject_all`, for each of the 4 models fits on train, calibrates a threshold as the 95th percentile of validation scores, scores test exactly once, computes precision/recall/F1/FPR/per-injection-type breakdown against ground truth, times detection latency (per-instance) and total execution time, records `measurement_context`, persists each fitted model to `data/models/anomaly/{model_type}.pkl` and the full result set to `data/reports/anomaly_benchmark_results.json`; depends on T005, T012, T014-T017
- [x] T019 [US1] Implement `backend/app/anomaly/model_selection.py`: `select_production_model(results)` ranks by F1 primary, FPR tie-break, execution_time second tie-break (research.md's documented rule), sets `tie_break_applied`, returns `ProductionModelSelection`
- [x] T020 [US1] Implement `backend/app/anomaly/router.py`: `POST /anomaly/benchmark` (runs `run_benchmark`, 409 on `AnomalyInputUnavailableError`) and `GET /anomaly/results` (reads persisted `data/reports/anomaly_benchmark_results.json`, 404 if absent) per contracts/api.md
- [x] T021 [US1] Register `anomaly_router` in `backend/app/main.py`, updating the "still placeholders" comment
- [x] T022 [P] [US1] `backend/tests/anomaly/test_leakage_isolation.py`: mirrors Phase 6's pattern — corrupts the test-split portion of the input matrix, re-runs the benchmark, asserts every model's fitted `parameters`/`calibrated_thresholds` are unchanged (SC-001)
- [x] T023 [P] [US1] `backend/tests/anomaly/test_model_selection.py`: recomputes the ranking rule against a fixture `BenchmarkResult[]` and asserts it reproduces `selected_model`, including a tie-break-triggering fixture (SC-004)
- [x] T024 [P] [US1] `backend/tests/anomaly/test_benchmark_metrics.py`: asserts each `BenchmarkResult` has all 5 `per_injection_type_breakdown` keys (SC-002), `measurement_context` is populated (FR-009), and re-scoring the same fitted model against the same injected test data reproduces identical metrics (SC-003)

**Checkpoint**: Full benchmark runs end-to-end and empirically selects a production model.

---

## Phase 5: User Story 3 - Populate the deferred `anomaly_count` window feature (Priority: P2)

**Goal**: Apply the selected production model to real (non-injected) claims per window and populate Phase 5's deferred `WindowFeatures.anomaly_count`.

**Independent Test**: Confirm `anomaly_count` transitions from null to a real integer for every window, using the selected model's scores against real claim data, and that re-running produces identical counts.

### Implementation for User Story 3

- [x] T025 [US3] Implement `backend/app/anomaly/window_enrichment.py`: `enrich_windows()` — reads the persisted `ProductionModelSelection` and its `.pkl` artifact, builds the real (non-injected) per-claim matrix via `data_loading.py`, slices claims into each window's date range (same window bounds as `WindowFeatures`), scores with the selected model's calibrated threshold, counts flagged claims per window, and calls `features_log.update_window_anomaly_count` per window (Phase 5's `PATCH /features/windows/{window_id}/anomaly-count` path); raises `NoProductionModelSelectedError` (409) if no selection exists yet
- [x] T026 [US3] Add `POST /anomaly/enrich-windows` to `backend/app/anomaly/router.py` (returns `{windows_enriched, model_used}`, 409 via `NoProductionModelSelectedError`) per contracts/api.md
- [x] T027 [P] [US3] `backend/tests/anomaly/test_window_enrichment_idempotency.py`: asserts every window's `anomaly_count` is non-null after enrichment (SC-005) and running enrichment twice against unmodified data produces identical counts both times (SC-006, FR-011)

**Checkpoint**: All three user stories independently functional; Phase 8 can now build on real `anomaly_count` values.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T028 Run quickstart.md's manual verification steps end-to-end against a running backend (benchmark → results → selection-matches-F1 check → enrich-windows → idempotency diff) and fix any drift between the contracts and the implementation
- [x] T029 [P] Review all `backend/app/anomaly/*.py` docstrings for consistency with the repo's per-file rationale-comment convention (see `stage1_structural.py`/`temporal_split.py` for the pattern)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 2 (Phase 3)**: Depends on Foundational only
- **User Story 1 (Phase 4)**: Depends on Foundational **and** User Story 2 (benchmark.py calls injection_harness.py) — this is the one cross-story dependency in this feature, called out explicitly because both stories are P1
- **User Story 3 (Phase 5)**: Depends on User Story 1 (needs a `ProductionModelSelection` to exist)
- **Polish (Phase 6)**: Depends on all three user stories

### Parallel Opportunities

- T002, T003 in parallel
- T014, T015, T016, T017 (the four model modules) in parallel — independent files, no shared state
- T022, T023, T024 in parallel once T018-T021 land
- T006, T013, T027 each parallel with their sibling phase's other test-writing once the code they test exists

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2 (setup + foundational)
2. Phase 3 (US2 — injection harness, since US1 depends on it)
3. Phase 4 (US1 — full benchmark + empirical selection) — **this is the feature's MVP**: a real, leakage-free, empirically-selected production model
4. Phase 5 (US3 — closes out Phase 5's deferred `anomaly_count` field) can ship as a fast-follow

### Incremental Delivery

Setup + Foundational → US2 (injection harness testable alone) → US1 (benchmark + selection, MVP) → US3 (window enrichment) → Polish.
