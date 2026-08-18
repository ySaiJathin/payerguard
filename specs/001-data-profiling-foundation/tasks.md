---

description: "Task list template for feature implementation"
---

# Tasks: Data Profiling Foundation

**Input**: Design documents from `/specs/001-data-profiling-foundation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md (all present)

**Tests**: Included — plan.md's Technical Context specifies pytest with fixture-driven tests, and explicitly lists the test files under Project Structure.

**Organization**: Tasks are grouped by user story (spec.md) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

Single backend service (per plan.md Structure Decision): `backend/app/data_engineering/`, `backend/tests/`, `data/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Filesystem locations the feature reads/writes, before any code is written.

- [X] T001 Create output directories `data/reports/.gitkeep` and `data/sampled/.gitkeep`, and test directory `backend/tests/data_engineering/__init__.py`, so the feature has somewhere to write artifacts and tests have somewhere to live

**Checkpoint**: Directories exist; ready for Foundational phase.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared entities and fixture every user story's implementation and tests depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Define `ColumnProfile`, `ProfilingReport`, and `SampleManifest` Pydantic models (fields and validation rules per data-model.md, including the six-value `category` enum: `identifier`, `date`, `amount`, `utilization_duration`, `categorical_code`, `diagnosis_procedure_code`) in `backend/app/data_engineering/schemas.py`
- [X] T003 [P] Create a small synthetic pipe-delimited fixture covering an identifier column, a date column (`DD-Mon-YYYY` format), an amount column, a categorical column, a diagnosis-code-pattern column, a fully-null column, and at least one `CLM_ID` with multiple line-item rows, in `backend/tests/fixtures/inpatient_sample.csv`
- [X] T004 Scaffold `backend/app/data_engineering/router.py` with an `APIRouter` instance and no routes yet (routes are added per user story below)

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Generate the full data profiling report (Priority: P1) 🎯 MVP

**Goal**: Compute and persist a full per-column and file-level statistical profile of `data/raw/inpatient.csv`.

**Independent Test**: Run profiling against `data/raw/inpatient.csv` and confirm row count (58,066), unique `CLM_ID` count (20,867), unique `BENE_ID` count (5,699), and duplicate-row count (0) match MVP_CONTEXT.md Section 2.2 exactly.

### Tests for User Story 1

- [X] T005 [P] [US1] Unit tests for file-level and column-level statistics computation (dtype, missing count/pct, cardinality, numeric percentiles, categorical top-value frequencies, date format + min/max detection, duplicate-row detection, and the "column count ≠ 197 fails fast" and "source file missing fails fast" edge cases) against the T003 fixture, in `backend/tests/data_engineering/test_profiling_service.py`
- [X] T006 [P] [US1] Integration test asserting a profiling run against the real `data/raw/inpatient.csv` matches MVP_CONTEXT.md Section 2.2 ground truth exactly (58,066 rows, 197 columns, 20,867 unique claims, 5,699 unique beneficiaries, 0 duplicate rows), in `backend/tests/data_engineering/test_profiling_real_data.py`

### Implementation for User Story 1

- [X] T007 [US1] Implement `profiling_service.py`: read `data/raw/inpatient.csv` with `sep="|"`, validate the column count is 197 and fail fast with a clear error otherwise (FR-001, FR-013), compute file-level statistics (total rows, unique `CLM_ID`, unique `BENE_ID`, lines-per-claim mean/median, full-duplicate-row count) and per-column statistics (dtype, missing count/pct, cardinality; numeric mean/median/std/min/max/p25/p50/p75/p95/p99 for numeric columns; top value frequencies for categorical columns; observed date format + min/max for date columns), assembling a `ProfilingReport` (category left unset — populated in Phase 4), in `backend/app/data_engineering/profiling_service.py` (depends on T002)
- [X] T008 [US1] Implement `report_writer.py`: persist a `ProfilingReport` as `data/reports/profiling_report.md` (human-readable narrative) and `data/reports/profiling_report.json` (machine-readable), overwriting any prior report rather than merging/appending (spec Edge Cases), in `backend/app/data_engineering/report_writer.py` (depends on T007)
- [X] T009 [US1] Implement `POST /data-engineering/profile` (runs profiling + categorization + report_writer, returns the summary shape from contracts/api.md, `422` when the source file is missing/unreadable/malformed) and `GET /data-engineering/profile` (returns the last-persisted `ProfilingReport`, `404` if none exists yet) in `backend/app/data_engineering/router.py` (depends on T007, T008)

**Checkpoint**: User Story 1 is fully functional and independently testable (categorization added next, but profiling already runs and reports end-to-end with categories left as a placeholder until Phase 4 wires them in).

---

## Phase 4: User Story 2 - Confirm column categorization (Priority: P2)

**Goal**: Every one of the 197 columns is assigned exactly one of the six fixed categories, matching MVP_CONTEXT.md Section 2.3 for the columns it names.

**Independent Test**: Every column named in MVP_CONTEXT.md Section 2.3 receives the same category in the categorization output; every column not named there still receives exactly one category.

### Tests for User Story 2

- [X] T010 [P] [US2] Unit tests asserting: every column explicitly categorized in MVP_CONTEXT.md Section 2.3 (e.g., `CLM_ID`→identifier, `CLM_PMT_AMT`→amount, `PRNCPAL_DGNS_CD`→diagnosis_procedure_code) gets that exact category; every column in the T003 fixture gets exactly one of the six categories; a fully-null column still gets categorized rather than skipped, in `backend/tests/data_engineering/test_categorization.py`

