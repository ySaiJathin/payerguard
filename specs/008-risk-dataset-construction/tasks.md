---

description: "Task list for Risk Dataset Construction"
---

# Tasks: Risk Dataset Construction

**Input**: Design documents from `/specs/008-risk-dataset-construction/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md — all present. Depends on Phase 3 (`quality` module: persisted `quality_results.json`), Phase 4 (`baseline` module: persisted `baseline_snapshot.json`), Phase 5/6 (`features` module: `WindowFeatures`, persisted `temporal_split.json`), and Phase 7 (`anomaly` module: `WindowFeatures.anomaly_count` enrichment) already being implemented, which they are.

**Tests**: Included — plan.md's Testing section names three required test files (row provenance, label reproducibility, zero-claim-window label); additional tests are added for the same reason 007's tasks.md added extras: every Success Criterion and fail-fast edge case needs a machine-checkable assertion, not just a manual quickstart step.

**Organization**: Tasks are grouped by user story. US1 (row assembly) and US2 (label derivation) are both P1 — US2's `label_formula.py` consumes US1's assembled (pre-label) rows, so US1 is implemented first within the shared P1 priority, mirroring how 007's tasks.md sequenced its two P1 stories by hard dependency. The router/service integration that ships the working `POST /risk/dataset/build` endpoint is placed at the end of the US2 phase because its response (`rows_built`, `label_distribution`, `formula_version`) is only meaningful once both US1 and US2's logic exist. US3 (temporal ordering) is P2 and adds a chronological-sort guarantee plus its own verification test on top of fields US1 already produces.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 (assemble window-grain rows from upstream signals), US2 (derive + document the investigation-risk label), US3 (preserve temporal ordering)

## Path Conventions

Backend module: `backend/app/risk/dataset/` (new sub-package inside the existing `backend/app/risk/` placeholder module). Tests: `backend/tests/risk/dataset/`. Reuses `backend/app/quality/` (Phase 3), `backend/app/baseline/` (Phase 4), `backend/app/features/` (Phase 5), `backend/app/features/selection/` (Phase 6), `backend/app/anomaly/` (Phase 7).

**Note on `backend/app/risk/dataset.py`**: repo scaffolding created this as a placeholder *file*. plan.md's Project Structure requires `dataset` to be a *sub-package* (directory) so `row_assembly.py`/`label_formula.py`/`label_distribution.py`/`router.py` can live inside it. Setup replaces the file with the directory; `backend/app/risk/router.py` and the other `backend/app/risk/*.py` placeholder files (Phase 9/10's `benchmark.py`, `scoring.py`, `logistic_model.py`, `random_forest_model.py`, `xgboost_model.py`) are untouched.

---

## Phase 1: Setup

**Purpose**: Align the existing Phase-0 scaffold with plan.md's exact module boundary before any real code goes in.

- [x] T001 Add `risk_dir()` to `backend/app/data_engineering/paths.py` (returns `find_data_dir() / "risk"`), for `data/risk/risk_dataset.csv` and `data/risk/investigation_risk_label_formula.md` per plan.md's Storage section
- [x] T002 Delete the placeholder `backend/app/risk/dataset.py` stub file and create `backend/app/risk/dataset/__init__.py` in its place, so `dataset` becomes a sub-package per plan.md's Project Structure
- [x] T003 [P] Create `backend/tests/risk/__init__.py` and `backend/tests/risk/dataset/__init__.py`

**Checkpoint**: Module skeleton matches plan.md exactly; ready for real implementation.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas and error types every user story's code depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Define `RiskDatasetRow`, `InvestigationRiskLabelFormula`, `LabelDistributionReport`, `RiskDatasetBuildResult` Pydantic models in `backend/app/risk/dataset/schemas.py` per data-model.md's field tables
- [x] T005 [P] Define `RiskDatasetInputUnavailableError` (raised when Phase 3/4/5 persisted outputs are missing) and `AnomalyEnrichmentIncompleteError(RiskDatasetInputUnavailableError)` (raised when any `WindowFeatures.anomaly_count` is still `None`, spec FR-008) in `backend/app/risk/dataset/errors.py`

**Checkpoint**: Foundation ready — row assembly and label derivation work can now begin.

---

## Phase 3: User Story 1 - Assemble window-grain rows from every upstream signal (Priority: P1) 🎯 MVP

**Goal**: One row per Phase 4/5 window carrying every real, already-computed upstream signal (GX failure count, anomaly frequency, affected-claim %, volume/amount deviation, historical quality-failure rate, claim count) with zero independently-recomputed statistics.

**Independent Test**: Confirm each row's fields are traceable back to a specific upstream phase's persisted output (Phase 3's quality results, Phase 5/7's window features, Phase 4's baseline) rather than being independently computed or assumed.

### Implementation for User Story 1

- [x] T006 [US1] Implement `backend/app/risk/dataset/row_assembly.py`: `assemble_rows(include_warning_in_gx_failure_count=True)` reads Phase 5's `window_features.csv` (post-Phase-7 enrichment) for `window_id`/`window_start`/`window_end`/`claim_count`/`volume_deviation`/`missing_pct`/`duplicate_pct`/`invalid_status_pct`/`anomaly_count`, Phase 3's `quality_results.json` for `gx_failure_count` (count of `Band.CRITICAL`, plus `Band.WARNING` when `include_warning_in_gx_failure_count` is true — documented as a batch-level count carried unchanged onto every row, since Phase 3's checks have no window dimension to partition by), and Phase 4's `baseline_snapshot.json` for `historical_quality_failure_rate` (mean of `historical_missing_rate_by_column.values()` combined with `historical_duplicate_rate` — also a batch-level constant per run, both values 0-100 scale matching `WindowFeatures`'s own pct fields); derives `anomaly_frequency = anomaly_count / claim_count` (0.0 for zero-claim windows), `anomaly_score = anomaly_frequency * 100`, `amount_deviation = max(abs(v) for v in WindowFeatures.amount_deviation.values())` (0.0 if empty — reduces Phase 5's per-amount-column dict to the single most-deviated column, matching how research.md's IRI formula treats volume/amount deviation as directly comparable scalars), and `affected_claim_pct = 100 * (1 - (1 - quality_issue_rate) * (1 - anomaly_frequency))` where `quality_issue_rate = 1 - (1 - duplicate_pct/100) * (1 - invalid_status_pct/100)` (a union-of-independent-rates approximation over Phase 5's own real per-claim/per-row quality proxies — `missing_pct` is deliberately excluded because it is a per-cell rate, not a per-claim rate, so including it would conflate grains); raises `AnomalyEnrichmentIncompleteError` if any window's `anomaly_count` is `None` and `RiskDatasetInputUnavailableError` if Phase 3/4/5 outputs are missing
- [x] T007 [P] [US1] `backend/tests/risk/dataset/test_row_provenance.py`: builds fixture Phase 3/4/5 persisted outputs, calls `assemble_rows`, and asserts every `RiskDatasetRow` field (or, for the documented derived fields, the exact documented combination of upstream values) matches its upstream source — no field is invented independently of the fixtures (SC-001)
- [x] T008 [P] [US1] `backend/tests/risk/dataset/test_missing_enrichment_fails_fast.py`: a fixture window with `anomaly_count=None` causes `assemble_rows` to raise `AnomalyEnrichmentIncompleteError` rather than assembling a row with a fabricated/zeroed anomaly signal (FR-008, Edge Cases)
- [x] T009 [P] [US1] `backend/tests/risk/dataset/test_zero_claim_window_fields.py`: a fixture zero-claim window (`claim_count=0`) produces a row with genuine zero/undefined values for every claim-dependent field (`anomaly_frequency`, `affected_claim_pct`, etc.) rather than being skipped or defaulted to a non-zero placeholder (Acceptance Scenario 4)

**Checkpoint**: `assemble_rows` is independently testable and ready for the label formula to consume.

---

## Phase 4: User Story 2 - Derive and document the investigation-risk label explicitly (Priority: P1)

**Goal**: A single, documented `InvestigationRiskLabelFormula` (weights, train-split-only normalization, percentile threshold) applied deterministically to every row, persisted as a reviewable artifact that explicitly cites MVP_CONTEXT.md Section 2.4, plus a `LabelDistributionReport`, plus the working `POST /risk/dataset/build` / `GET /risk/dataset` / `GET /risk/dataset/label-formula` endpoints.

**Independent Test**: Confirm a documented artifact states the exact formula/thresholds, and that re-applying that documented formula to a row's own stored input fields reproduces that row's stored label exactly.

### Implementation for User Story 2

- [x] T010 [US2] Implement `backend/app/risk/dataset/label_formula.py`: `compute_formula(rows, split)` computes per-signal min/max normalization statistics using only rows whose `window_start` falls in `split.train_date_range` (via `app.features.selection.temporal_split.assign_split`, never validation/test — constitution Principle VII), builds an `InvestigationRiskLabelFormula` with default weights `w_q=0.4, w_a=0.4, w_d=0.2`, `percentile_threshold=75.0`, `formula_version="v1"`, and a `rationale_text` explicitly citing MVP_CONTEXT.md Section 2.4's rejection of a timing-based label (research.md); `apply_formula(rows, formula)` computes `investigation_risk_indicator = w_q*norm(historical_quality_failure_rate/100) + w_a*norm(anomaly_frequency) + w_d*norm(amount_deviation_scalar)` per row (`norm` clips to [0, 1] using the formula's persisted min/max), thresholds against the train-split IRI's 75th percentile for `investigation_risk_label`, and forces `investigation_risk_label = 0` for every zero-claim-window row regardless of its IRI (FR-006, SC-004)
- [x] T011 [US2] Implement `render_formula_markdown(formula)` in `backend/app/risk/dataset/label_formula.py`: renders `InvestigationRiskLabelFormula` (weights, normalization stats, threshold, `rationale_text`, `generated_at`) as reviewable Markdown per research.md's decision that the artifact must be independently reviewable, "not only embedded in code" (FR-003, FR-004)
- [x] T012 [US2] Implement `backend/app/risk/dataset/label_distribution.py`: `compute_label_distribution(rows)` returns a `LabelDistributionReport` (total/investigation-worthy/not-investigation-worthy counts and percentages, `zero_claim_window_count`) computed from the actual assembled+labeled rows (FR-009)
- [x] T013 [US2] Implement `backend/app/risk/dataset/dataset_log.py`: `write_risk_dataset_rows`/`read_risk_dataset_rows` (persist `RiskDatasetRow[]` as `data/risk/risk_dataset.csv`, overwrite-on-each-run per Phase 3's `quality_results_log.py` precedent) and `write_label_formula`/`read_label_formula` (persist `InvestigationRiskLabelFormula` as `data/risk/investigation_risk_label_formula.json`, plus regenerate `data/risk/investigation_risk_label_formula.md` from `render_formula_markdown` on every write, per research.md)
- [x] T014 [US2] Implement `backend/app/risk/dataset/service.py`: `build_risk_dataset()` orchestrates `row_assembly.assemble_rows()` → `label_formula.compute_formula()` + `apply_formula()` → `label_distribution.compute_label_distribution()` → persists rows and formula via `dataset_log.py` → returns `RiskDatasetBuildResult(rows_built, label_distribution, formula_version)`; propagates `RiskDatasetInputUnavailableError`/`AnomalyEnrichmentIncompleteError` for the router's 409 (FR-008, FR-010)
- [x] T015 [US2] Implement `backend/app/risk/dataset/router.py`: `POST /risk/dataset/build` (calls `service.build_risk_dataset()`, 409 on `RiskDatasetInputUnavailableError`), `GET /risk/dataset` (reads persisted rows via `dataset_log.read_risk_dataset_rows`, 404 if none built yet), `GET /risk/dataset/label-formula` (reads persisted formula via `dataset_log.read_label_formula`, 404 if none built yet) per contracts/api.md
- [x] T016 [US2] Register the new `backend/app/risk/dataset/router.py` router in `backend/app/main.py`, updating the "still placeholders" comment (the top-level `backend/app/risk/router.py` placeholder for Phase 9/10 stays untouched)
- [x] T017 [P] [US2] `backend/tests/risk/dataset/test_label_reproducibility.py`: re-applies `InvestigationRiskLabelFormula` by hand to each row's own stored input fields and asserts it reproduces that row's stored `investigation_risk_label` exactly for every row (SC-002); also runs `build_risk_dataset()` twice against unmodified fixture upstream data and asserts byte-identical persisted `RiskDatasetRow` records, including labels (SC-006, FR-010)
- [x] T018 [P] [US2] `backend/tests/risk/dataset/test_zero_claim_window_label.py`: a fixture zero-claim window's row has `investigation_risk_label == 0` even when its (zero-claim-adjusted) `investigation_risk_indicator` would otherwise clear the threshold (SC-004, FR-006)
- [x] T019 [P] [US2] `backend/tests/risk/dataset/test_formula_rationale_references_section_2_4.py`: asserts `InvestigationRiskLabelFormula.rationale_text` contains "Section 2.4" (case-insensitive) and that the rendered Markdown artifact does too (SC-003)
- [x] T020 [P] [US2] `backend/tests/risk/dataset/test_router_build_and_fetch.py`: FastAPI `TestClient` round-trip — `POST /risk/dataset/build` then `GET /risk/dataset` and `GET /risk/dataset/label-formula` return the persisted data, and `POST /risk/dataset/build` returns `409` when fixture Phase 3/4/5 outputs are absent or Phase 7 enrichment is incomplete

**Checkpoint**: `POST /risk/dataset/build` runs end-to-end and produces a documented, reproducible investigation-risk label. This is the feature's MVP.

---

## Phase 5: User Story 3 - Preserve temporal ordering for the eventual train/val/test split (Priority: P2)

**Goal**: Every row carries its window's chronological position explicitly and unambiguously, so Phase 9 can apply the temporal 70/15/15 split without re-deriving chronology.

**Independent Test**: Confirm sorting the dataset by its chronological field reproduces the true chronological window sequence, and each row can be matched against Phase 6's `TemporalSplit` boundaries without recomputing the split.

### Implementation for User Story 3

- [x] T021 [US3] In `backend/app/risk/dataset/row_assembly.py`, explicitly sort `assemble_rows`'s returned rows by `window_start` ascending before returning, guaranteeing FR-007's chronological ordering regardless of Phase 5's on-disk row order
- [x] T022 [P] [US3] `backend/tests/risk/dataset/test_temporal_ordering.py`: sorting assembled rows by `window_start` reproduces the true chronological window sequence (Acceptance Scenario 1), and calling `app.features.selection.temporal_split.assign_split` on each row's `window_start` against a fixture `TemporalSplit` unambiguously assigns every row to train/validation/test with no gaps or overlaps (Acceptance Scenario 2)

**Checkpoint**: All three user stories independently functional; Phase 9 can now build on a complete, documented, chronologically-ordered risk dataset.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T023 Run quickstart.md's manual verification steps end-to-end against a running backend (build → verify provenance → verify label reproducibility → verify Section 2.4 reference → verify zero-claim labels) and fix any drift between the contracts and the implementation
- [x] T024 [P] Review all `backend/app/risk/dataset/*.py` docstrings for consistency with the repo's per-file rationale-comment convention (see `quality/gx_result_utils.py`/`baseline/schemas.py` for the pattern)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational **and** User Story 1 (`label_formula.py`/`service.py` consume `row_assembly.assemble_rows()`'s output) — the one cross-story dependency, called out because both stories are P1
- **User Story 3 (Phase 5)**: Depends on User Story 1 (edits `row_assembly.py`) and is verifiable once User Story 2's `service.py`/router exist end-to-end, though its own change is additive to US1's file
- **Polish (Phase 6)**: Depends on all three user stories

### Parallel Opportunities

- T003 alongside T001/T002
- T005 alongside T004
- T007, T008, T009 in parallel once T006 lands
- T017, T018, T019, T020 in parallel once T010-T016 land
- T022 in parallel with Polish once T021 lands
- T024 alongside T023

---

## Implementation Strategy

### MVP First

1. Phase 1 + Phase 2 (setup + foundational)
2. Phase 3 (US1 — row assembly, no independently-recomputed fields) — **this is the feature's MVP**: a complete, provenance-traceable window-grain dataset ready for labeling
3. Phase 4 (US2 — documented, reproducible investigation-risk label + working endpoints)
4. Phase 5 (US3 — explicit chronological ordering) can ship as a fast-follow

### Incremental Delivery

Setup + Foundational → US1 (rows assemble and are provenance-testable alone) → US2 (label formula + endpoints, MVP-complete) → US3 (temporal ordering guarantee) → Polish.
