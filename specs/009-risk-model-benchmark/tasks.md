---

description: "Task list for Risk Model Benchmark"
---

# Tasks: Risk Model Benchmark

**Input**: Design documents from `/specs/009-risk-model-benchmark/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md — all present. Depends on Phase 6 (`features/selection` module: persisted `temporal_split.json`) and Phase 8 (`risk/dataset` module: persisted `risk_dataset.csv` + `LabelDistributionReport`) already being implemented, which they are.

**Tests**: Included — plan.md's Testing section names a leakage test, a selection-reproducibility test, and a split-consistency test; one more (label-distribution-reported) and one calibration test are added for the same reason 007/008's tasks.md added extras: every Success Criterion needs a machine-checkable assertion.

**Organization**: Tasks are grouped by user story. US1 (benchmark the 3 classifiers) and US2 (empirical production selection) are both P1 — US2's `model_selection.py`/`router.py` consume US1's `RiskBenchmarkResult[]`, so US1 is implemented first, mirroring 008/007's within-priority sequencing by hard dependency. US3 (calibration reporting, P2) needs no new production code beyond what US1 already produces (the `RiskBenchmarkResult` schema requires `calibration_brier_score` from the start, so it's computed as part of US1's core evaluation loop) — US3's phase is its own dedicated verification test confirming the metric is genuinely present and visible in every run, per spec Acceptance Scenario 2 ("the calibration gap is visible in the output, not hidden").

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (benchmark 3 classifiers under temporal discipline), US2 (empirical production selection), US3 (calibration reporting)

## Path Conventions

Backend module: `backend/app/risk/benchmark/` (new sub-package inside the existing `backend/app/risk/` module, alongside Phase 8's `dataset/`). Tests: `backend/tests/risk/benchmark/`. Reuses `backend/app/features/selection/` (Phase 6: `TemporalSplit`, `assign_split`) and `backend/app/risk/dataset/` (Phase 8: `RiskDatasetRow`, `dataset_log.read_risk_dataset_rows`).

**Note on existing `backend/app/risk/*.py` placeholders**: repo scaffolding created top-level `benchmark.py`, `logistic_model.py`, `random_forest_model.py`, `xgboost_model.py` stub files directly under `backend/app/risk/` (one per name in MVP_CONTEXT.md Section 3's `risk (logistic, random_forest, xgboost, benchmark, scoring)` list). plan.md's Project Structure instead nests this feature's real code under a `benchmark/` sub-package with different filenames (`logistic.py`, not `logistic_model.py`). Setup deletes the four now-superseded top-level stubs; `backend/app/risk/router.py` and `backend/app/risk/scoring.py` are untouched (Phase 10's `scoring` sub-step, not this feature).

---

## Phase 1: Setup

**Purpose**: Align the existing Phase-0 scaffold with plan.md's exact module boundary before any real code goes in.

- [x] T001 Delete the placeholder `backend/app/risk/benchmark.py`, `backend/app/risk/logistic_model.py`, `backend/app/risk/random_forest_model.py`, `backend/app/risk/xgboost_model.py` stub files — superseded by the `backend/app/risk/benchmark/` sub-package this feature creates
- [x] T002 Create `backend/app/risk/benchmark/__init__.py`, so `benchmark` becomes a sub-package per plan.md's Project Structure
- [x] T003 [P] Create `backend/tests/risk/benchmark/__init__.py`

**Checkpoint**: Module skeleton matches plan.md exactly; ready for real implementation.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas and error types every user story's code depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Define `ModelType` (`logistic_regression`/`random_forest`/`xgboost`), `RiskModelCandidate`, `RiskBenchmarkResult`, `ProductionRiskModelSelection` Pydantic models in `backend/app/risk/benchmark/schemas.py` per data-model.md's field tables, plus an additive `RiskBenchmarkRunResult` wrapper (`benchmark_results: list[RiskBenchmarkResult]`, `production_model_selection: ProductionRiskModelSelection`, matching contracts/api.md's response shape exactly) with one extra `data_scale_warning: str | None` field — mirroring Phase 6 `TemporalSplit.sample_size_warning`'s precedent for surfacing a data-scale limitation as a reportable field (spec Edge Cases) rather than a silent pass
- [x] T005 [P] Define `RiskModelInputUnavailableError` (raised when Phase 6's `TemporalSplit` or Phase 8's `risk_dataset.csv` is missing) and `InsufficientClassDiversityError(RiskModelInputUnavailableError)` (raised when the train-split rows contain only one label class, making fitting meaningless) in `backend/app/risk/benchmark/errors.py`

**Checkpoint**: Foundation ready — benchmark work can now begin.

---

## Phase 3: User Story 1 - Benchmark three classifiers on the real risk dataset under strict temporal discipline (Priority: P1) 🎯 MVP

**Goal**: Logistic Regression, Random Forest, and XGBoost each fit on Phase 8's risk dataset restricted to Phase 6's train-range rows, tuned on validation-range rows only, evaluated on test-range rows exactly once, computing accuracy/precision/recall/F1/ROC-AUC/PR-AUC/calibration/false-negative-rate.

**Independent Test**: Confirm all three models are fit using only Phase 8's rows falling in Phase 6's train-split date range, tuned only on validation-range rows, and scored on test-range rows exactly once.

### Implementation for User Story 1

- [x] T006 [US1] Implement `backend/app/risk/benchmark/data_loading.py`: `load_benchmark_frame()` reads Phase 8's `risk_dataset.csv` (via `app.risk.dataset.dataset_log.read_risk_dataset_rows`) and Phase 6's `temporal_split.json` (via `app.features.selection.temporal_split.read_temporal_split`), assigns every row to train/validation/test using `assign_split(row.window_start, split)` (never recomputing the split — FR-002), builds a feature matrix from the 8 raw signal columns (`claim_count`, `gx_failure_count`, `anomaly_score`, `anomaly_frequency`, `affected_claim_pct`, `volume_deviation`, `amount_deviation`, `historical_quality_failure_rate` — deliberately excluding `investigation_risk_indicator`, since it's the exact weighted composite Phase 8 thresholds to produce `investigation_risk_label`, so including it would let a model trivially reproduce the label instead of learning from the underlying signals) and label vector from `investigation_risk_label` per split, and computes `risk_dataset_version` as a SHA-256 hash of the persisted `risk_dataset.csv` bytes (a stable, non-invasive versioning key since Phase 8 itself stamps no version field, satisfying FR-009 without modifying Phase 8); raises `RiskModelInputUnavailableError` if either upstream file is missing, `InsufficientClassDiversityError` if the train split has fewer than 2 label classes
- [x] T007 [P] [US1] Implement `backend/app/risk/benchmark/logistic.py`: `MODEL_TYPE = ModelType.logistic_regression`, a small `HYPERPARAMETER_GRID` (varying `C` with `class_weight="balanced"`), `build_model(params) -> sklearn.linear_model.LogisticRegression`
- [x] T008 [P] [US1] Implement `backend/app/risk/benchmark/random_forest.py`: `MODEL_TYPE = ModelType.random_forest`, a small `HYPERPARAMETER_GRID` (varying `n_estimators`/`max_depth`, `class_weight="balanced"`), `build_model(params) -> sklearn.ensemble.RandomForestClassifier`
- [x] T009 [P] [US1] Implement `backend/app/risk/benchmark/xgboost_model.py`: `MODEL_TYPE = ModelType.xgboost`, a small `HYPERPARAMETER_GRID` (varying `n_estimators`/`max_depth`), `build_model(params) -> xgboost.XGBClassifier` (`objective="binary:logistic"`, `eval_metric="logloss"`)
- [x] T010 [P] [US1] Implement `backend/app/risk/benchmark/calibration.py`: `brier_score(y_true, y_proba) -> float` wrapping `sklearn.metrics.brier_score_loss` (research.md's documented calibration metric — chosen over ECE because it needs no bin-count choice, keeping it exactly reproducible per SC-002)
- [x] T011 [US1] Implement `backend/app/risk/benchmark/benchmark_runner.py`: `run_benchmark()` — for each of the 3 model types, fits every `HYPERPARAMETER_GRID` candidate on train rows only, scores each candidate's PR-AUC on validation rows only (skipping tuning and using the grid's first candidate when validation has fewer than 2 classes, noting this in `data_scale_warning`) to pick the best-tuned `RiskModelCandidate`, then evaluates that one fitted candidate on test rows exactly once at a fixed 0.5 probability threshold (accuracy/precision/recall/F1/false-negative-rate `= 1 - recall`) plus threshold-independent ROC-AUC/PR-AUC and `calibration.brier_score`; persists each fitted model to `data/models/risk/{model_type}.pkl` and returns the full per-model `RiskBenchmarkResult[]` tagged with `risk_dataset_version`/`split_id`; depends on T006-T010
- [x] T012 [P] [US1] `backend/tests/risk/benchmark/test_leakage_isolation.py`: mirrors Phase 7's pattern — corrupts the test-split portion of a fixture risk dataset, re-runs the benchmark, asserts every model's fitted hyperparameters/parameters are unchanged (SC-001)
- [x] T013 [P] [US1] `backend/tests/risk/benchmark/test_split_consistency.py`: cross-checks that `load_benchmark_frame`'s row-to-split assignment matches calling `assign_split` directly against the same fixture `TemporalSplit`, with zero discrepancy (SC-006)

**Checkpoint**: All three models can be fit/tuned/evaluated end-to-end under correct temporal discipline.

---

## Phase 4: User Story 2 - Select the production risk model empirically, prioritizing recall and PR-AUC (Priority: P1)

**Goal**: A documented, non-arbitrary ranking rule (PR-AUC floor gate, then rank by recall, Brier-score tie-break, false-negative-rate final tie-break) selects the production model from the real `RiskBenchmarkResult[]` — never defaulting to XGBoost — plus the working `POST /risk/benchmark` / `GET /risk/benchmark/results` endpoints with versioned run history.

**Independent Test**: Confirm the selected model is the one with the best recall+PR-AUC-weighted ranking among the three, even when a different model has higher raw accuracy.

### Implementation for User Story 2

- [x] T014 [US2] Implement `backend/app/risk/benchmark/model_selection.py`: `select_production_model(results, test_label_base_rate)` excludes any model whose `pr_auc` is at or below `test_label_base_rate` (a random/majority-class classifier's PR-AUC equals the positive base rate exactly, so this is a standard, non-arbitrary "meaningfully better than random" floor — research.md); among survivors (or, if none survive, among all three, flagged via the caller's `data_scale_warning`), ranks by `recall` descending, `calibration_brier_score` ascending as first tie-break, `false_negative_rate` ascending as final tie-break; returns `ProductionRiskModelSelection` with `ranking_rule` stating the rule and `pr_auc_floor_used` set to the computed floor; never defaults to XGBoost by assumption (FR-006)
- [x] T015 [US2] Implement `backend/app/risk/benchmark/benchmark_log.py`: `append_run_result`/`read_latest_run_result`/`read_run_result_by_version` persisting an append-only versioned history to `data/reports/risk_benchmark_results.json` (each entry keyed by `risk_dataset_version`/`split_id`/`generated_at`) — mirrors Phase 4's `snapshot_log.py` append pattern (not Phase 3/7/8's overwrite pattern), since FR-009 requires prior and new runs to remain distinguishable as new data is loaded
- [x] T016 [US2] Implement `backend/app/risk/benchmark/router.py`: `POST /risk/benchmark` (orchestrates `data_loading.load_benchmark_frame` → `benchmark_runner.run_benchmark` → `model_selection.select_production_model` → `benchmark_log.append_run_result`, 409 on `RiskModelInputUnavailableError`) and `GET /risk/benchmark/results` (optional `risk_dataset_version` query param via `benchmark_log.read_run_result_by_version`, else `read_latest_run_result`; 404 if none found) per contracts/api.md
- [x] T017 [US2] Register the new `backend/app/risk/benchmark/router.py` router in `backend/app/main.py`, updating the "still placeholders" comment
- [x] T018 [P] [US2] `backend/tests/risk/benchmark/test_model_selection.py`: recomputes the ranking rule against a fixture `RiskBenchmarkResult[]` and asserts it reproduces `selected_model` (SC-003), including a tie-break-triggering fixture and a fixture where XGBoost has the worst recall (asserting it is correctly *not* selected, spec Acceptance Scenario 3)
- [x] T019 [P] [US2] `backend/tests/risk/benchmark/test_label_distribution_reported.py`: asserts Phase 8's `LabelDistributionReport` context is present and accurate alongside every benchmark run's results (SC-004)
- [x] T020 [P] [US2] `backend/tests/risk/benchmark/test_router_build_and_fetch.py`: FastAPI `TestClient` round-trip — `POST /risk/benchmark` then `GET /risk/benchmark/results` (with and without the `risk_dataset_version` query param) return the persisted run, `POST /risk/benchmark` returns `409` when prerequisites are missing, and `GET /risk/benchmark/results` returns `404` before any build — added beyond the original task list for the same reason 008's tasks.md added a router test: the router-wiring/409/404 contract needs its own machine-checkable assertion, not just the quickstart's manual curl steps

**Checkpoint**: `POST /risk/benchmark` runs end-to-end and empirically selects a production risk model. This is the feature's MVP.

---

## Phase 5: User Story 3 - Evaluate calibration, not just discrimination (Priority: P2)

**Goal**: A documented calibration metric (Brier score) is reported alongside discrimination metrics for every model, so a well-discriminating-but-poorly-calibrated model's gap is visible rather than hidden.

**Independent Test**: Confirm a calibration metric is computed and reported per model on the test split, for every benchmark run.

### Implementation for User Story 3

- [x] T021 [P] [US3] `backend/tests/risk/benchmark/test_calibration_reported.py`: runs the benchmark against a fixture risk dataset and asserts `calibration_brier_score` is present and numeric for all 3 `RiskBenchmarkResult` entries (SC-005), plus a direct unit test on `calibration.brier_score` proving two prediction sets with identical ROC-AUC (identical discrimination) but different confidence produce different Brier scores — the calibration gap is visible rather than masked by a discrimination-only metric (spec Acceptance Scenario 2) — no new production code needed since `benchmark_runner.py` (US1) already computes and includes this field for every model from the start

**Checkpoint**: All three user stories independently functional; Phase 10 can now build on an empirically-selected, calibration-aware production risk model.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T022 Run quickstart.md's manual verification steps end-to-end against a running backend (benchmark → results → selection-matches-ranking-rule check → split-consistency check → calibration-reported check) and fix any drift between the contracts and the implementation
- [x] T023 [P] Review all `backend/app/risk/benchmark/*.py` docstrings for consistency with the repo's per-file rationale-comment convention

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational **and** User Story 1 (`model_selection.py`/`router.py` consume `benchmark_runner.run_benchmark()`'s output) — the one cross-story dependency, called out because both stories are P1
- **User Story 3 (Phase 5)**: Depends on User Story 1 (the field it verifies is produced there); independently testable once US1 lands, without needing US2
- **Polish (Phase 6)**: Depends on all three user stories

### Parallel Opportunities

- T003 alongside T001/T002
- T005 alongside T004
- T007, T008, T009, T010 in parallel once T004/T005 land
- T012, T013 in parallel once T006-T011 land
- T018, T019, T020 in parallel once T014-T017 land
- T021 in parallel with Phase 4 once T011 lands (US3 only needs US1, not US2)
- T023 alongside T022

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2 (setup + foundational)
2. Phase 3 (US1 — benchmark all three classifiers under leakage-free temporal discipline) — a complete, reproducible benchmark ready for selection
3. Phase 4 (US2 — documented empirical selection + working endpoints) — **this is the feature's MVP**: a real, empirically-selected production risk model
4. Phase 5 (US3 — calibration verification) can ship as a fast-follow, or even in parallel with Phase 4 since it only depends on US1

### Incremental Delivery

Setup + Foundational → US1 (benchmark runs and is leakage/consistency-testable alone) → US2 (empirical selection + endpoints, MVP-complete) → US3 (calibration verification) → Polish.