### Implementation for User Story 2

- [X] T011 [US2] Implement `categorization.py`: a static `column_name → category` mapping seeded from MVP_CONTEXT.md Section 2.3, plus pattern rules for the repeated-slot columns not individually named there (`ICD_DGNS_CD\d+`, `ICD_DGNS_E_CD\d+`, `ICD_PRCDR_CD\d+` → `diagnosis_procedure_code`; `PRCDR_DT\d+` → `date`; `CLM_PPS_CPTL_*`/`CLM_TOT_PPS_CPTL_*` → `amount`) with a documented default for any remaining column, covering all 197 real columns, in `backend/app/data_engineering/categorization.py` (depends on T002)
- [X] T012 [US2] Wire `categorization.py` into `profiling_service.py` so each `ColumnProfile.category` is populated, and persist `data/reports/column_categories.json` via `report_writer.py` (depends on T007, T008, T011)

**Checkpoint**: User Stories 1 and 2 both work independently — the report now carries real categories.

---

## Phase 5: User Story 3 - Produce a fast-iteration working sample (Priority: P3)

**Goal**: A smaller, claim-consistent, reproducible sample of `inpatient.csv` under `data/sampled/`, with the raw file left untouched.

**Independent Test**: Generate the sample; confirm `data/raw/inpatient.csv` is byte-identical before/after, and every `CLM_ID` in the sample has 100% of its line items included.

### Tests for User Story 3

- [X] T013 [P] [US3] Unit tests for `sampling_service.py`: same `seed`/`target_claim_fraction` run twice yields an identical claim set and file contents; a `target_claim_fraction` that would select zero claims raises a clear configuration error rather than producing an empty file; `data/raw/inpatient.csv` checksum is unchanged before/after sampling; no claim's line items are split across the sample boundary, in `backend/tests/data_engineering/test_sampling_service.py`

### Implementation for User Story 3

- [X] T014 [US3] Implement `sampling_service.py`: select `target_claim_fraction` (default 0.10) of distinct `CLM_ID` values using a seeded RNG (default seed 42), include every line-item row for each selected claim, write the result to `data/sampled/inpatient_sample.csv` without ever modifying/moving/deleting `data/raw/inpatient.csv`, raise a clear error when the configured fraction would select zero claims, and return a `SampleManifest`, in `backend/app/data_engineering/sampling_service.py` (depends on T002)
- [X] T015 [US3] Implement `POST /data-engineering/sample` accepting optional `seed`/`target_claim_fraction`, returning the `SampleManifest` JSON body, `422` on a degenerate fraction or missing source file, in `backend/app/data_engineering/router.py` (depends on T014)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Wire the feature into the app and validate it end-to-end against the real dataset.

- [X] T016 Wire `data_engineering_router` into `backend/app/main.py`'s router include list, following the existing commented-out pattern for the other domain routers
- [X] T017 [P] Run `quickstart.md` end-to-end against the real `data/raw/inpatient.csv` (`POST`/`GET /data-engineering/profile`, `POST /data-engineering/sample`, reproducibility re-run, claim-consistency check) and confirm SC-001 through SC-005 all hold

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational only. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational (T002) and on US1's `profiling_service.py`/`report_writer.py` (T007, T008) existing to wire categories into — cannot be fully implemented in parallel with US1, though its test (T010) and mapping (T011) can be written independently.
- **User Story 3 (Phase 5)**: Depends on Foundational (T002) only — fully independent of US1/US2, can be implemented in parallel with either.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Within Each User Story

- Tests (T005/T006, T010, T013) should be written and failing before their corresponding implementation tasks.
- Schemas (T002) before service logic.
- Service logic before router endpoints.

### Parallel Opportunities

- T002 and T003 (Foundational) can run in parallel.
- T005 and T006 (US1 tests) can run in parallel.
- T010 (US2 test) can be written in parallel with US1 implementation, but T011/T012 implementation waits on T007/T008.
- T013/T014/T015 (US3, entirely independent of US1/US2) can be built in parallel with Phase 3/4 by a second implementer.

---

## Parallel Example: Foundational + User Story 3 run alongside User Story 1

```bash
# Foundational, in parallel:
Task: "Define ColumnProfile/ProfilingReport/SampleManifest in backend/app/data_engineering/schemas.py"
Task: "Create synthetic fixture in backend/tests/fixtures/inpatient_sample.csv"

# Once Foundational is done, US1 and US3 can proceed in parallel (different files):
Task: "Implement profiling_service.py"       # US1
Task: "Implement sampling_service.py"        # US3
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 — profiling report generation and persistence
4. **STOP and VALIDATE**: run T006 against the real `inpatient.csv` and confirm ground-truth statistics match exactly (SC-003)

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate against real data → MVP demo (a real, computed profiling report)
3. User Story 2 → validate categorization coverage → demo (every column categorized)
4. User Story 3 → validate reproducibility + claim consistency → demo (fast local sample)
5. Polish → wire into `main.py`, run full quickstart

## Notes

- [P] tasks touch different files with no unmet dependencies.
- Every reported statistic must be computed at run time from the current `inpatient.csv` — never hardcoded (constitution Principle II, FR-012). Tests should assert against MVP_CONTEXT.md's documented ground truth, not against literals baked into the implementation.
- Commit after each task or logical group; stop at each checkpoint to validate that story independently before moving on.
