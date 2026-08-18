---

description: "Task list for Feature Engineering (005)"
---

# Tasks: Feature Engineering

**Input**: Design documents from `/specs/005-feature-engineering/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: plan.md's Testing section explicitly calls out required pytest tests (missing-input-produces-null for SC-001, unseen-category encoding for SC-005, schema/contract test for SC-004) plus deviation/window-completeness coverage implied by SC-002/SC-003 — test tasks are included per user story.

**Organization**: Tasks are grouped by user story (US1 claim-level, US2 window-level, US3 deferred `anomaly_count` schema slot) to enable independent implementation and testing of each.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

Backend module at `backend/app/features/`, tests at `backend/tests/features/`, file outputs at `data/features/` — per plan.md's Project Structure.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `features` module skeleton so subsequent tasks have somewhere to land.

- [ ] T001 Create `backend/app/features/` package skeleton: `__init__.py`, `claim_level/__init__.py`, `window_level/__init__.py`, and `backend/tests/features/__init__.py` (empty modules, matching plan.md's Project Structure)

**Checkpoint**: Module skeleton exists; foundational work can begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared utilities and schemas that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Extract the admission→discharge day-difference calculation currently inlined in `backend/app/baseline/length_of_stay_baseline.py` into a shared utility function `compute_length_of_stay_days(admission: pd.Series, discharge: pd.Series) -> pd.Series` in a new `backend/app/shared/length_of_stay.py` module; update `backend/app/baseline/length_of_stay_baseline.py` to call it instead of computing `(discharge - admission).dt.days` inline. No behavior change — existing `backend/tests/baseline/test_length_of_stay_baseline.py` must still pass unmodified (research.md: "Length-of-stay reuses Phase 4's exact derivation via a shared utility, not a re-implementation")
- [ ] T003 [P] Define `ClaimFeatures`, `WindowFeatures`, and `EncodingScheme` Pydantic models in `backend/app/features/schemas.py` per data-model.md's field tables (including `WindowFeatures.anomaly_count: int | None = None` and `EncodingScheme.unseen_category_policy: str`)
- [ ] T004 [P] Add `features_dir() -> Path` to `backend/app/data_engineering/paths.py`, returning `find_data_dir() / "features"`, following the existing `cleaned_dir()`/`reports_dir()` pattern

**Checkpoint**: Foundation ready — US1 and US2 can now proceed in parallel.

---

## Phase 3: User Story 1 - Compute claim-level features (Priority: P1) 🎯 MVP

**Goal**: Every cleaned claim receives a `ClaimFeatures` row (amount ratios, length-of-stay, date-derived attributes, encoded categoricals, provider frequency), with missing inputs producing explicit nulls rather than fabricated values.

**Independent Test**: Run feature engineering against Phase 2's cleaned output and confirm every claim receives the full documented feature set, with nulls (not fabricated values) for claims lacking underlying source data.

### Tests for User Story 1

- [ ] T005 [P] [US1] Test: payment-to-charge ratio is real when both inputs present, and null (not a divide-by-zero error or default) when `CLM_TOT_CHRG_AMT` is zero or missing, in `backend/tests/features/test_amount_ratios.py` (FR-001, SC-001)
- [ ] T006 [P] [US1] Test: `length_of_stay_days` matches Phase 4's shared utility output for valid dates, and is null when admission or discharge date is missing, in `backend/tests/features/test_length_of_stay_feature.py` (FR-002)
- [ ] T007 [P] [US1] Test: an encoder fit on a fixture, then applied to a claim with a category value absent from fitting, maps to the documented unknown bucket without raising and without aliasing to an existing category's code, in `backend/tests/features/test_categorical_encoding.py` (FR-004, SC-005)
- [ ] T008 [P] [US1] Test: `provider_frequency` reflects the real occurrence count/rate of a `PRVDR_NUM` in the configured historical scope (including a provider appearing only once), and is null when `PRVDR_NUM` is missing, in `backend/tests/features/test_provider_frequency.py` (FR-005)

### Implementation for User Story 1

- [ ] T009 [P] [US1] Implement `compute_amount_ratios(df: pd.DataFrame) -> pd.DataFrame` in `backend/app/features/claim_level/amount_ratios.py`: `payment_to_charge_ratio = CLM_PMT_AMT / CLM_TOT_CHRG_AMT`, null when denominator is 0/NaN or numerator is NaN (FR-001)
- [ ] T010 [US1] Implement `compute_length_of_stay_feature(df: pd.DataFrame) -> pd.Series` in `backend/app/features/claim_level/length_of_stay.py`, calling the shared `compute_length_of_stay_days` utility from T002 — no independent reimplementation of the date-difference formula (FR-002; depends on T002)
- [ ] T011 [P] [US1] Implement `compute_date_features(df: pd.DataFrame) -> pd.DataFrame` in `backend/app/features/claim_level/date_features.py`: `admission_day_of_week`, `admission_month`, `admission_year` derived from standardized ISO `CLM_ADMSN_DT`, null when the date is missing/unparseable (FR-003)
- [ ] T012 [US1] Implement `backend/app/features/claim_level/categorical_encoding.py`: `fit_encoding_scheme(df, categories) -> dict[str, EncodingScheme]` (one-hot for low-cardinality categorical columns, frequency encoding for high-cardinality categorical/diagnosis-procedure columns, per research.md's cardinality rule) and `apply_encoding_scheme(df, schemes) -> dict[str, ...]`, with every scheme's `unseen_category_policy` mapping unseen values to an explicit "unknown" bucket/sentinel — never erroring, never aliasing to an existing category (FR-004; depends on T003 for the `EncodingScheme` schema)
- [ ] T013 [P] [US1] Implement `compute_provider_frequency(df: pd.DataFrame) -> pd.Series` in `backend/app/features/claim_level/provider_frequency.py`: each claim's feature = count (or rate) of its `PRVDR_NUM` across the full historical dataframe passed in, null when `PRVDR_NUM` is missing for that claim (FR-005)
- [ ] T014 [US1] Implement `backend/app/features/claim_feature_service.py`: `compute_claim_features(df: pd.DataFrame, categories: dict) -> list[ClaimFeatures]` orchestrating T009, T010, T011, T012, T013 into one `ClaimFeatures` row per claim, keyed by `CLM_ID`, never fabricating a value for a claim missing the relevant input (FR-010; depends on T009-T013)
- [ ] T015 [US1] Implement `backend/app/features/features_log.py` with `write_claim_features(rows: list[ClaimFeatures], out_dir=None) -> Path` and `read_claim_features(out_dir=None) -> list[ClaimFeatures]`, persisting to `data/features/claim_features.csv` via `features_dir()` from T004 (depends on T004, T003)

**Checkpoint**: User Story 1 is independently functional and testable — claim-level features can be computed and persisted.

---

## Phase 4: User Story 2 - Compute window-level features from currently-available signals (Priority: P1)

**Goal**: Every processing window (Phase 4's window definition) receives a `WindowFeatures` row — claim count, amount stats, missingness/duplicate/invalid-status %, and volume/amount deviation vs. Phase 4's `BaselineSnapshot`.

**Independent Test**: Compute window-level features for the historical data and confirm volume/amount deviation values are computed relative to Phase 4's `BaselineSnapshot`, not an independently re-derived or assumed baseline.

### Tests for User Story 2

- [ ] T016 [P] [US2] Test: every window in the current run's date range — including zero-claim windows — receives a complete `WindowFeatures` row (`claim_count`, `amount_stats`, `missing_pct`, `duplicate_pct`, `invalid_status_pct` all present), in `backend/tests/features/test_window_aggregates.py` (FR-006, FR-009, SC-002)
- [ ] T017 [P] [US2] Test: `volume_deviation` and `amount_deviation` are recomputable by hand from a fixture `BaselineSnapshot` and a window's own claim data (matching by `window_id`), in `backend/tests/features/test_deviation_features.py` (FR-007, SC-003)
- [ ] T018 [P] [US2] Test: when the configured window definition doesn't match `BaselineSnapshot.volume_baseline.window_definition`, computing deviation features raises a typed mismatch error rather than silently computing a deviation, in `backend/tests/features/test_window_definition_mismatch.py` (FR-007, edge case)

### Implementation for User Story 2

- [ ] T019 [P] [US2] Implement `compute_window_aggregates(df: pd.DataFrame, categories: dict, reference_stats, window_definition=DEFAULT_WINDOW_DEFINITION) -> list[dict]` in `backend/app/features/window_level/window_aggregates.py`: reuses `app.baseline.window_definition.resolve_windows` for window boundaries (including zero-claim windows); per window computes `claim_count` (row count, same grain convention as `volume_baseline.py`), `amount_stats` (`{mean, median, std}` per AMOUNT column), `missing_pct` (overall % of null cells across the window's rows), `duplicate_pct` (`df.duplicated()` rate within the window's slice), and `invalid_status_pct` (% of the window's `PTNT_DSCHRG_STUS_CD` values not in `reference_stats.known_values`, reusing `app.data_engineering.invalid_value_detection` methodology) (FR-006, FR-009)
- [ ] T020 [US2] Implement `backend/app/features/window_level/deviation_features.py`: `compute_deviation_features(window_aggregates: list[dict], baseline: BaselineSnapshot, window_definition: str) -> dict[str, dict]` — first asserts `window_definition == baseline.volume_baseline.window_definition`, raising `WindowDefinitionMismatchError` (defined in this module) if not; then for each window, `volume_deviation = window.claim_count - baseline_window.claim_count` (matched by `window_id`) and `amount_deviation = {column: window_mean - baseline_amount.mean for each AMOUNT column}` (FR-007; depends on T019)
- [ ] T021 [US2] Implement `backend/app/features/window_feature_service.py`: `compute_window_features(df, categories, reference_stats, baseline: BaselineSnapshot, window_definition) -> list[WindowFeatures]` orchestrating T019 and T020 into one `WindowFeatures` row per window, with `anomaly_count` always `None` at this point (FR-008; depends on T019, T020, T003)
- [ ] T022 [US2] Extend `backend/app/features/features_log.py` (from T015) with `write_window_features(rows: list[WindowFeatures], out_dir=None) -> Path` and `read_window_features(out_dir=None) -> list[WindowFeatures]`, persisting to `data/features/window_features.csv`, preserving `anomaly_count` nulls through the CSV round-trip (depends on T015)
- [ ] T023 [US2] Implement `backend/app/features/features_service.py`: `compute_features(window_definition=DEFAULT_WINDOW_DEFINITION) -> tuple[list[ClaimFeatures], list[WindowFeatures]]` — the single top-level orchestrator that loads Phase 2's cleaned batch, Phase 1's column categories, Phase 2's reference stats, and Phase 4's latest `BaselineSnapshot` (raising a `FeaturesInputUnavailableError` if any are missing, mirroring `app.baseline.snapshot_service.BaselineInputUnavailableError`), then calls T014's `compute_claim_features` and T021's `compute_window_features` (depends on T014, T021)
- [ ] T024 [US2] Implement `backend/app/features/router.py`: `POST /features/compute` (calls T023, persists via T015/T022, returns `{claims_processed, windows_processed, generated_at}`, `409` on `FeaturesInputUnavailableError` or `WindowDefinitionMismatchError`), `GET /features/claims` (optional `claim_id` query param), `GET /features/windows` — per contracts/api.md (depends on T023, T015, T022)
- [ ] T025 [US2] Wire `features_router` into `backend/app/main.py`, alongside the existing `data_engineering_router`, `quality_router`, `baseline_router` (depends on T024)

**Checkpoint**: User Stories 1 and 2 both work independently — `POST /features/compute` produces both claim- and window-level features end to end.

---

## Phase 5: User Story 3 - Reserve the window-level schema for anomaly count (Priority: P3)

**Goal**: `WindowFeatures.anomaly_count` is present and null in every row produced before Phase 7 exists, with a dedicated enrichment path for Phase 7/8 to populate it later without a schema migration.

**Independent Test**: Confirm the window-level feature schema includes `anomaly_count` (nullable) immediately after this feature ships, before Phase 7 exists, and that no downstream consumer errors on its null value.

### Tests for User Story 3

- [ ] T026 [P] [US3] Test: after `POST /features/compute`, every `WindowFeatures` row's `anomaly_count` is `None` (not `0`), verified via the persisted schema/contract, in `backend/tests/features/test_window_schema_anomaly_count.py` (FR-008, SC-004)

### Implementation for User Story 3

- [ ] T027 [US3] Add `update_window_anomaly_count(window_id: str, anomaly_count: int, out_dir=None) -> WindowFeatures` to `backend/app/features/features_log.py`: looks up the persisted window row by `window_id` and rewrites only its `anomaly_count`, leaving every other field untouched, raising `KeyError` if `window_id` isn't found (depends on T022)
- [ ] T028 [US3] Add `PATCH /features/windows/{window_id}/anomaly-count` to `backend/app/features/router.py` per contracts/api.md, calling T027 and returning the updated `WindowFeatures` row (`404` if `window_id` unknown); confirm this is structurally the only write path for `anomaly_count` — `POST /features/compute` never sets it to non-null (depends on T024, T027)

**Checkpoint**: All three user stories are independently functional; the window-feature schema is stable for Phase 6/7/8 to build on.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verification that spans all three stories.

- [ ] T029 Run the full `backend/tests/features/` suite (`pytest backend/tests/features/`) plus `backend/tests/baseline/test_length_of_stay_baseline.py` to confirm T002's refactor didn't regress Phase 4, and fix any failures
- [ ] T030 Execute quickstart.md's curl-based verification steps end to end (compute, missing-discharge-date null check, `anomaly_count` all-null check, unseen-category test, deviation recomputation check) against a running backend instance, confirming each documented expected outcome

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS both user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (T002 for T010, T003 for T012/T014/T015, T004 for T015). Independent of US2.
- **User Story 2 (Phase 4)**: Depends on Foundational (T003, T004) and reuses `app.baseline` modules directly (not on US1's outputs) for T019/T020/T021; T023's orchestrator depends on both T014 (US1) and T021 (US2), so T023-T025 are the integration point where the two stories join.
- **User Story 3 (Phase 5)**: Depends on US2's `features_log.py` (T022) and `router.py` (T024).
- **Polish (Phase 6)**: Depends on all three user stories.

### Within Each User Story

- Tests before implementation (write first, confirm they fail, then implement).
- Claim-level feature computers (T009, T011, T013 — parallelizable) before the orchestrator (T014).
- Window aggregates (T019) before deviation features (T020) before the window orchestrator (T021).
- Both story orchestrators (T014, T021) before the top-level `features_service.py` (T023) and router (T024).

### Parallel Opportunities

- T003 and T004 (Foundational) can run in parallel — different files.
- T005-T008 (US1 tests) can run in parallel — different files, no shared dependency.
- T009, T011, T013 (US1 claim-level computers) can run in parallel — different files.
- T016-T018 (US2 tests) can run in parallel — different files.
- T019 must complete before T020 (deviation reads window aggregates' output shape).

---

## Parallel Example: User Story 1

```bash
# Tests together:
Task: "Test payment-to-charge ratio nulls on zero/missing denominator in backend/tests/features/test_amount_ratios.py"
Task: "Test length-of-stay matches Phase 4 derivation, null on missing dates in backend/tests/features/test_length_of_stay_feature.py"
Task: "Test unseen-category encoding maps to unknown bucket in backend/tests/features/test_categorical_encoding.py"
Task: "Test provider frequency reflects real occurrence rate in backend/tests/features/test_provider_frequency.py"

# Independent claim-level computers together:
Task: "Implement compute_amount_ratios in backend/app/features/claim_level/amount_ratios.py"
Task: "Implement compute_date_features in backend/app/features/claim_level/date_features.py"
Task: "Implement compute_provider_frequency in backend/app/features/claim_level/provider_frequency.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1 — claim-level features computable and persistable in isolation (even without a router yet).
4. **STOP and VALIDATE**: Run T005-T008 against T009-T015.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. User Story 1 → claim-level features validated independently.
3. User Story 2 → window-level features validated independently; T023-T025 join both stories behind the `/features` API.
4. User Story 3 → `anomaly_count` schema slot + enrichment endpoint, completing the full feature set.
5. Polish → full-suite regression check + quickstart validation.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- No task fabricates a feature value for missing source data (constitution Principle II, FR-010) — every "null on missing input" behavior is enforced in the implementation task itself, not deferred to a later cleanup pass.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
