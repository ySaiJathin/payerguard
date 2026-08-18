---

description: "Task list template for feature implementation"
---

# Tasks: Quality Validation Layer

**Input**: Design documents from `/specs/003-quality-validation-layer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md (all present); Phase 1 (`001-data-profiling-foundation`) and Phase 2 (`002-cleaning-standardization`) implemented — `data/reports/column_categories.json`, `data/reports/profiling_report.json`, and `data/cleaned/inpatient_cleaned.csv` must exist before `POST /quality/validate` can run.

**Tests**: Included — plan.md's Technical Context lists specific pytest fixtures (legitimately-high-missingness column, negative-amount cell, determinism re-run) and explicit test files under Project Structure.

**Organization**: Tasks are grouped by user story. US1 (composite score) is implemented as a pure function first, tested against hand-built `ExpectationCheckResult` fixtures so its correctness doesn't depend on Great Expectations executing correctly. US2 (category suites, also P1) then produces the real check results that feed US1's function in the full pipeline. US3 (P2) adds persistence/query and the freshness check, then Polish wires the orchestrator end-to-end.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

New module alongside Phases 1-2: `backend/app/quality/`, `backend/app/quality/expectations/`, `backend/tests/quality/`, `data/reports/quality_results.json`.

---

## Phase 1: Setup

- [ ] T001 Create `backend/app/quality/__init__.py`, `backend/app/quality/expectations/__init__.py`, and `backend/tests/quality/__init__.py` package skeletons

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 [P] Add `ExpectationType`, `Band` enums and `ExpectationCheckResult`, `QualityScoreResult`, `CompletenessCalibrationEntry` Pydantic models (fields per data-model.md; reuse `ColumnCategory` from `app.data_engineering.schemas`) to `backend/app/quality/schemas.py`
- [ ] T003 [P] Create fixtures reusing Phase 1/2's 9-column schema: a small cleaned-batch CSV with one column at legitimately-high documented missingness, one negative `CLM_PMT_AMT` cell, one out-of-range date, one unrecognized categorical code, and a `CLM_ID` that repeats across two line-item rows (multi-line claim) in `backend/tests/fixtures/quality_cleaned_sample.csv`; a matching `backend/tests/fixtures/quality_column_categories.json`; and a matching `backend/tests/fixtures/quality_profiling_report.json` (with realistic `missing_pct`/`unique_claim_count` values consistent with the CSV)
- [ ] T004 [US-shared] Implement `data_loader.py`: `load_cleaned_batch(path, categories) -> pd.DataFrame` reading the cleaned CSV with an explicit dtype map (string for `identifier`/`categorical_code`/`diagnosis_procedure_code`, numeric for `amount`/`utilization_duration`, string for `date`) so numeric-looking identifier strings (e.g. `BENE_ID`) don't get re-inferred as ints on CSV round-trip; raises `QualityInputUnavailableError` if the file is missing (FR-012), in `backend/app/quality/data_loader.py` (depends on T002)

**Checkpoint**: Foundation ready.

---

## Phase 3: User Story 1 - Compute a real, deterministic 0-100 quality score (Priority: P1) 🎯 MVP

**Goal**: A pure, recomputable composite score function over persisted check results.

**Independent Test**: Feed `compute_composite_score` a hand-built `ExpectationCheckResult[]` and weight config; confirm the returned `composite_score` equals the documented weighted-proportion formula applied by hand to those same inputs.

### Tests for User Story 1

- [ ] T005 [P] [US1] Unit tests for `bands.py`: `classify_missing_rate` boundaries (<2 PASS, 2-5 WARNING, >5 CRITICAL) and `classify_duplicate_rate` boundaries (0 PASS, 0-1 WARNING, >1 CRITICAL) per MVP_CONTEXT.md 3.1, in `backend/tests/quality/test_bands.py`
- [ ] T006 [P] [US1] Unit tests for `scoring_service.compute_composite_score`: recomputing the score by hand from a fixed `ExpectationCheckResult[]` + `weights_used` yields an exact match (SC-001); `contributing_check_ids` exactly equals the input check IDs (SC-005); a weight config that would push the score outside [0,100] is clamped and flagged as a configuration error rather than silently accepted (Edge Cases), in `backend/tests/quality/test_scoring_service.py`

### Implementation for User Story 1

- [ ] T007 [US1] Implement `bands.py`: `classify_missing_rate(pct) -> Band`, `classify_duplicate_rate(pct) -> Band` using the exact MVP_CONTEXT.md 3.1 bands, in `backend/app/quality/bands.py` (depends on T002)
- [ ] T008 [US1] Implement `scoring_service.py` part 1: `compute_composite_score(check_results, weights) -> QualityScoreResult` as a pure function (`score = Σ(category_weight × category_pass_proportion)`, clamped to [0,100], raising a config error if weights don't sum sensibly) and `compute_file_level_checks(df) -> list[ExpectationCheckResult]` implementing the exact MissingRate/DuplicateRate formulas (FR-009) via `bands.py`, in `backend/app/quality/scoring_service.py` (depends on T007)

**Checkpoint**: User Story 1 functional standalone — composite scoring is correct and recomputable independent of Great Expectations.

---

## Phase 4: User Story 2 - Run category-appropriate expectation suites (Priority: P1)

**Goal**: Each of the six column categories gets real, category-appropriate Great Expectations checks executed against the cleaned batch, producing real `ExpectationCheckResult`s.

**Independent Test**: Run suite execution against the T003 fixture; confirm `CLM_ID` gets a claim-grain cardinality check, every `amount` column gets a ≥0 validity check, every `date` column gets a range+format check, and every `categorical_code`/`diagnosis_procedure_code` column gets a code-set + calibrated-completeness check.

### Tests for User Story 2

- [ ] T009 [P] [US2] Unit tests for `completeness_calibration.py`: a column with real observed missingness above the universal CRITICAL band (from the T003 profiling fixture) gets a `CompletenessCalibrationEntry` with `source_note` referencing the profiling report; a low-missingness column gets no override entry, in `backend/tests/quality/test_completeness_calibration.py`
- [ ] T010 [P] [US2] Unit tests for `suite_builder.py` + `expectations/*` against the T003 fixture: all six categories produce at least one suite/check (SC-002); `CLM_ID`'s cardinality check's observed distinct count matches the fixture's `unique_claim_count`; the negative-amount cell trips a CRITICAL validity check; the out-of-range date trips a range check; the unrecognized code trips a code-set check; the calibrated column's completeness check is not CRITICAL despite high missingness (SC-003), in `backend/tests/quality/test_suite_builder.py`

### Implementation for User Story 2

- [ ] T011 [US2] Implement `completeness_calibration.py`: `build_calibration_table(profiling_report) -> dict[str, CompletenessCalibrationEntry]` — for every column whose `ColumnProfile.missing_pct` exceeds the universal CRITICAL threshold (5%), create an override entry with `expected_max_missing_pct = min(100, missing_pct + slack)` (documented slack constant) and `source_note` citing the profiling report; columns at or below the threshold get no entry, in `backend/app/quality/completeness_calibration.py` (depends on T002)
- [ ] T012 [US2] Implement `expectations/completeness.py`: adds `ExpectColumnValuesToNotBeNull` per column to a suite (mostly-threshold derived from the calibration table when present, else the universal 2%/5% bands), and `extract_results(validation_result, ...)` mapping GX's `missing_percent` into `ExpectationCheckResult`s with band reclassified via the calibrated-vs-universal logic (PASS at/under threshold, WARNING up to 1.5x, CRITICAL beyond), in `backend/app/quality/expectations/completeness.py` (depends on T002, T011)
- [ ] T013 [P] [US2] Implement `expectations/uniqueness.py`: adds `ExpectColumnUniqueValueCountToBeBetween(column="CLM_ID", min_value=n, max_value=n)` where `n` is the profiling report's `unique_claim_count` (FR-002), and `extract_results` mapping the observed distinct count into an `ExpectationCheckResult`, in `backend/app/quality/expectations/uniqueness.py` (depends on T002)
- [ ] T014 [P] [US2] Implement `expectations/validity.py`: adds `ExpectColumnValuesToBeBetween(min_value=0)` per `amount` column (FR-003) and `ExpectColumnValuesToBeInSet(value_set=<observed values in this batch>)` per `categorical_code`/`diagnosis_procedure_code` column (FR-006), and `extract_results` mapping GX's `unexpected_percent` into `ExpectationCheckResult`s, in `backend/app/quality/expectations/validity.py` (depends on T002)
- [ ] T015 [P] [US2] Implement `expectations/range_checks.py`: for `date` columns, builds a parsed-datetime copy of the column (GX's between-expectation requires matching dtypes, not raw ISO strings) and adds `ExpectColumnValuesToBeBetween` using the batch's own observed min/max plus the Phase 2 365-day slack, plus `ExpectColumnValuesToMatchRegex(r"^\d{4}-\d{2}-\d{2}$")` on the original string column for format (FR-004/FR-005); for `utilization_duration` columns, adds a non-negative + observed-max-based upper-bound `ExpectColumnValuesToBeBetween`; `extract_results` maps both into `ExpectationCheckResult`s, in `backend/app/quality/expectations/range_checks.py` (depends on T002)
- [ ] T016 [US2] Implement `suite_builder.py`: `build_suites(context, categories, calibration, df) -> dict[ColumnCategory, gx.ExpectationSuite]`, wiring T012-T015 so each category's suite gets exactly the expectation types applicable to it (identifier -> completeness [+ uniqueness for `CLM_ID`]; date -> completeness + range + dtype; amount -> completeness + validity + dtype; utilization_duration -> completeness + range; categorical_code/diagnosis_procedure_code -> completeness + code-set validity) per FR-001, in `backend/app/quality/suite_builder.py` (depends on T011-T015)
- [ ] T017 [US2] Implement `scoring_service.py` part 2: `run_category_suites(context, df, suites) -> list[ExpectationCheckResult]` executing each category's suite once via `batch.validate(suite)` and collecting results through each `expectations/*.extract_results`, in `backend/app/quality/scoring_service.py` (depends on T008, T016)

**Checkpoint**: User Stories 1 and 2 both work — real GX-backed check results feed a correct, recomputable composite score.

---

## Phase 5: User Story 3 - Persist per-check results for downstream consumption (Priority: P2)

**Goal**: Every individual check result (plus the freshness check) is persisted and independently queryable.

**Independent Test**: Run the full validation once; confirm every check (completeness, uniqueness, validity, dtype, range, code-set, freshness) is a separately retrievable record, and that `GET /quality/results`/`GET /quality/checks/{check_id}` work against the persisted file.

### Tests for User Story 3

- [ ] T018 [P] [US3] Unit tests for `expectations/freshness.py`: a batch whose source file mtime falls inside the configured ingestion window -> PASS; a stale mtime -> WARNING/CRITICAL per the documented window, in `backend/tests/quality/test_freshness.py`
- [ ] T019 [P] [US3] Unit tests for `quality_results_log.py`: write/read round-trip preserves both `QualityScoreResult` and `ExpectationCheckResult[]`; a second write overwrites rather than appends (idempotency, mirroring Phase 2's `quality_issue_log.py` precedent); `find_check(check_id)` returns `None` for an unknown ID, in `backend/tests/quality/test_quality_results_log.py`

### Implementation for User Story 3

- [ ] T020 [US3] Implement `expectations/freshness.py`: a single file-level check (column_name=null) comparing the cleaned batch file's mtime against a configured expected ingestion window (documented as an mtime-based proxy per research.md, since no ingestion-timestamp field exists yet), classified PASS/WARNING/CRITICAL, in `backend/app/quality/expectations/freshness.py` (depends on T002)
- [ ] T021 [US3] Implement `quality_results_log.py`: `write_quality_results(score_result, check_results)`/`read_quality_results()`/`find_check(check_id)` persisting `data/reports/quality_results.json` in the `{"quality_score_result": ..., "check_results": [...]}` shape from contracts/api.md, overwriting on each write, in `backend/app/quality/quality_results_log.py` (depends on T002)

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T022 Implement `scoring_service.run_validation(batch_source="raw") -> QualityScoreResult` orchestrator tying together: load categories + profiling report + cleaned df (T004) -> calibration (T011) -> suites (T016) -> execute (T017) -> file-level MissingRate/DuplicateRate (T008) -> freshness (T020) -> `compute_composite_score` (T008) -> persist (T021); raises `QualityInputUnavailableError` if no cleaned batch exists (FR-012), in `backend/app/quality/scoring_service.py` (depends on T017, T020, T021)
- [ ] T023 Implement `POST /quality/validate` (`409` on `QualityInputUnavailableError`), `GET /quality/results` (optional `band`/`category` filters, `404` if no run yet), and `GET /quality/checks/{check_id}` (`404` if unknown) in `backend/app/quality/router.py`; wire the router into `backend/app/main.py`
- [ ] T024 [P] Run `quickstart.md` end-to-end against the real `data/cleaned/inpatient_cleaned.csv`, and confirm SC-001 through SC-005 all hold

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)**: blocks all stories.
- **US1 (Phase 3)**: depends on Foundational only (`bands.py`/`scoring_service.compute_composite_score` are pure functions, independently testable without GX).
- **US2 (Phase 4)**: depends on Foundational; `scoring_service.py` part 2 (T017) depends on part 1 (T008) existing.
- **US3 (Phase 5)**: depends on Foundational only for its two modules (T020/T021 touch different files than US1/US2 and can be built in parallel with Phases 3-4).
- **Polish (Phase 6)**: depends on all three stories (T022 wires US1+US2+US3 together).

### Parallel Opportunities

- T002/T003 (Foundational, different files).
- T005/T006 (US1 tests, different files).
- T009/T010 (US2 tests, different files).
- T013/T014/T015 (US2 implementation, different files, no dependency on each other) can be built in parallel; only `suite_builder.py` (T016) and `scoring_service.py` part 2 (T017) are sequential.
- T018/T019 (US3 tests and implementation, different files, no dependency on US1/US2) can be built alongside Phases 3-4.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Setup + Foundational
2. US1 — composite scoring is correct and recomputable, tested standalone against hand-built check results
3. **STOP and VALIDATE**: run T006 and confirm the formula recomputes exactly

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → validate recomputability (SC-001) → demo (the score math is correct in isolation)
3. US2 → validate real GX suites produce the right checks (SC-002, SC-003) → demo
4. US3 → validate persistence/query independence (SC-005) → demo
5. Polish → wire orchestrator + router, run full quickstart (SC-001 through SC-005 against the real cleaned batch)

## Notes

- Great Expectations' `ExpectColumnValuesToBeBetween` requires matching Python types between column values and bounds — string ISO dates must be parsed to `pd.Timestamp` before that expectation runs, or GX raises a `MetricResolutionError` instead of computing a result. Confirmed during setup.
- No individual check's band is ever assigned independently of its computed rate/count and threshold (constitution Principle II, FR-013) — every `expectations/*.py` must derive `band` from `computed_rate_or_count` + `threshold_used`, never hardcode it.
- Idempotency of persistence (T021): every write overwrites prior output rather than appending, mirroring Phase 2's `quality_issue_log.py`.
- Commit after each task or logical group; validate at each checkpoint before moving on.
