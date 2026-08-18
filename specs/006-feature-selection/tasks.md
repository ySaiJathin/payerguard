---

description: "Task list for Feature Selection (006)"
---

# Tasks: Feature Selection

**Input**: Design documents from `/specs/006-feature-selection/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: plan.md's Testing section explicitly calls out required pytest tests (test-set-isolation for SC-003, known-constant-column drop for SC-002, `anomaly_count`-exemption for SC-005) plus a temporal-split ordering/determinism test implied by SC-001 — test tasks are included per user story.

**Organization**: Tasks are grouped by user story (US1 shared temporal split, US2 Stage 1 structural filtering, US3 Stage 2/3 + full orchestration/API) to enable independent implementation and testing of each.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

New sub-package at `backend/app/features/selection/`, tests at `backend/tests/features/selection/`, file outputs at `data/features/` (via the existing `features_dir()` in `backend/app/data_engineering/paths.py`) — per plan.md's Project Structure.

## Scope Notes (grounding decisions made at task-generation time)

- **Candidate feature set**: Stage 1/2/3 operate over two parallel candidate frames — a **claim-level** frame (Phase 2's cleaned dataframe columns, keyed by `CLM_ID`, joined with Phase 5's `ClaimFeatures` scalar fields) and a **window-level** frame (Phase 5's `WindowFeatures` scalar fields, keyed by `window_id`). This is what makes the `anomaly_count` exemption (a `WindowFeatures` field) meaningful as a candidate that must survive.
- **Stage 1 runs on the full dataset** (both train+validation and test rows), per data-model.md's `stage_computed_on: full_dataset` note — structural checks (constant/duplicate/raw-ID/leakage) are column-shape properties, not statistics fit on labels, so this doesn't violate FR-010's test-isolation guarantee, which applies to Stage 2/3.
- **Test isolation is structural, not just observed**: `selection_service.py` filters both candidate frames down to train+validation rows (using the `TemporalSplit` boundaries) *before* Stage 2/3 ever see the data — Stage 2/3 functions never receive a full dataframe or a split argument, only the pre-filtered train+validation frame, so there is no code path by which test rows could leak in.
- **Stage 3's target**: the provisional signal is each window's amount/volume deviation magnitude (`abs(WindowFeatures.volume_deviation)` and `abs()` of each `amount_deviation` value, combined), broadcast to each claim via its window membership — since claim-level candidate features need a claim-aligned target for XGBoost/permutation importance.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Replace the Phase-0 `backend/app/features/selection.py` placeholder with the real sub-package skeleton.

- [X] T001 Delete the placeholder `backend/app/features/selection.py` and create `backend/app/features/selection/` package skeleton: `__init__.py`, `schemas.py`, `temporal_split.py`, `stage1_structural.py`, `stage2_statistical.py`, `stage3_model_based.py`, `drop_decision_log.py`, `selection_service.py`, `router.py` (empty modules matching plan.md's Project Structure, plus one extra file `selection_service.py` needed as the top-level orchestrator, analogous to Phase 5's `features_service.py`), and `backend/tests/features/selection/__init__.py`

**Checkpoint**: Module skeleton exists; foundational work can begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas and the deferred-field convention every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Define `TemporalSplit`, `FeatureDropDecision`, and `SelectedFeatureSet` Pydantic models in `backend/app/features/selection/schemas.py` per data-model.md's field tables; `TemporalSplit` additionally carries a `sample_size_warning: str | None = None` field, populated when the validation or test portion falls below a configured minimum row count (edge case: "validation or test portion too small for reliable Stage 2/3 statistics")
- [X] T003 [P] In `backend/app/features/schemas.py` (Phase 5), mark `WindowFeatures.anomaly_count` as deferred via `Field(default=None, json_schema_extra={"deferred": True})`, and add `deferred_window_feature_fields() -> set[str]` that introspects `WindowFeatures.model_fields` for fields whose `json_schema_extra` has `deferred: True` — a schema-level tag, not a hardcoded column-name exception list, per research.md's decision (FR-008)
- [X] T004 Implement `backend/app/features/selection/temporal_split.py`: `compute_temporal_split(claim_dates: pd.Series) -> TemporalSplit` (sorts by date, earliest 70% -> train, next 15% -> validation, latest 15% -> test, zero shuffling, deterministic on unmodified input; sets `sample_size_warning` when validation or test count is below a documented minimum), `assign_split(date, split: TemporalSplit) -> Literal["train", "validation", "test"]` (classifies any date, e.g. a window's `start` date, against the computed boundaries), `write_temporal_split(split, out_dir=None) -> Path` and `read_temporal_split(out_dir=None) -> TemporalSplit | None`, persisting to `data/features/temporal_split.json` via `features_dir()` (FR-001, FR-002; depends on T002)

**Checkpoint**: Foundation ready — US1, US2, and (with US1/US2 output) US3 can proceed.

---

## Phase 3: User Story 1 - Establish the shared temporal split (Priority: P1) 🎯 MVP

**Goal**: A single, deterministic, chronological 70/15/15 `TemporalSplit` is computed once and exposed via the API for Phase 7/9 to reuse.

**Independent Test**: Compute the split once and confirm the training portion contains only chronologically earlier claims than validation, which is earlier than test, with zero date overlap.

### Tests for User Story 1

- [X] T005 [P] [US1] Test: given a fixture of claim dates spanning a known range, `compute_temporal_split` assigns the earliest 70% to train / next 15% to validation / latest 15% to test with zero date-range overlap, and re-running against the unmodified fixture reproduces an identical assignment, in `backend/tests/features/selection/test_temporal_split.py` (FR-001, FR-002, SC-001)

### Implementation for User Story 1

- [X] T006 [US1] Implement `backend/app/features/selection/router.py`: `POST /features/split` (computes via T004 if no split is persisted yet, else returns the existing one; response `TemporalSplit`) and `GET /features/split` (pure read via `read_temporal_split`, `404` if none computed yet — never triggers computation) per contracts/api.md (depends on T004)
- [X] T007 [US1] Wire the new `selection_router` (from T006) into `backend/app/main.py` alongside the existing `features_router`, both mounted under the `/features` prefix (depends on T006)

**Checkpoint**: User Story 1 is independently functional — the shared split can be computed, persisted, and read back via the API.

---

## Phase 4: User Story 2 - Apply Stage 1 (structural) filtering (Priority: P1)

**Goal**: Constant, near-constant, duplicate, raw-identifier, high-missingness, and leakage-risk columns are dropped from both candidate frames before any statistical/model-based selection runs, with every drop recorded.

**Independent Test**: Confirm the specific columns MVP_CONTEXT.md Section 2.2 already flags (constant columns, fully-null columns) are dropped by Stage 1 alone, without running Stage 2/3.

### Tests for User Story 2

- [X] T008 [P] [US2] Test: a fixture cleaned-claims dataframe containing the documented constant columns (`NCH_CLM_TYPE_CD`, `CLM_FREQ_CD`, `CLAIM_QUERY_CODE`, `CLM_MDCR_NON_PMT_RSN_CD`, `PTNT_DSCHRG_STUS_CD`) and fully-null columns (`OT_PHYSN_UPIN`, `FI_NUM`) — when Stage 1 runs, all appear in the drop list with the correct reason (`"constant column..."` vs `"high-missingness..."`); raw identifier columns (`CLM_ID`, `BENE_ID`, `PRVDR_NUM`) are dropped as raw-ID; a synthetic column matching a leakage naming pattern is dropped with a leakage reason; and a `WindowFeatures` fixture with `anomaly_count` all-null does NOT appear in any Stage 1 drop list, in `backend/tests/features/selection/test_stage1_structural.py` (FR-003, FR-004, FR-005, FR-008, SC-002)

### Implementation for User Story 2

- [X] T009 [US2] Implement `backend/app/features/selection/stage1_structural.py`: `drop_constant_and_near_constant(df, near_constant_threshold=0.99) -> list[FeatureDropDecision]` (single value, or one value covering >= threshold of non-null rows), `drop_duplicate_columns(df) -> list[FeatureDropDecision]` (columns that are exact duplicates of an earlier column, keeping the first occurrence), `drop_raw_identifiers(columns, categories) -> list[FeatureDropDecision]` (drops columns categorized `ColumnCategory.IDENTIFIER` by Phase 1's `categories` dict — `CLM_ID`, `BENE_ID`, `PRVDR_NUM`, NPI columns, `FI_NUM`), `drop_high_missingness(df, threshold=0.95, exempt_fields=frozenset()) -> list[FeatureDropDecision]` (skips any column in `exempt_fields`, i.e. T003's `deferred_window_feature_fields()`), `drop_leakage_risk(columns, leakage_name_patterns) -> list[FeatureDropDecision]` (a documented, configurable list of case-insensitive substrings such as `"OUTCOME"`, `"INVESTIGATION"`, `"INCIDENT"` that would indicate a post-hoc-derived column) — each returns one `FeatureDropDecision` per flagged column with `stage=1`, `stage_computed_on="full_dataset"` (FR-003, FR-004, FR-005; depends on T002, T003)
- [X] T010 [US2] Implement `apply_stage1(cleaned_df, claim_features, window_features, categories) -> tuple[dict[str, list[str]], list[FeatureDropDecision]]` in `backend/app/features/selection/stage1_structural.py`: builds the claim-level candidate frame (raw `cleaned_df` columns joined with `ClaimFeatures` scalar fields on `CLM_ID`, excluding `encoded_categoricals`) and the window-level candidate frame (`WindowFeatures` scalar fields), runs all five T009 checks against each frame, and returns `{"claim": [...surviving columns...], "window": [...]}` plus the combined decision list; raises a new `AllFeaturesDroppedError` (defined in this module) if every column of a single Phase-1 `ColumnCategory` is dropped (FR-011, edge case; depends on T009)
- [X] T011 [US2] Implement `backend/app/features/selection/drop_decision_log.py`: `write_drop_decisions(decisions: list[FeatureDropDecision], out_dir=None) -> Path` and `read_drop_decisions(stage: int | None = None, out_dir=None) -> list[FeatureDropDecision]` (optional stage filter), persisting to `data/features/feature_drop_decisions.json`, overwrite semantics matching Phase 3/5's `*_log.py` precedent (FR-009; depends on T002)

**Checkpoint**: User Story 2 is independently functional — Stage 1 can run standalone against fixtures and produce a complete, correctly-reasoned drop list.

---

## Phase 5: User Story 3 - Apply Stage 2/3 fit on train+validation only, and expose the full pipeline (Priority: P2)

**Goal**: The Stage 1 survivors are further narrowed by Stage 2 (statistical) and Stage 3 (model-based) thresholds computed exclusively on train+validation data, and the full pipeline is orchestrated end-to-end behind the `/features` API.

**Independent Test**: Confirm no Stage 2/3 threshold, correlation figure, or importance ranking changes when the test-split portion of the input is deliberately corrupted.

### Tests for User Story 3

- [X] T012 [P] [US3] Test: running `selection_service.run_selection()` once, then corrupting only the test-split portion (per the persisted `TemporalSplit`) of the source fixture and re-running, produces byte-identical `SelectedFeatureSet.features`, identical Stage 2/3 `FeatureDropDecision.statistic_value`s, in `backend/tests/features/selection/test_leakage_isolation.py` (FR-010, SC-003)
- [X] T013 [P] [US3] Test: after `run_selection()`, `anomaly_count` is absent from every stage's `FeatureDropDecision` list (Stage 1 via T009/T010, Stage 2 via T014) despite being 100% null in the fixture, in `backend/tests/features/selection/test_anomaly_count_exempt.py` (FR-008, SC-005)

### Implementation for User Story 3

- [X] T014 [US3] Implement `backend/app/features/selection/stage2_statistical.py`: `apply_stage2(train_val_df, columns, exempt_fields=frozenset()) -> tuple[list[str], list[FeatureDropDecision]]` — drops near-zero-variance columns (`sklearn.feature_selection.VarianceThreshold`), high-cardinality categorical columns above a documented threshold, columns above the missingness threshold (skipping `exempt_fields`), and one of each highly-correlated pair (Pearson correlation above a documented cutoff, or mutual information for categorical/numeric pairs via `sklearn.feature_selection.mutual_info_classif`/`mutual_info_regression`) — tie-break keeps the column with lower missingness, then (if tied) the one with lower entry in a static `_DERIVATION_DEPTH` map (raw source columns = 0, single-step derived features = 1, multi-step = 2+); every statistic is computed only from the passed-in `train_val_df`, never a full dataset (FR-006; depends on T002, T003)
- [X] T015 [US3] Implement `backend/app/features/selection/stage3_model_based.py`: `apply_stage3(train_val_df, columns, target: pd.Series, importance_threshold=..., rfe_feature_count_ceiling=...) -> tuple[list[str], list[FeatureDropDecision]]` — fits `xgboost.XGBRegressor` on `train_val_df[columns]` against `target`, computes feature importances and permutation importance (`sklearn.inspection.permutation_importance`), drops columns below `importance_threshold`; if the surviving count still exceeds `rfe_feature_count_ceiling`, runs `sklearn.feature_selection.RFE` to narrow further; every `FeatureDropDecision.reason` names the specific statistic and threshold crossed (FR-007; depends on T002)
- [X] T016 [US3] Implement `backend/app/features/selection/selection_service.py`: `run_selection() -> SelectedFeatureSet` — loads Phase 5's `read_claim_features()`/`read_window_features()` and Phase 2's cleaned batch (raising `FeaturesInputUnavailableError`, defined in this module, if any are missing, mirroring `app.features.features_service`'s pattern), computes or reads the `TemporalSplit` (T004), builds the provisional target (each window's `abs(volume_deviation)` plus summed `abs()` of `amount_deviation` values, broadcast to claims via window membership), filters both candidate frames to train+validation rows only using `assign_split` (T004) *before* calling Stage 2/3 (structural test-isolation, FR-010), calls `apply_stage1` (T010, full data) -> `apply_stage2` (T014, train+validation only) -> `apply_stage3` (T015, train+validation only), and assembles a `SelectedFeatureSet` with `target_used="provisional_deviation_magnitude"` and the three stage drop counts (depends on T004, T010, T011, T014, T015)
- [X] T017 [US3] Add `write_selected_feature_set(feature_set: SelectedFeatureSet, out_dir=None) -> Path` and `read_selected_feature_set(out_dir=None) -> SelectedFeatureSet | None` to `backend/app/features/selection/drop_decision_log.py` (from T011), persisting to `data/features/selected_feature_set.json` (FR-009; depends on T002, T011)
- [X] T018 [US3] Extend `backend/app/features/selection/router.py` (from T006): `POST /features/select` (calls T016, persists the decisions via T011 and the feature set via T017, returns `SelectedFeatureSet`, `409` on `FeaturesInputUnavailableError`), `GET /features/selected` (T017, `404` if none computed yet), `GET /features/drop-decisions` with optional `stage` query param (T011) — per contracts/api.md (depends on T016, T017, T011, T007)

**Checkpoint**: All three user stories work independently and together — `POST /features/split` then `POST /features/select` produces a fully audited `SelectedFeatureSet` with structural test-set isolation.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verification that spans all three stories.

- [X] T019 Run the full `backend/tests/features/selection/` suite plus `backend/tests/features/` and `backend/tests/baseline/` (`pytest backend/tests/`) to confirm no regression from T003's `WindowFeatures` schema change, and fix any failures
- [X] T020 Execute quickstart.md's curl-based verification steps end to end (split + select, known-constant-column drop check, test-set-isolation test, `anomaly_count` exemption check, every-drop-has-a-reason check) against a running backend instance, confirming each documented expected outcome

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (T004's `temporal_split.py`, itself depending on T002). Independent of US2.
- **User Story 2 (Phase 4)**: Depends on Foundational (T002, T003). Independent of US1 — Stage 1 doesn't need the split (it runs on the full dataset).
- **User Story 3 (Phase 5)**: Depends on US1's `temporal_split.py` (T004) and US2's `apply_stage1`/`drop_decision_log.py` (T010, T011) — this is the integration point where all three stories join. T007 (router wiring) must also be done before T018 extends the same router.
- **Polish (Phase 6)**: Depends on all three user stories.

### Within Each User Story

- Tests before implementation (write first, confirm they fail, then implement).
- Foundational schema (T002) before any stage module that returns `FeatureDropDecision` (T009-T017).
- Stage 1 checks (T009) before the Stage 1 orchestrator (T010).
- Stage 2 (T014) and Stage 3 (T015) before the top-level orchestrator (T016).
- `selection_service.py` (T016) before the router endpoints that call it (T018).

### Parallel Opportunities

- T002 and T003 (Foundational) can run in parallel — different files.
- T005 (US1 test) has no same-file conflict with T006/T007 and can be written before or alongside them.
- T008 (US2 test) can be written in parallel with Foundational/US1 work — different file.
- T012 and T013 (US3 tests) can run in parallel — different files.

---

## Parallel Example: Foundational + User Story 1

```bash
# Foundational, together:
Task: "Define TemporalSplit, FeatureDropDecision, SelectedFeatureSet in backend/app/features/selection/schemas.py"
Task: "Mark WindowFeatures.anomaly_count deferred + add deferred_window_feature_fields() in backend/app/features/schemas.py"

# User Story 1 test, independent of the above file:
Task: "Test temporal split chronological ordering + determinism in backend/tests/features/selection/test_temporal_split.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1 — the shared `TemporalSplit` is computable, persistable, and readable via the API, ready for Phase 7/9 to consume even before Stage 1/2/3 exist.
4. **STOP and VALIDATE**: Run T005 against T004.

### Incremental Delivery

1. Setup + Foundational -> foundation ready.
2. User Story 1 -> shared temporal split validated independently; Phase 7/9 unblocked to start reusing it.
3. User Story 2 -> Stage 1 structural filtering validated independently against fixtures.
4. User Story 3 -> Stage 2/3 + full orchestration + API, completing the pipeline; test-set isolation proven structurally.
5. Polish -> full-suite regression check + quickstart validation.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- No task fabricates a threshold, statistic, or importance score — every drop decision's `statistic_value` is computed from real data (constitution Principle II, FR-009).
- Stage 2/3 functions structurally never receive the test-split portion as an argument — test isolation is enforced by `selection_service.py`'s filtering, not caller discipline (FR-010, contracts/api.md's Notes section).
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
