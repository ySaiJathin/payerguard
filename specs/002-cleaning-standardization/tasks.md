---

description: "Task list template for feature implementation"
---

# Tasks: Cleaning & Standardization

**Input**: Design documents from `/specs/002-cleaning-standardization/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md (all present); Phase 1 (`001-data-profiling-foundation`) implemented — `data/reports/column_categories.json` must exist before `POST /data-engineering/clean` can run

**Tests**: Included — plan.md's Technical Context specifies pytest with a synthetic dirty fixture, and explicitly lists the test files under Project Structure.

**Organization**: Tasks are grouped by user story (spec.md). US1 and US2 are both P1 and implemented in the same orchestrator pass (dtype/date conversion and its audit trail are produced together), so their implementation tasks share `cleaning_service.py` sequentially rather than in parallel — each story still has its own independently-checkable test assertions.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Same backend service as Phase 1: `backend/app/data_engineering/`, `backend/tests/data_engineering/`, `data/`.

---

## Phase 1: Setup

- [X] T001 Create output directory `data/cleaned/.gitkeep` in repo root

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Add `QualityIssueRecord`, `SchemaValidationResult`, and `CleaningRunSummary` Pydantic models (fields per data-model.md) to `backend/app/data_engineering/schemas.py`
- [X] T003 [P] Create a synthetic "dirty" fixture reusing the Phase 1 fixture's 9-column schema (`BENE_ID`, `CLM_ID`, `CLM_FROM_DT`, `CLM_THRU_DT`, `CLM_PMT_AMT`, `CLM_IP_ADMSN_TYPE_CD`, `PRNCPAL_DGNS_CD`, `OT_PHYSN_UPIN`, `CLM_LINE_NUM`), containing: one exact-duplicate row pair, one negative `CLM_PMT_AMT`, one malformed/unparseable date string, one missing cell in a non-`OT_PHYSN_UPIN` column, and one `CLM_IP_ADMSN_TYPE_CD` value outside `{1,2,3}`, in `backend/tests/fixtures/inpatient_dirty_sample.csv`

**Checkpoint**: Foundation ready.

---

## Phase 3: User Story 1 - Produce a standardized, type-correct dataset (Priority: P1) 🎯 MVP

**Goal**: Every column converted to its category-implied dtype; every date in ISO 8601.

**Independent Test**: Run cleaning against `data/raw/inpatient.csv`; assert every date column contains only ISO-format values and every amount/utilization column is numeric.

### Tests for User Story 1

- [X] T004 [P] [US1] Unit tests for `date_standardization.py`: `DD-Mon-YYYY` → ISO 8601 for a valid date, and an unparseable string is flagged (not guessed) in `backend/tests/data_engineering/test_date_standardization.py`
- [X] T005 [P] [US1] Unit tests for `cleaning_service.py` dtype conversion and schema validation: amount/utilization columns numeric, identifier/categorical/diagnosis columns string, date columns ISO 8601, and a schema mismatch (wrong column count) fails fast, against the T003 fixture, in `backend/tests/data_engineering/test_cleaning_service.py`

### Implementation for User Story 1

- [X] T006 [US1] Implement `date_standardization.py`: parse observed `DD-Mon-YYYY` values to ISO 8601 (`YYYY-MM-DD`), leaving unparseable values as null-equivalent and returning enough detail (old value, new value, per-cell outcome) for the caller to build audit records, in `backend/app/data_engineering/date_standardization.py`
- [X] T007 [US1] Implement `dtype_conversion.py`: load `data/reports/column_categories.json` (Phase 1's categorization output — `expected_column_count` and per-column categories are read from it, never hardcoded) and coerce each column per its category (`amount`/`utilization_duration` → numeric via `pd.to_numeric`; `date` → delegated to `date_standardization.py`; `identifier`/`categorical_code`/`diagnosis_procedure_code` → string), leaving missing cells null, in `backend/app/data_engineering/dtype_conversion.py` (depends on T002, T006)
- [X] T008 [US1] Implement `cleaning_service.py` orchestrator, part 1: load `column_categories.json` and validate the input's column set/count against it into a `SchemaValidationResult` (fail fast — raise a distinct, catchable error — on mismatch, per FR-001/Edge Cases), then run `dtype_conversion.py` over the loaded source dataframe, in `backend/app/data_engineering/cleaning_service.py` (depends on T007)

**Checkpoint**: User Story 1 functional — a typed, ISO-dated dataset can be produced (audit trail wired in next).

---

## Phase 4: User Story 2 - Preserve a full correction audit trail (Priority: P1)

**Goal**: Every actual value change (and every missing cell) gets exactly one `QualityIssueRecord`; unchanged cells get none.

**Independent Test**: Clean the T003 fixture; confirm a `(original_value, cleaned_value, quality_issue)` record exists per known bad value, with the record count exactly matching changed-cell count.

### Tests for User Story 2

- [X] T009 [US2] Extend `test_cleaning_service.py` with audit-trail assertions: a `date_format_standardized` record with the exact original/cleaned values for a reformatted date; zero records for cells that didn't change; a `missing_value` record for every missing cell; and total record count for changed/missing cells exactly equals the count of cells that actually changed or were missing (SC-002), in `backend/tests/data_engineering/test_cleaning_service.py`

### Implementation for User Story 2

- [X] T010 [US2] Implement `quality_issue_log.py`: accumulate `QualityIssueRecord` entries in memory during a run and persist/read them as `data/reports/quality_issues.json`, overwriting on each write (never appending — required for idempotency, FR-009), in `backend/app/data_engineering/quality_issue_log.py` (depends on T002)
- [X] T011 [US2] Wire audit-record emission into `cleaning_service.py`'s dtype/date pass from T008: emit exactly one record per cell that actually changed (`date_format_standardized`, `date_unparseable`) and one `missing_value` record per missing cell, and never a record for an unchanged cell, in `backend/app/data_engineering/cleaning_service.py` (depends on T008, T010)

**Checkpoint**: User Stories 1 and 2 both work independently — cleaned output plus a trustworthy audit trail.

---

## Phase 5: User Story 3 - Detect duplicates and invalid values without silent deletion (Priority: P2)

**Goal**: Full-row duplicates and invalid values are flagged and excluded/preserved per FR-004/FR-005, never silently dropped or guessed.

**Independent Test**: Clean a fixture with an injected duplicate row and an injected negative amount; confirm both are flagged with the correct `quality_issue` label and neither is silently dropped from the audit trail.

### Tests for User Story 3

- [X] T012 [P] [US3] Unit tests for `duplicate_detection.py`: an exact-duplicate row is flagged `duplicate_row`, excluded from the deduplicated output, and still recoverable via its audit record; the real `data/raw/inpatient.csv` yields 0 duplicates (matching MVP_CONTEXT.md 2.2), in `backend/tests/data_engineering/test_duplicate_detection.py`
- [X] T013 [P] [US3] Unit tests for `invalid_value_detection.py`: a negative amount is flagged `invalid_value_negative_amount` with the original value left unchanged (not corrected); a categorical value outside the observed set is flagged `unrecognized_code`; a date outside the observed-range-plus-slack window is flagged, in `backend/tests/data_engineering/test_invalid_value_detection.py`

### Implementation for User Story 3

- [X] T014 [US3] Implement `duplicate_detection.py`: detect full-row duplicates (`DataFrame.duplicated(keep="first")`), exclude non-first occurrences from the working dataset, and emit a `duplicate_row` `QualityIssueRecord` per excluded row (original row never deleted from any source file — only excluded from the in-memory/output cleaned dataset), in `backend/app/data_engineering/duplicate_detection.py` (depends on T002)
- [X] T015 [US3] Implement `invalid_value_detection.py`: (a) amount columns must be ≥ 0, flag `invalid_value_negative_amount` otherwise; (b) date columns must fall within the observed min/max date **computed fresh from `data/raw/inpatient.csv` at run time** (never a hardcoded range, per constitution Principle II — MVP_CONTEXT.md's stated 2015-04-01..2022-10-31 was found stale during Phase 1 implementation) plus a documented ±365-day slack window, flag `date_unparseable`-adjacent `invalid_value_date_out_of_range` otherwise; (c) categorical/diagnosis columns must belong to the set of values actually observed in `data/raw/inpatient.csv` for that column (loaded fresh, not limited to Phase 1's persisted top-N), flag `unrecognized_code` otherwise — none of these corrects the value, only flags it, in `backend/app/data_engineering/invalid_value_detection.py` (depends on T002)
- [X] T016 [US3] Wire `duplicate_detection.py` and `invalid_value_detection.py` into `cleaning_service.py`'s orchestrator, and assemble the final `CleaningRunSummary` (`rows_in`, `rows_out`, `duplicate_rows_excluded`, `quality_issue_count`, `generated_at`) and persisted `data/cleaned/inpatient_cleaned.csv`, in `backend/app/data_engineering/cleaning_service.py` (depends on T011, T014, T015)

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T017 Implement `POST /data-engineering/clean` (body `{"source": "raw"|"sampled"}`, `422` on `SchemaValidationResult.passed = false`, `409` if `column_categories.json` is missing), `GET /data-engineering/quality-issues` (optional `quality_issue`/`column_name` filters, `404` if no run yet), and `GET /data-engineering/clean` (last `CleaningRunSummary`, `404` if no run yet) in `backend/app/data_engineering/router.py`
- [X] T018 [P] Run `quickstart.md` end-to-end against the real `data/raw/inpatient.csv` (date standardization, audit-trail non-fabrication check, idempotency re-run byte-comparison, `duplicate_rows_excluded == 0`) and confirm SC-001 through SC-006 all hold

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)**: blocks all stories.
- **US1 (Phase 3)**: depends on Foundational only.
- **US2 (Phase 4)**: depends on US1's `cleaning_service.py`/`dtype_conversion.py` (T008) existing — the audit trail is emitted from the same pass. Not parallel with US1's implementation tasks, though T004/T005 (US1 tests) and T009 (US2 test) can be drafted independently before either implementation lands.
- **US3 (Phase 5)**: depends on Foundational only for its own two modules (`duplicate_detection.py`, `invalid_value_detection.py` — T014/T015 touch different files than US1/US2 and can be built in parallel with Phases 3–4); wiring them into `cleaning_service.py` (T016) waits on T011.
- **Polish (Phase 6)**: depends on all three stories.

### Parallel Opportunities

- T002/T003 (Foundational).
- T004/T005 (US1 tests, different files).
- T012/T013 (US3 tests, different files).
- T014/T015 (US3 implementation, different files, no dependency on US1/US2) can be built alongside Phases 3–4 by a second implementer; only the final wiring step (T016) is sequential.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup + Foundational
2. US1 — typed, ISO-standardized dataset
3. **STOP and VALIDATE**: run T005 against the real file structure; confirm dtypes/date formats are correct

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → validate dtype/date correctness → demo
3. US2 → validate audit trail completeness/exactness (SC-002) → demo (this is the project's non-negotiable evidence trail)
4. US3 → validate duplicate/invalid flagging without silent deletion → demo
5. Polish → wire router, run full quickstart

## Notes

- No cell's missing value is ever fabricated or defaulted (constitution Principle II, FR-006, SC-005) — every implementation task that touches a missing cell must leave it null.
- Idempotency (FR-009, SC-004): every write in T010/T016 overwrites prior output rather than appending/patching.
- Commit after each task or logical group; validate at each checkpoint before moving on.
