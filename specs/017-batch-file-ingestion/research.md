# Phase 0 Research: Batch File Ingestion

## Decision: This feature ingests the raw 197-column schema; it is not a rewrite or replacement of `app/demo`'s upload endpoint

**Decision**: `POST /claims/upload` (this feature) validates against the raw, pre-cleaning claims schema (the 197 columns profiled in Phase 1, pipe-delimited) and runs the file through Phase 2's actual `cleaning_service.run_cleaning`. `POST /demo/upload` (existing, unchanged) validates against the already-cleaned schema (`column_profile["column_order"]`, sourced from `data/cleaned/inpatient_cleaned.csv`) for synthetic/demo data and skips cleaning entirely. Both endpoints coexist permanently; neither supersedes the other.

**Rationale**: The two inputs are genuinely different shapes — a real CMS extract has never been cleaned, while demo/synthetic batches are generated to already match the cleaned schema so the Simulator can skip straight to quality/anomaly/risk for demo speed. Conflating them would either force real uploads through a cleaning-skip path they need (silently violating Phase 2), or force demo data through cleaning it was never designed to need. `app/demo/pipeline.py`'s own docstring already documents this distinction implicitly by scoping itself to "batches, simulator runs and uploads" of demo data specifically.

**Alternatives considered**: Extending `app/demo/upload.py` to also accept the raw schema and branch internally (rejected — mixes a demo-scoped module's responsibility with a production ingestion path, violating Principle VI's modular ownership, and would make `app/demo` a dependency of the real ingestion flow rather than the reverse).

## Decision: `pipeline_runner.py` calls each phase's existing public service function directly, in-process, synchronously

**Decision**: On a validated upload, `ingestion.pipeline_runner.run(db, batch_id, raw_path)` calls, in order: `data_engineering.cleaning_service.run_cleaning(source_path=raw_path, db=db)` → `quality.scoring_service.run_validation()` → `features.features_service.compute_features()` (Phase 5, which already reads whatever baseline currently exists internally — see the updated decision below on why baseline is not recomputed here) → `anomaly.window_enrichment.enrich_windows()` → `risk.dataset.row_assembly.assemble_rows()` joined with the new `risk.scoring.inference.score_window` call (see next decision) → `incidents.service.create_incident(...)` for any window crossing the incident threshold — all within the same request that accepted the upload, matching the precedent `app/demo/pipeline.py`'s `run_pipeline` already set for demo data. **Updated during implementation** (tasks.md Post-Implementation Finding A): every stage after cleaning is called with its *default* arguments, reading/writing the same shared, single-current-batch locations every other phase's router already uses — not batch-scoped output paths as originally described here — because `anomaly.window_enrichment`'s default inputs have no per-batch override at all, and isolating every other stage while that one couldn't be isolated would silently disconnect them. Baseline is deliberately **not** recomputed per batch (Post-Implementation Finding B): `compute_features` already reads the existing baseline as-is; recomputing it from the incoming batch itself would compare the batch against itself.

**Rationale**: Every one of these functions already exists, is already tested, and `run_cleaning` already accepts a `source_path` override specifically so callers (including tests) can point it at a file other than the default `data/raw/inpatient.csv` — this feature needs no new pipeline logic, only a new caller. Synchronous, in-process orchestration avoids introducing a job queue/worker infrastructure this codebase doesn't have yet, and matches spec Assumptions' explicit call for synchronous processing in this MVP pass.

**Alternatives considered**: A background task queue (e.g., Celery/RQ) processing uploads asynchronously with a polling status endpoint (rejected for this pass — real infrastructure addition beyond this feature's scope; the dataset's realistic scale, tens of thousands of rows per MVP_CONTEXT.md Section 2.2, completes well within a single request/response cycle, as already demonstrated by `app/demo/router.py`'s synchronous `POST /demo/upload`).

## Decision: A new `risk.scoring.inference` module loads the Phase 9-selected production model and scores a newly-assembled row; it does not live in `ingestion`

**Decision**: Phase 9 (`risk/benchmark/model_selection.py`) selects and the codebase persists the winning model (`data/models/risk/{logistic_regression,random_forest,xgboost}.pkl`), and Phase 8 (`risk/dataset/row_assembly.py`) shapes training rows — but no production function currently scores one *new* window with the persisted model; that capability exists only inside `app/demo/risk_model.py`'s `predict_risk`, which is scoped to demo/synthetic data. This feature adds `risk/scoring/inference.py`, owned by the `risk` module (not `ingestion`), that loads the real persisted production artifact and scores a row shaped identically to `assemble_rows`'s training rows.

**Rationale**: Constitution Principle VI assigns each module ownership of its own logic — risk inference is `risk`'s concern, and `ingestion` should only call it, not contain it, exactly like ingestion calls into `quality`, `baseline`, `anomaly`, and `incidents` rather than reimplementing any of them. Without this addition, uploaded batches would have anomaly scores but no real risk score, silently violating spec FR-003 and constitution Principle II (no fabricated values) the moment someone was tempted to stub one in.

**Alternatives considered**: Reusing `app/demo/risk_model.py`'s `predict_risk` directly from `ingestion` (rejected — it is demo-scoped, imports demo-specific generator/column-profile modules, and mixing it into the production path would make real ingestion depend on the demo module, inverting the intended dependency direction).

## Decision: `IngestedBatch` is the production analog of MVP_CONTEXT.md Section 3's `claim_batches` table; it does not reuse `app/demo`'s `pipeline_runs.json`

**Decision**: A new `ingested_batches` table (SQLAlchemy model in `ingestion/models.py`) persists one row per upload attempt — accepted or rejected — independent of `app/demo`'s file-backed `pipeline_runs.json`, which tracks synthetic/demo pipeline runs only.

**Rationale**: MVP_CONTEXT.md Section 3 already names `claim_batches` as a core table for real ingestion, distinct from the demo module's own bookkeeping (which predates this feature and serves a different, demo-specific purpose — surviving restarts is explicitly not a design goal there, per `app/demo/router.py`'s `simulation_status` comment). A real database table (versus a JSON log file) also gives FR-006's listing endpoint proper pagination/filtering without hand-rolling it.

**Alternatives considered**: Extending `pipeline_runs.json` to also track real uploads (rejected — couples a production data-tracking requirement to a file format chosen for demo convenience, and the demo module's own docs describe that log as reset-on-regenerate, which is wrong behavior for real ingested-batch history).

## Decision: Registry re-entry is a two-line change, not a redesign

**Decision**: `backend/app/audit/registry.py`'s `EXPECTED_AUDITED_MODULES` and `backend/app/audit/schemas.py`'s `PipelineStage` enum both already carry a comment reading "re-add this line when ingestion is re-scoped and built" — this feature un-comments exactly those lines once `ingestion.batch_service` starts calling `audit.aggregation_service.append_entry` for every accepted/rejected upload.

**Rationale**: Phase 16 anticipated this exact moment and left an explicit marker rather than silently dropping the concept — honoring that marker is the minimal, intended change; anything more (e.g., restructuring the registry) would be unrequested scope.

**Alternatives considered**: None — the prior phase's own comments already specify the resolution.
