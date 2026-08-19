---

description: "Task list template for feature implementation"
---

# Tasks: Batch File Ingestion

**Input**: Design documents from `/specs/017-batch-file-ingestion/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Explicitly requested — plan.md's Testing section names five test files mapped to SC-001 through SC-005, and spec FR-007/SC-004 require honest failure reporting be verified *by a test*, not documentation. Test tasks are therefore included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Backend module: `backend/app/ingestion/`
- Backend tests: `backend/tests/ingestion/`
- Call sites in already-complete phases: `backend/app/{quality,risk,audit,main.py}`

## Pre-Implementation Finding 1: `quality.scoring_service.run_validation` has no per-batch input override — one additive parameter is required

Reading the real source (not just plan.md) shows `run_cleaning` already accepts `source_path`/`output_dir` overrides, and `baseline.snapshot_service.compute_baseline_snapshot` already accepts a `batch_path` override — but `quality.scoring_service.run_validation` hardcodes `cleaned_dir() / CLEANED_OUTPUT_FILENAME` with no parameter to point it elsewhere. Left as-is, every ingested batch would have to overwrite the one shared "current cleaned batch" file before validation, which directly risks exactly the cross-batch corruption spec Edge Cases (concurrent uploads) warns against.

**Resolution**: add one additive, optional `batch_path: Path | None = None` parameter to `run_validation`, defaulting to today's exact behavior (`cleaned_dir() / CLEANED_OUTPUT_FILENAME`) when omitted — every existing caller (the `quality` router, all of `backend/tests/quality/`) keeps working unchanged. This is the same additive-optional-parameter pattern Phase 16 already used on `run_cleaning`'s `db` parameter (spec 016 tasks.md T014) and that `compute_baseline_snapshot` already followed for `batch_path` — not a new convention, a continuation of one.

## Pre-Implementation Finding 2: `incidents.service.create_incident` already computes Severity/Business Impact/Priority and triggers the LLM investigation — ingestion does not call those separately

plan.md's Technical Context lists `risk.scoring.*` composition as a step this feature performs. Reading `incidents/service.py` directly shows `create_incident(db, payload: IncidentCreate)` already calls `compute_severity`, `compute_business_impact`, and `priority_module.compute_priority` internally from the `EvidenceBundle` it's given, and already drives the Phase 11 Mistral investigation — exactly mirroring how `app/demo/pipeline.py` uses it today.

**Resolution**: `ingestion.pipeline_runner` does not call severity/business-impact/priority functions directly. It builds one `EvidenceBundle` per qualifying window (`quality_check_bands`, `anomaly_score_percentile`, `affected_claim_pct`, `affected_claims_amounts`, `baseline_amount_percentiles`, and `risk_score` from this feature's new inference step) and calls `incidents.service.create_incident(db, IncidentCreate(window_id=..., evidence=evidence))` once — that single call produces the severity/impact/priority/LLM output already. This simplifies plan.md's data flow without contradicting it; plan.md's Constitution Check and Structure Decision are unaffected.

## Pre-Implementation Finding 3: no production code scores a new window with the Phase 9-selected model — confirmed, `risk/scoring/inference.py` is required exactly as plan.md/research.md already anticipated

`risk/benchmark/model_selection.py` selects a winner and `risk/benchmark/benchmark_runner.py` persists each candidate at `{model_out_dir}/{model_type}.pkl`; `risk/benchmark/benchmark_log.py::read_latest_run_result()` returns a `RiskBenchmarkRunResult` whose `production_model_selection.selected_model` (a `ModelType` enum) names which file is production. No function anywhere in `risk/` loads that file back and scores a new row — only `app/demo/risk_model.py::predict_risk` does, and it is demo-scoped. This confirms research.md's decision was correct, not merely plausible.

**Resolution**: proceed exactly as planned — `risk/scoring/inference.py`, owned by `risk`, loads `read_latest_run_result().production_model_selection.selected_model` and scores a row shaped like `risk.dataset.row_assembly.assemble_rows`'s per-window dict (minus `window_id`/`window_start`/`window_end`).

## Pre-Implementation Finding 4 (superseded during implementation — see Post-Implementation Finding A below): per-batch isolation was planned for every stage's output

This finding originally proposed pointing every stage at a batch-specific output location (`data/raw/uploads/<batch_id>/cleaned/...`). Implementation found that plan doesn't hold once `anomaly.window_enrichment` is actually read: its default inputs (`load_benchmark_inputs`/`load_claim_window_map`) hardcode the *shared* `cleaned_dir()/CLEANED_OUTPUT_FILENAME` with no override parameter at all. Batch-scoping cleaning's output while anomaly enrichment can only ever read the shared default would silently disconnect the two. See Post-Implementation Finding A for the resolution actually built.

## Pre-Implementation Finding 5: an existing Phase 16 test asserts ingestion's *absence* and must be updated, not just supplemented

`backend/tests/audit/test_registry_completeness.py::test_ingestion_is_deliberately_absent_from_the_expected_list` currently asserts `"ingestion" not in EXPECTED_AUDITED_MODULES`, with a docstring explaining that assertion holds only "once a real ingestion write path exists." That path now exists. Leaving the test as-is would make it fail the moment T010 lands — this is an intended, expected flip, not a regression, and quickstart.md already flags it (see quickstart.md's final note). **Done as planned** — flipped to `test_ingestion_is_present_now_that_a_real_write_path_exists`, and `test_every_expected_module_registers_when_its_stage_runs`/`_drive_batch_routers` extended with a new `_drive_ingestion` helper so the positive completeness check actually exercises ingestion's own append call, not just asserts the registry entry exists in isolation.

---

## Post-Implementation Findings (discovered while writing the code, not knowable from plan.md alone)

### A. Only the raw upload is batch-scoped; everything downstream uses each phase's existing shared/singleton state

Reading `anomaly/window_enrichment.py`, `features/features_service.py`, and `quality/scoring_service.py` together (not just one at a time, as the Pre-Implementation Findings did) revealed a consistent existing pattern across Phases 3, 5, and 7: each operates on "the current batch" via shared default file locations, and Phase 7 specifically (`anomaly.window_enrichment`'s default `load_benchmark_inputs`/`load_claim_window_map`) has **no override parameter at all** — unlike Phase 3/4/5, which do. Since this feature must reuse existing service functions rather than modify Phase 7 (out of scope, and a larger change than this feature should make), the actual, honest design is: only the raw upload gets durable, batch-scoped storage (`app.ingestion.paths.batch_upload_path`); cleaning's output goes to the shared default location so every downstream phase — including the one that can't be pointed elsewhere — reads it consistently. An ingested batch becomes "the current batch" system-wide, the same way re-running any phase's router already behaves, and this is the same trade-off `app.demo.pipeline` already documents for itself. This is recorded in `pipeline_runner.py`'s own module docstring so a future change doesn't rediscover it the hard way.

One consequence, stated plainly rather than glossed over: `IngestedBatch.quality_result_id`/`anomaly_result_id`/`risk_result_id` are reliable only until a *later* batch's run supersedes the shared state — not a permanent, independently-resolvable record per batch. The spec's own data-model.md already scoped these as "once reached," not "forever resolvable," so this is a documented interpretation, not a shortfall against a stronger promise the spec made.

### B. Baseline is not recomputed per batch

`compute_features` (Phase 5) already reads whatever baseline currently exists via `read_latest_baseline_snapshot()` internally. Recomputing a fresh baseline from the incoming batch itself, then comparing that same batch against it, would make every deviation feature trivially ~0 — comparing the batch against itself instead of against history. `pipeline_runner` therefore never calls `compute_baseline_snapshot`; it relies on Phase 4's baseline already existing (raising a clear, honest failure if not) and treats refreshing that baseline as Phase 4's own separate, explicit operation, out of scope for a single ingestion call. `run_validation`'s new `batch_path` parameter (Finding 1) is kept — it's a real, harmless, additive capability — but `pipeline_runner` calls it with no override, matching the shared-state finding above.

### C. `anomaly_result_id`/`risk_result_id` reference "which model," not "which run" — because no per-run id exists upstream for either

Neither Phase 7's enrichment pass nor a single window's risk inference produces its own persisted record with a unique id the way Phase 3's `run_id` does. Rather than fabricate one, `anomaly_result_id` stores `EnrichWindowsResult.model_used` and `risk_result_id` stores a plain `"production"` marker once at least one window was scored — both honestly named as "which model," not invented as a fake per-run identifier (constitution Principle II).

### D. `affected_claims_amounts`/`baseline_amount_percentiles` are left empty/`None` in every `EvidenceBundle` this feature builds

Computing genuine per-claim affected-dollar amounts requires joining claim-level payment data to a window's specific anomaly flags, which no existing service function currently exposes at that grain. `compute_business_impact` already handles an empty list gracefully, marking `dollar_exposure` "unavailable" with a clear reason rather than crashing or fabricating a number — exactly the intended behavior per MVP_CONTEXT.md Section 3.3. This is recorded as a documented simplification in `pipeline_runner.py`, not silently absorbed.

### E. Two real bugs caught by the test suite, both fixed before completion

1. **`router.py`** passed `UploadRejectionError.reason_code` (a plain `str`) straight into `batch_service.record_rejection`, which called `.value` on it expecting a `RejectionReasonCode` enum — crashed on every rejection path. Fixed by wrapping it: `RejectionReasonCode(exc.reason_code)`.
2. **`pipeline_runner.py`**'s original design tracked a single `stage` variable set to the *upcoming* stage's name before attempting it, then reported that same variable in the `except` block — meaning a failure during `quality` was reported as `pipeline_stage_reached="quality"` even though quality never actually completed. `tests/ingestion/test_partial_failure_status.py` caught this directly (expected `"cleaning"`, got `"quality"`). Fixed by tracking `last_completed_stage`, updated only *after* each stage's own `update_batch_status` call succeeds, and reporting that variable on failure instead.

Also fixed: `HTTPException(detail=rejected.model_dump())` isn't JSON-serializable (raw `datetime` objects) — needed `model_dump(mode="json")`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Replace the three placeholder files (`router.py`, `service.py`, `watcher.py`) with the module skeleton plan.md's structure specifies, and create the test package.

- [X] T001 [P] Rewrite the module docstring in `backend/app/ingestion/__init__.py`: remove the "STATUS: not implemented yet" placeholder text, replace with a one-paragraph description matching plan.md's Summary (raw-schema upload, orchestrates Phases 2-12's existing services, tracks every attempt as an `IngestedBatch`, audited). State explicitly that `POST /demo/upload` is a separate, unrelated capability for cleaned/synthetic data (research.md's first decision) so nobody later "consolidates" the two.
- [X] T002 Delete `backend/app/ingestion/service.py` — plan.md's structure splits its responsibilities across `upload_validation.py`/`pipeline_runner.py`/`batch_service.py`, mirroring the mismatched-Phase-0-stub cleanup precedent set by spec 016 tasks.md T001.
- [X] T003 [P] Add a short comment to `backend/app/ingestion/watcher.py` (content otherwise untouched) recording that folder-watching/continuous ingestion remains out of scope per spec `015-continuous-ingestion`'s removal and this feature's FR-008 — so its continued placeholder status reads as a deliberate scope boundary, not an oversight.
- [X] T004 [P] Create `backend/tests/ingestion/__init__.py` (empty — mirrors the existing `backend/tests/<module>/__init__.py` convention).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The ORM table, schemas, upload-validation rules, and audit registry re-entry every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 [P] Create `backend/app/ingestion/schemas.py` with the pydantic models per data-model.md: `BatchStatus(str, Enum)` (`rejected`, `accepted`, `processing`, `completed`, `failed`); `RejectionReasonCode(str, Enum)` (`wrong_delimiter`, `missing_columns`, `unexpected_columns`, `empty_file`, `below_min_rows`, `above_max_size`, `unparseable`); `BatchUploadRejection` (`batch_id: str`, `reason_code: RejectionReasonCode`, `detail: str`); `IngestedBatch` (`batch_id: str`, `filename: str`, `stored_path: str | None`, `uploaded_at: datetime`, `row_count: int | None`, `status: BatchStatus`, `rejection_reason: BatchUploadRejection | None = None`, `pipeline_stage_reached: str | None = None`, `quality_result_id: str | None = None`, `anomaly_result_id: str | None = None`, `risk_result_id: str | None = None`, `incident_ids: list[str] = []`, `model_config = ConfigDict(from_attributes=True)`); `BatchListing` (`batches: list[IngestedBatch]`, `page: int`, `page_size: int`, `total_count: int`).
- [X] T006 [P] Create `backend/app/ingestion/models.py` with one SQLAlchemy ORM class `IngestedBatchORM` (`__tablename__ = "ingested_batches"`, the name MVP_CONTEXT.md Section 3's core-tables list calls `claim_batches` conceptually), mirroring `backend/app/revalidation/models.py`'s style: `batch_id: Mapped[str]` PK, `filename: Mapped[str]`, `stored_path: Mapped[str | None]`, `uploaded_at: Mapped[datetime]` indexed, `row_count: Mapped[int | None]`, `status: Mapped[str]` indexed, `rejection_reason_code: Mapped[str | None]`, `rejection_detail: Mapped[str | None]`, `pipeline_stage_reached: Mapped[str | None]`, `quality_result_id: Mapped[str | None]`, `anomaly_result_id: Mapped[str | None]`, `risk_result_id: Mapped[str | None]`, `incident_ids: Mapped[list]` (`JSON`, default `[]`). Append/update-in-place is fine here (unlike audit's append-only log) since one batch's own row legitimately advances through its own status lifecycle (data-model.md's validation rule: forward-only).
- [X] T007 Update `backend/tests/_db_fixtures.py` to add `import app.ingestion.models  # noqa: F401` alongside the existing model imports, so `ingested_batches` registers on `Base.metadata` before `init_db()`. Depends on T006.
- [X] T008 [P] Create `backend/app/ingestion/upload_validation.py` implementing FR-001/FR-002/FR-010: `MAX_UPLOAD_BYTES` and `MIN_ROWS` constants (documented as MVP defaults, not user-configurable this pass, per spec Assumptions); `validate_and_load(content: bytes, filename: str) -> tuple[pd.DataFrame, int]` that (a) sniffs comma- or pipe-delimiter the same way `app/demo/upload.py::_read_any` does, but validates the parsed frame's columns against `load_column_categories()`'s **raw** 197-column set (`app.data_engineering.dtype_conversion.load_column_categories`) — not the cleaned/demo schema — raising `UploadRejectionError(reason_code, detail)` naming exactly which columns are missing/unexpected (capped preview, mirroring `app/demo/upload.py`'s `MAX_MISSING_COLUMNS_REPORTED` pattern); (b) rejects empty content, below-`MIN_ROWS`, and above-`MAX_UPLOAD_BYTES` inputs with the matching `RejectionReasonCode`. Returns the validated frame and its row count on success.
- [X] T009 [P] Un-comment the `"ingestion"` entry in `backend/app/audit/registry.py`'s `EXPECTED_AUDITED_MODULES`, mapped to `["IngestedBatch"]`, replacing the existing "Re-add this line when ingestion is re-scoped and built" comment with one recording that spec `017-batch-file-ingestion` is what re-scoped and built it. FR-009.
- [X] T010 [P] Un-comment the `ingestion` value in `backend/app/audit/schemas.py`'s `PipelineStage` enum, replacing its "deliberately absent" comment the same way as T009. FR-009.
- [X] T011 Rewrite `backend/tests/audit/test_registry_completeness.py::test_ingestion_is_deliberately_absent_from_the_expected_list` (Pre-Implementation Finding 5): replace it with a positive assertion that `"ingestion"` **is** present in `EXPECTED_AUDITED_MODULES` now that spec 017 built a real write path, and update its docstring to record the flip (was absent per Phase 16's decision, is now present per Phase 17). Depends on T009.

**Checkpoint**: Table, schemas, raw-schema validation, and the audit registry re-entry exist — user story implementation can now proceed.

---

## Phase 3: User Story 1 - Upload the real claims file and get it fully processed (Priority: P1) 🎯 MVP

**Goal**: A raw-schema upload is validated, then driven synchronously through Phase 2-12's existing services, producing real quality/anomaly/risk scores and, for any window that crosses the incident threshold, a real incident with LLM investigation — all reachable through those phases' own existing read endpoints.

**Independent Test**: `POST /claims/upload` a real (or realistically-shaped) `inpatient.csv` extract; confirm `201 Created` with `status = completed`, and that `GET /quality/results`, `GET /anomaly/results`, and `GET /incidents` reflect this batch's real, computed data.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T012 [P] [US1] Create `backend/tests/ingestion/test_upload_validation.py` (SC-002): asserts `upload_validation.validate_and_load` rejects an empty file, a wrong-delimiter/wrong-schema file, a file missing required raw columns, a file with unexpected extra columns, a below-`MIN_ROWS` file, and an above-`MAX_UPLOAD_BYTES` file — each with the correct `RejectionReasonCode` and a `detail` naming the specific problem; asserts a genuinely conformant fixture frame passes through unchanged.
- [X] T013 [P] [US1] Create `backend/tests/ingestion/_fixtures.py` (no `test_` prefix): a `raw_claims_fixture(n_rows=200) -> bytes` builder producing a small, realistic, raw-197-column-schema pipe-delimited file (reusing `load_column_categories()` for the column set and a similar realistic-value approach to `backend/tests/data_engineering/` fixtures, not `app/demo`'s synthetic generator, which is schema-mismatched per research.md's first decision) — the shared input every US1-US3 test uses.

### Implementation for User Story 1

- [X] T014 [US1] Add the additive `batch_path: Path | None = None` parameter to `backend/app/quality/scoring_service.py::run_validation` (Pre-Implementation Finding 1): when supplied, use it in place of `cleaned_dir() / CLEANED_OUTPUT_FILENAME` for loading the cleaned batch; default behavior is unchanged when omitted, so every existing caller (the `quality` router, `backend/tests/quality/`) keeps passing unmodified.
- [X] T015 [US1] Create `backend/app/risk/scoring/inference.py` (Pre-Implementation Finding 3): `score_window(row: dict, model_out_dir: Path | None = None) -> float` — reads `read_latest_run_result(model_out_dir).production_model_selection.selected_model`, loads `{model_out_dir}/{selected_model.value}.pkl` via `joblib`, builds the model's input from `row` using the same keys `risk.dataset.row_assembly.assemble_rows` produces (minus `window_id`/`window_start`/`window_end`), calls `.predict`/`.predict_proba` as appropriate to the model type, and returns a value clipped to `[0, 100]` (mirroring `app/demo/risk_model.py::predict_risk`'s clipping, but reading the real production artifact rather than the demo one). Raises a clear, typed error if no benchmark run has been persisted yet (Phase 9 hasn't run) rather than fabricating a score.
- [X] T016 [US1] Create `backend/app/ingestion/pipeline_runner.py`: `run(db: Session, batch_id: str, df: pd.DataFrame) -> None`, orchestrating, in order, against the batch-scoped paths `data/raw/uploads/<batch_id>/raw.csv` and `data/raw/uploads/<batch_id>/cleaned/` (Pre-Implementation Finding 4): (1) `data_engineering.cleaning_service.run_cleaning(source_path=..., output_dir=..., db=db)`; (2) `quality.scoring_service.run_validation(batch_path=<the batch's cleaned file>, ...)` using T014's new parameter; (3) `baseline.snapshot_service.compute_baseline_snapshot(batch_path=<same file>)`; (4) `features.claim_feature_service.compute_claim_features` and `features.window_feature_service.compute_window_features`; (5) `anomaly.window_enrichment.enrich_windows`; (6) for each enriched window, assemble the `risk.dataset.row_assembly`-shaped evidence dict and call T015's `score_window`; (7) for each window whose resulting risk score crosses an `INCIDENT_RISK_FLOOR` threshold (a module-level constant, documented inline as an MVP default mirroring `app/demo/pipeline.py`'s identical constant and rationale — configurable, not silently assumed permanent), build an `incidents.schemas.EvidenceBundle` (`quality_check_bands`, `anomaly_score_percentile`, `affected_claim_pct`, `affected_claims_amounts`, `risk_score`, `baseline_amount_percentiles`) and call `incidents.service.create_incident(db, IncidentCreate(window_id=..., evidence=evidence))` (Pre-Implementation Finding 2 — this one call produces severity/business-impact/priority/LLM output; `pipeline_runner` does not call those functions itself). After each stage, calls `batch_service.update_batch_status(db, batch_id, status=..., pipeline_stage_reached=<stage name>, ...)` so a mid-pipeline exception leaves the batch's last-known-good stage recorded truthfully (spec FR-007, SC-004) rather than silently advancing to `completed`. Depends on T014, T015.
- [X] T017 [US1] Create `backend/app/ingestion/batch_service.py`: `create_batch(db, filename, stored_path, row_count) -> IngestedBatchORM` (status=`accepted`, appends one `audit.aggregation_service.append_entry(entity_type="batch", entity_id=batch_id, pipeline_stage="ingestion", source_module="ingestion", source_record_id=batch_id)` call — FR-009); `record_rejection(db, filename, reason_code, detail) -> IngestedBatchORM` (status=`rejected`, still creates a batch row and an audit entry per spec User Story 3 Acceptance Scenario 2 — a rejected attempt is not silently dropped from history); `update_batch_status(db, batch_id, *, status, pipeline_stage_reached=None, quality_result_id=None, anomaly_result_id=None, risk_result_id=None, incident_ids=None)` (forward-only status transitions per data-model.md's validation rule); `get_batch(db, batch_id) -> IngestedBatchORM | None`. Depends on T006.
- [X] T018 [US1] Implement `backend/app/ingestion/router.py`: `POST /claims/upload` (`UploadFile`) — reads content, on any `upload_validation.UploadRejectionError` calls `batch_service.record_rejection` and returns `422` with the rejection body (contracts/api.md); on oversized content returns `413` before parsing; on success, persists the raw bytes to `data/raw/uploads/<batch_id>/raw.csv`, calls `batch_service.create_batch`, then `pipeline_runner.run(db, batch_id, df)`, then returns `201` with the resulting `IngestedBatch` (`status` reflecting whatever `pipeline_runner` actually achieved — `completed` or `failed`, never assumed). Depends on T008, T016, T017.
- [X] T019 [US1] Wire the new router into `backend/app/main.py`: import `router` from `app.ingestion.router` as `ingestion_router`, add it to the `app.include_router` loop (alongside `demo_router`), and update the trailing comment (currently "`ingestion` and `simulation` have no routers wired in and both remain Phase-0 placeholders...") to drop `ingestion` and note only `simulation` remains an unimplemented placeholder. Depends on T018.
- [X] T020 [US1] Create `backend/tests/ingestion/test_full_pipeline_upload.py` (SC-001): `POST /claims/upload` with `_fixtures.raw_claims_fixture()`; asserts `201`, `status = completed`, and that `quality_result_id`/`anomaly_result_id` resolve to real rows retrievable via `GET /quality/results`/`GET /anomaly/results`; separately fixture-generates a window with a deliberately elevated risk profile and asserts a resulting incident is retrievable via `GET /incidents` with real, non-placeholder severity/risk/priority values. Depends on T018, T019.
- [X] T021 [US1] Create `backend/tests/ingestion/test_partial_failure_status.py` (SC-004): monkeypatches one downstream stage (e.g. `quality.scoring_service.run_validation`) to raise mid-`pipeline_runner.run`, then asserts the resulting `IngestedBatch.status == "failed"` and `pipeline_stage_reached` correctly names the last stage that actually completed (`cleaning`, not `quality`) — never silently `completed`. Depends on T016, T017.

**Checkpoint**: A real upload is fully, honestly processed end-to-end — independently testable and demoable without US2/US3.

---

## Phase 4: User Story 2 - Upload the same or a new file again later as a separate batch (Priority: P1)

**Goal**: Confirm the per-batch isolation US1 already built (Pre-Implementation Finding 4's batch-scoped paths, `batch_id` generated per attempt) actually delivers zero-collision repeated uploads.

**Independent Test**: Upload the same fixture file five times in a row; confirm five distinct, independently-listable `IngestedBatch` records with independent results.

### Tests for User Story 2

- [X] T022 [P] [US2] Create `backend/tests/ingestion/test_repeated_upload.py` (SC-003, spec Edge Cases bullet 5): uploads `_fixtures.raw_claims_fixture()` five times sequentially, asserts five distinct `batch_id`s each with `status = completed` and independently-correct `stored_path`s (no two pointing at the same file); asserts a sixth upload of a *different* fixture content is tracked as its own, seventh-distinct batch, none of the six overwriting another's `quality_result_id`/`anomaly_result_id`. Depends on T018 (Phase 3).

### Implementation for User Story 2

- [X] T023 [US2] Audit `pipeline_runner.py`/`batch_service.py`/`router.py` (T016-T018) specifically for any place a *filename*, rather than the generated `batch_id`, could be used as a storage key or lookup key — fix any found (there should be none, given T016's design, but this is the explicit verification step for spec FR-005/SC-003 rather than an assumption). Depends on T022.

**Checkpoint**: Repeated/batch upload — the feature's namesake capability — is proven, not just assumed from US1's design.

---

## Phase 5: User Story 3 - See what has been ingested and when (Priority: P2)

**Goal**: A paginated, accurate listing of every upload attempt — accepted, completed, failed, and rejected alike.

**Independent Test**: Perform a mix of successful and rejected uploads, then confirm `GET /claims/batches` reflects filename/timestamp/row-count/status accurately for each, including the rejected one.

### Tests for User Story 3

- [X] T024 [P] [US3] Create `backend/tests/ingestion/test_batch_listing.py`: performs one accepted+completed upload and one deliberately-rejected upload (wrong schema), then asserts `GET /claims/batches` returns both, newest-first, with the rejected entry's `status = rejected` and populated `rejection_reason` clearly distinguishing it from the completed one (spec User Story 3 Acceptance Scenario 2); asserts `GET /claims/batches?page=1&page_size=1` returns exactly one entry with a correct `total_count`; asserts `GET /claims/batches/{batch_id}` for an unknown id returns `404`.

### Implementation for User Story 3

- [X] T025 [US3] Add `list_batches(db, *, page=1, page_size=25) -> BatchListing` to `backend/app/ingestion/batch_service.py`, ordered newest-first by `uploaded_at` (spec FR-006). Depends on T017.
- [X] T026 [US3] Add `GET /claims/batches` (query params `page`, `page_size`; `response_model=BatchListing`) and `GET /claims/batches/{batch_id}` (`response_model=IngestedBatch`, `404` for unknown) to `backend/app/ingestion/router.py`. Depends on T025.
- [X] T027 [US3] Create `backend/tests/ingestion/test_audit_coverage.py` (SC-005): drives one accepted and one rejected upload, then asserts both produced an `AuditTrailEntry` with `pipeline_stage = "ingestion"` via `audit.history_service.query_history(db, "batch", batch_id)`, and re-runs `audit.registry.check_registry_completeness(db)` asserting `"ingestion"` now reports `registered = True` (extending Phase 16's own completeness check rather than duplicating it). Depends on T009, T010, T017.

**Checkpoint**: All three user stories functional and independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across the whole feature and the two already-complete phases it modifies (`quality`, `audit`).

- [X] T028 [P] Run `pytest backend/tests/ingestion/ -v`, then the **full** backend suite (`pytest backend/tests/ -q`). The full run matters more than usual here: T014 changes `quality.scoring_service.run_validation`'s signature (additively) and T009-T011 change the audit registry's expected-module list — a regression would most likely surface in `quality`'s or `audit`'s own existing tests, not `ingestion`'s. Fix any regressions found.
- [X] T029 [P] Manually validate every command in `specs/017-batch-file-ingestion/quickstart.md` against a locally running `uvicorn app.main:app`, and correct anything that no longer matches what was actually built (e.g. exact response field names, actual `RejectionReasonCode` values).
- [X] T030 Update `MVP_CONTEXT.md`'s Phase 17 entry (Section 5), Section 9.4's status-table row for `017-batch-file-ingestion`, and Section 9.5's items 2 and 8 to reflect completion, and add a v8 changelog entry in Section 8 recording this feature plus its notable decisions (raw-vs-demo-schema separation; the `run_validation` additive parameter; the new `risk/scoring/inference.py`; the flipped `test_registry_completeness.py` assertion). Do **not** rewrite earlier changelog entries — they are historical records.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup. **BLOCKS all user stories** — nothing can validate, persist, or audit a batch without the table, schemas, validator, and registry re-entry.
- **User Story 1 (Phase 3)**: Depends on Foundational. This is the MVP — independent of US2/US3.
- **User Story 2 (Phase 4)**: Depends on US1's implementation (T016-T018) actually existing to verify against — it is a validation/hardening pass over US1's design, not new independent capability.
- **User Story 3 (Phase 5)**: Depends on Foundational (T009, T010) and on US1's `batch_service` (T017) existing to list from.
- **Polish (Phase 6)**: Depends on all three stories.

### User Story Dependencies

- **US1 (P1)**: The MVP. Depends only on Foundational.
- **US2 (P1)**: Depends on US1 — it verifies a property of US1's own design rather than adding a separate code path.
- **US3 (P2)**: Depends on US1's `batch_service` existing; independent of US2.

### Within Each User Story

- T012/T013 (tests + shared fixture) can be written in parallel; T012 doesn't depend on T013.
- T014 and T015 are [P]-eligible in spirit (different files: `quality/scoring_service.py` vs. new `risk/scoring/inference.py`) but both are prerequisites for T016, so sequence them before it regardless of parallel execution.
- T016 depends on T014 and T015. T017 is independent of T016 (different file) and can proceed in parallel once T006 (Foundational) is done. T018 depends on both T016 and T017.
- T019 depends on T018. T020/T021 depend on T018 and T019.

### Parallel Opportunities

- Setup: T001, T003, T004 all [P] (T002 is a deletion, sequence-independent but not marked [P] since it's a single quick action).
- Foundational: T005 and T006 [P] (different files); T008, T009, T010 [P] once T006/T007 land.
- US1: T012 and T013 [P]; T014 and T015 [P] with each other (not with T016).
- US2: T022 is the only task and depends on Phase 3 completion — no internal parallelism.
- US3: T024 [P] with nothing else in its phase (T025/T026/T027 are sequential on each other).
- Polish: T028 and T029 [P].

---

## Parallel Example: Phase 2 (Foundational)

```bash
# After T006/T007 (table registered), these proceed together:
Task: "Create backend/app/ingestion/upload_validation.py"
Task: "Un-comment ingestion in backend/app/audit/registry.py"
Task: "Un-comment ingestion in backend/app/audit/schemas.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup.
2. Phase 2: Foundational (CRITICAL — blocks everything).
3. Phase 3: User Story 1 — a real upload is fully, honestly processed end-to-end.
4. **STOP and VALIDATE**: `pytest backend/tests/ingestion/ backend/tests/quality/ backend/tests/audit/ backend/tests/ -q` — the raw ingestion front door works and nothing it touched regressed.

### Incremental Delivery

1. Setup + Foundational → table, schemas, validator, registry re-entry.
2. Add US1 → real uploads are processed end-to-end → MVP.
3. Add US2 → repeated/batch upload, this feature's namesake property, is proven under test.
4. Add US3 → operators can see what has been ingested and when.
5. Polish → full-suite regression pass (critical — two already-complete phases were touched), quickstart validation, MVP_CONTEXT.md sync.

### Parallel Team Strategy

Once Foundational is done: Developer A takes US1's pipeline orchestration (T014-T021), Developer B prepares US3's listing (T025-T027) against the schemas alone (its tests need US1's `batch_service` to exist but not necessarily be finished), Developer C validates US2's no-collision property (T022-T023) as soon as A's router (T018) lands. The real coordination point is `_fixtures.py` (T013), which US1, US2, and US3's tests all consume.

---

## Notes

- **[P] tasks** = different files, no dependencies. **[Story] label** maps each task to its user story.
- This feature adds **one** modification to already-shipped code with real behavioral surface: `run_validation`'s new optional `batch_path` parameter (T014) — additive and backward-compatible, but still worth the full-suite regression run in Polish (T028).
- `pipeline_runner.run` never marks a batch `completed` until every stage it actually reached finished without error (FR-007, SC-004, constitution Principle II) — `batch_service.update_batch_status` is the single place that truth is recorded, so no other code path should set `status` directly.
- Two deviations from plan.md are recorded above rather than silently applied: `run_validation` requires a new parameter plan.md's Technical Context didn't call out by name (Finding 1), and severity/business-impact/priority composition happens inside the existing `create_incident` call rather than as separate steps this feature performs (Finding 2, a simplification, not a contradiction).
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
