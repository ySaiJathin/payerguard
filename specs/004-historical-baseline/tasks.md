---

description: "Task list for 004-historical-baseline"
---

# Tasks: Historical Baseline

**Input**: Design documents from `/specs/004-historical-baseline/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: plan.md's Testing section explicitly requires a determinism/no-hardcoding test (SC-002) and a length-of-stay exclusion test (SC-004), so test tasks are included per user story.

**Organization**: Tasks are grouped by user story (US1/US2/US3 from spec.md) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task description

## Path Conventions

Backend module per plan.md's Project Structure: `backend/app/baseline/` (source), `backend/tests/baseline/` (tests), `data/reports/baseline_snapshot.json` (persisted output). Existing scaffolding placeholders at `backend/app/baseline/{__init__,router,service}.py` and `backend/app/models/baseline.py` are replaced by this feature's implementation tasks (the `models/baseline.py` ORM placeholder stays a placeholder — plan.md's Storage section designates the file-based `baseline_snapshot.json` path as the MVP home, matching the `models/quality.py` precedent from 003).

---

## Phase 1: Setup

**Purpose**: Establish the module skeleton and shared schemas every story builds on.

- [X] T001 Create `backend/tests/baseline/__init__.py` (empty, matches `backend/tests/quality/__init__.py` precedent) and confirm `backend/app/baseline/` package dir already exists (it does, from repo scaffolding).
- [X] T002 [P] Replace the placeholder docstring in `backend/app/baseline/__init__.py` with a real module docstring describing the baseline module's scope (volume/amount/data-health/length-of-stay baselines + snapshot persistence), matching the style of `backend/app/quality/__init__.py`.
- [X] T003 Define `backend/app/baseline/schemas.py` with the Pydantic models from data-model.md: `VolumeWindow`, `VolumeBaseline`, `AmountBaseline`, `Percentiles` (p25/p50/p75/p95/p99), `DataHealthBaseline`, `LengthOfStayBaseline`, `BaselineSnapshot`. Every field name must avoid "processing_time"/"sla"/"turnaround" per FR-006/SC-005 — this is the schema-level enforcement point for that constraint.

**Checkpoint**: Schemas compile and import cleanly; no story work depends on anything beyond this.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure every user story's baseline computation reads from — input loading and provenance helpers.

**⚠️ CRITICAL**: No user story task can begin until this phase is complete.

- [X] T004 Implement `backend/app/baseline/window_definition.py`: a documented, configurable window definition (FR-001, Assumptions) — a default `"daily"` calendar-day window over `CLM_FROM_DT` plus support for an `"N-claim-batch"` alternative, per research.md's date-based/batch-index decision (not wall-clock). Export a function that takes a `pd.DataFrame` + window kind and returns ordered window boundaries.
- [X] T005 Implement `backend/app/baseline/snapshot_service.py`'s input-loading helper: load Phase 2's cleaned batch (`data/cleaned/inpatient_cleaned.csv` via `app.data_engineering.paths.cleaned_dir()` and `CLEANED_OUTPUT_FILENAME`, with dtypes from `app.quality.data_loader.load_cleaned_batch` / `app.data_engineering.dtype_conversion.load_column_categories`) and Phase 3's `data/reports/quality_results.json` (via `app.quality.quality_results_log.read_quality_results`). Raise a `BaselineInputUnavailableError(FileNotFoundError)` if either is missing, mirroring `QualityInputUnavailableError`'s pattern (FR-007's provenance needs both source and quality inputs to exist first).
- [X] T006 [P] Implement the provenance-record builder in `backend/app/baseline/snapshot_service.py`: given the loaded cleaned dataframe and its source path, produce `{source_file, source_row_count, source_date_range: {min_date, max_date}}` from `CLM_FROM_DT` (FR-007, SC-006). This is a pure function reusable by every story's snapshot assembly.

**Checkpoint**: Input loading and provenance are ready — all user stories can now proceed.

---

## Phase 3: User Story 1 - Volume and amount baseline (Priority: P1) 🎯 MVP

**Goal**: Compute claim-volume-per-window and amount distribution statistics (mean/median/std/min/max/percentiles) from the cleaned historical data, matching MVP_CONTEXT.md 2.2's documented `CLM_PMT_AMT` ground truth.

**Independent Test**: Compute the baseline from Phase 2's cleaned output; confirm `CLM_PMT_AMT`/`CLM_TOT_CHRG_AMT` mean/median/std/percentiles match Section 2.2's documented figures (mean $13,638.31, median $1,481.72, std $35,993.91 for `CLM_PMT_AMT`), and that every window (including zero-claim ones) appears in `VolumeBaseline.windows`.

### Tests for User Story 1

- [X] T007 [P] [US1] Write `backend/tests/baseline/test_volume_baseline.py`: assert every window in the computed range appears in output including a zero-claim window from a fixture with an intentional date gap (SC-003), and that `window_definition` is recorded.
- [X] T008 [P] [US1] Write `backend/tests/baseline/test_amount_baseline.py` (per plan.md's Testing section): assert mean/median/std/min/max/percentiles are computed for a small fixture with hand-computable expected values, covering both `CLM_PMT_AMT` and `CLM_TOT_CHRG_AMT` as independent, separately-stored statistics (spec Edge Cases: don't assume they're always identical).
- [X] T009 [US1] Write `backend/tests/baseline/test_no_hardcoding.py` (SC-002, plan.md's Testing section): mutate a fixture's `CLM_PMT_AMT` values, recompute the amount baseline, and assert `mean`/`median` change accordingly — proves no value is a hardcoded constant.

### Implementation for User Story 1

- [X] T010 [P] [US1] Implement `backend/app/baseline/volume_baseline.py` (FR-001, FR-010): given the cleaned dataframe and a window definition from `window_definition.py`, group claims per window using `CLM_FROM_DT`, count claims per window, and explicitly include windows with `claim_count = 0` within the observed date range (no omission/interpolation). Return a `VolumeBaseline`.
- [X] T011 [P] [US1] Implement `backend/app/baseline/amount_baseline.py` (FR-002): for every `amount`-category column (identified via `load_column_categories()` filtering to `ColumnCategory.AMOUNT`), compute mean/median/std/min/max and p25/p50/p75/p95/p99 percentiles with pandas/numpy. Return a `list[AmountBaseline]`.
- [X] T012 [US1] Wire T010/T011 into `backend/app/baseline/snapshot_service.py`'s assembly function (`compute_baseline_snapshot`), populating `BaselineSnapshot.volume_baseline` and `.amount_baselines` alongside the T006 provenance fields and a fresh `snapshot_id` (uuid4) + `computed_at` timestamp.
- [X] T013 [US1] Implement `backend/app/baseline/router.py`'s `POST /baseline/compute` and `GET /baseline` endpoints (contracts/api.md): compute returns `200` with the assembled `BaselineSnapshot` or `409` on `BaselineInputUnavailableError`; `GET /baseline` returns the most recently persisted snapshot or `404` if none exists yet. Persist via a `snapshot_log.py` write/read pair modeled on `app.quality.quality_results_log` (write to `data/reports/baseline_snapshot.json`, overwrite-on-write like Phase 3's precedent).
- [X] T014 [US1] Wire `baseline_router` into `backend/app/main.py`'s router list (currently commented out at line 18-21 as a placeholder), matching the `data_engineering_router`/`quality_router` inclusion pattern.

**Checkpoint**: User Story 1 is independently functional — `POST /baseline/compute` then `GET /baseline` returns real volume + amount statistics matching Section 2.2.

---

## Phase 4: User Story 2 - Data-health baseline (Priority: P1)

**Goal**: Record historical missingness-rate-per-column, duplicate rate, and categorical/status distributions, sourced from Phase 3's quality results rather than re-derived independently.

**Independent Test**: Confirm the baseline's duplicate rate and per-column missingness rates match Phase 3's `quality_results.json` MissingRate/DuplicateRate checks on the same batch, and that `PTNT_DSCHRG_STUS_CD`'s distribution baseline reflects its near-constant real distribution.

### Tests for User Story 2

- [X] T015 [P] [US2] Write `backend/tests/baseline/test_data_health_baseline.py`: given a fixture `quality_results.json`-shaped input (file-level `MISSING_RATE`/`DUPLICATE_RATE` `ExpectationCheckResult`s) and a small cleaned-data fixture, assert `DataHealthBaseline.historical_duplicate_rate` matches the check's `computed_rate_or_count` exactly (not independently recomputed to a different figure) and that `categorical_distributions["PTNT_DSCHRG_STUS_CD"]` reflects the fixture's real value counts.

### Implementation for User Story 2

- [X] T016 [US2] Implement `backend/app/baseline/data_health_baseline.py` (FR-003, FR-004): read the historical missingness/duplicate figures from the `(QualityScoreResult, list[ExpectationCheckResult])` tuple returned by `read_quality_results()` (filtering `ExpectationType.MISSING_RATE`/`DUPLICATE_RATE` checks; per-column missing rate derived from the cleaned dataframe's own `isna()` counts if Phase 3 doesn't expose it per-column, cross-checked against Phase 3's file-level figure per research.md's fallback note), and compute the categorical distribution (`value -> count`) for `PTNT_DSCHRG_STUS_CD` at minimum from the cleaned dataframe directly. Return a `DataHealthBaseline`.
- [X] T017 [US2] Wire T016 into `snapshot_service.py`'s `compute_baseline_snapshot`, populating `BaselineSnapshot.data_health_baseline`, and raise `BaselineInputUnavailableError` up front (already in T005) if `quality_results.json` isn't available so this story's dependency on Phase 3 is enforced at the same 409 boundary as US1's Phase 2 dependency.

**Checkpoint**: User Stories 1 AND 2 both work independently — `GET /baseline` now also exposes historical data-health figures traceable to Phase 3's own numbers.

---

## Phase 5: User Story 3 - Length-of-stay baseline (Priority: P2)

**Goal**: Compute a length-of-stay distribution baseline (`NCH_BENE_DSCHRG_DT` − `CLM_ADMSN_DT`) as the duration signal, explicitly excluding and counting claims with missing/invalid dates, with no processing-time/SLA field anywhere in the output.

**Independent Test**: Confirm the baseline includes length-of-stay mean/median/percentiles computed from the two admission/discharge date columns, that claims with a missing/invalid date on either side are excluded with the exclusion count reported, and that no field named or semantically equivalent to "processing time"/"SLA"/"turnaround" appears anywhere in the full snapshot output.

### Tests for User Story 3

- [X] T018 [P] [US3] Write `backend/tests/baseline/test_length_of_stay_baseline.py` (per plan.md's Testing section, SC-004): fixture with a mix of valid claims and claims missing `CLM_ADMSN_DT` or `NCH_BENE_DSCHRG_DT`; assert excluded claims are absent from the mean/median/percentile computation, `claims_excluded_missing_dates` equals the exact injected count, and `claims_included` + `claims_excluded_missing_dates` equals the fixture's total row count.
- [X] T019 [P] [US3] Write `backend/tests/baseline/test_no_sla_field.py` (SC-005): assemble a full `BaselineSnapshot` from a fixture, serialize it (`model_dump_json`), lowercase it, and assert `"processing_time"`, `"sla"`, and `"turnaround"` are absent anywhere in the blob — this is the automated end-to-end counterpart to quickstart.md's manual `curl | python` check.

### Implementation for User Story 3

- [X] T020 [US3] Implement `backend/app/baseline/length_of_stay_baseline.py` (FR-005): compute `(NCH_BENE_DSCHRG_DT - CLM_ADMSN_DT).days` per claim from the cleaned dataframe's parsed date columns; exclude any claim where either date is missing/unparseable; compute mean/median/p25/p50/p75/p95/p99 over the included claims only; return a `LengthOfStayBaseline` with `claims_included` and `claims_excluded_missing_dates` as first-class fields. MUST NOT read or reference `NCH_WKLY_PROC_DT`/`FI_CLM_PROC_DT` anywhere (FR-006).
- [X] T021 [US3] Wire T020 into `snapshot_service.py`'s `compute_baseline_snapshot`, populating `BaselineSnapshot.length_of_stay_baseline`, completing the full snapshot assembly (all four sub-baselines + provenance).
- [X] T022 [US3] Implement `backend/app/baseline/router.py`'s `GET /baseline/history` endpoint (contracts/api.md): returns provenance-only fields (`snapshot_id`, `source_file`, `source_row_count`, `computed_at`) for every persisted snapshot. Extend `snapshot_log.py`'s persistence to append (not overwrite) each computed snapshot to a list in `baseline_snapshot.json` (or a companion history file) so `/baseline/history` has more than one entry across repeated `POST /baseline/compute` calls, supporting FR-008's recompute-without-code-changes requirement.

**Checkpoint**: All three user stories are independently functional. Full `BaselineSnapshot` includes volume, amount, data-health, and length-of-stay baselines with provenance, and `/baseline/history` lists prior computations.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the feature end-to-end against the full historical file and close out spec-level guarantees that span multiple stories.

- [X] T023 [P] Run `backend/tests/baseline/` against the full 58,066-row `data/cleaned/inpatient_cleaned.csv` (not just fixtures) and confirm `CLM_PMT_AMT` mean/median/std fall within tolerance of MVP_CONTEXT.md Section 2.2's documented figures (SC-001), documenting any Phase 2 cleaning-driven deltas (e.g., excluded duplicates) in a short note in `backend/app/baseline/__init__.py` or a code comment on the assembly function.
- [X] T024 Execute quickstart.md's four manual verification steps (compute, verify amount stats, verify no SLA field, verify length-of-stay exclusion reporting) against a running local server to confirm the contracts/api.md endpoints behave as documented end-to-end.
- [X] T025 [P] Re-read `data-model.md`'s validation rule ("No field anywhere in `BaselineSnapshot` or its sub-entities is named or semantically equivalent to processing time/SLA/turnaround") against the final `backend/app/baseline/schemas.py` field list as a manual audit, independent of T019's automated check.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup (needs `schemas.py` for T006's `BaselineSnapshot`-shaped provenance) — BLOCKS all user stories.
- **User Story 1 (Phase 3, P1)**: Depends on Foundational only.
- **User Story 2 (Phase 4, P1)**: Depends on Foundational only; independent of US1 (different sub-entity, different source file). Can run in parallel with US1 if staffed separately, though T014 (router wiring) is a natural serialization point since both stories touch `router.py`/`snapshot_service.py`.
- **User Story 3 (Phase 5, P2)**: Depends on Foundational only; independent of US1/US2's logic, though T021 touches the same `snapshot_service.py` assembly function as T012/T017.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- US1, US2, US3 are each independently computable and testable (spec's Independent Test criteria) — none reads another story's output. They share only the Foundational input-loading/provenance layer and converge in `snapshot_service.py`'s single assembly function and `router.py`'s single router, which is why T012/T017/T021 (and T013/T022) should be applied sequentially even though the underlying `*_baseline.py` computation files (T010, T011, T016, T020) are parallelizable.

### Within Each User Story

- Tests before implementation (T007-T009 before T010-T014; T015 before T016-T017; T018-T019 before T020-T022).
- `*_baseline.py` computation modules before their `snapshot_service.py` wiring.
- Router endpoints after the snapshot service they call.

### Parallel Opportunities

- T002 and T003 (Setup) can run in parallel.
- T006 (Foundational) can run in parallel with T004/T005 once T005's function signature is settled.
- T007, T008 (US1 tests) in parallel; T010, T011 (US1 implementation) in parallel.
- T015 (US2) has no sibling test to parallelize against but can run in parallel with US1's entire phase once Foundational is done.
- T018, T019 (US3 tests) in parallel; US3's phase can run in parallel with US1 and US2's phases once Foundational is done.
- T023 and T025 (Polish) in parallel.

---

## Parallel Example: User Story 1

```bash
# Launch both US1 tests together:
Task: "Write backend/tests/baseline/test_volume_baseline.py"
Task: "Write backend/tests/baseline/test_amount_baseline.py"

# Launch both US1 computation modules together:
Task: "Implement backend/app/baseline/volume_baseline.py"
Task: "Implement backend/app/baseline/amount_baseline.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1 — volume + amount baseline).
3. **STOP and VALIDATE**: `POST /baseline/compute` then `GET /baseline`, confirm `CLM_PMT_AMT` stats against Section 2.2.
4. This alone unblocks Phase 5/7/8's amount- and volume-deviation features even before US2/US3 land.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 (volume/amount) → test independently → this is the MVP.
3. US2 (data-health) → test independently → adds missingness/duplicate/status baselines.
4. US3 (length-of-stay) → test independently → completes the full `BaselineSnapshot` and closes out FR-006/SC-005's SLA-field prohibition end-to-end.
5. Polish → full-file validation against Section 2.2 ground truth + quickstart.md walkthrough.

### Parallel Team Strategy

With multiple developers, once Foundational (Phase 2) is done: Developer A takes US1, Developer B takes US2, Developer C takes US3. All three converge on `snapshot_service.py`'s assembly function and `router.py` — apply their wiring tasks (T012/T017/T021, T013/T022) in priority order (P1s before P2) to avoid merge churn on those two shared files.
