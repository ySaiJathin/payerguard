# Implementation Plan: Batch File Ingestion

**Branch**: `017-batch-file-ingestion` | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/017-batch-file-ingestion/spec.md`

## Summary

Build the real `ingestion` module — currently three unimplemented placeholder files (`router.py`, `service.py`, `watcher.py`) — so a raw, 197-column, pipe-delimited claims extract can be uploaded manually and repeatedly, validated against the raw (not cleaned) schema before anything runs, and driven end-to-end through the already-built Phase 2–12 pipeline (cleaning → quality → baseline → features → anomaly → risk → severity/priority → incident creation) by calling each phase's existing service functions directly, never re-implementing them. Every upload — accepted or rejected — is persisted as its own `IngestedBatch` record and appended to the audit trail, closing the exact gap `backend/app/audit/registry.py` and `schemas.py` have stood ready for since Phase 16 (`ingestion` was deliberately left out of `EXPECTED_AUDITED_MODULES` / `PipelineStage` with a comment to re-add it once this module exists).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI (router, `UploadFile`), pandas (parse/validate the uploaded frame), SQLAlchemy (persist `IngestedBatch`), pydantic (schemas) — calls into `data_engineering.cleaning_service.run_cleaning`, `quality.scoring_service.run_validation`, `baseline.snapshot_service.compute_baseline_snapshot`, `features.claim_feature_service`/`window_feature_service`, `anomaly.window_enrichment.enrich_windows`, `risk.scoring.*`, `incidents.service.create_incident`, and `audit.aggregation_service.append_entry` — no new pipeline logic, only orchestration.

**Storage**: New `ingested_batches` table (MVP_CONTEXT.md Section 3 core tables already name `claim_batches` for this purpose); uploaded file bytes persisted under `data/raw/uploads/` (mirroring the existing `data/raw/inpatient.csv` convention, kept separate from `app/demo`'s `data/demo/synthetic/uploads/`, which is a different schema entirely).

**Testing**: pytest — schema-conformance rejection tests (SC-002), a full-pipeline fixture test asserting real quality/anomaly/risk/incident output from an uploaded frame (SC-001), a repeated-upload no-collision test (SC-003), an induced-mid-pipeline-failure status test (SC-004), and an audit-completeness test extending Phase 16's existing registry check now that `ingestion` re-enters `EXPECTED_AUDITED_MODULES` (SC-005).

**Target Platform**: Same as prior phases (FastAPI backend service, local dev via Docker Compose per MVP_CONTEXT.md Section 3)

**Project Type**: Backend module — fills in the existing `backend/app/ingestion/` module boundary (MVP_CONTEXT.md Section 3's module list already names it; only the files are placeholders)

**Performance Goals**: Synchronous processing of a single upload within one request/response cycle, sized for this dataset's realistic scale (tens of thousands of rows, matching the real `inpatient.csv` profile in MVP_CONTEXT.md Section 2.2) — no specific throughput target beyond "one upload completes in one call," consistent with the precedent already set by `app/demo/router.py`'s `POST /demo/upload`.

**Constraints**: Raw-schema validation MUST run before any pipeline stage (FR-002); every phase's existing service function is reused, never duplicated (FR-003, constitution Principle VI); batch status MUST never report "completed" for a partial failure (FR-007, constitution Principle II); no live/streaming/socket path and no random-claim generator (FR-008, constitution "Scope Discipline"); every upload attempt is audited (FR-009, constitution Principle V).

**Scale/Scope**: One new module (`backend/app/ingestion/`) plus one registry re-entry each in `backend/app/audit/registry.py` and `backend/app/audit/schemas.py` (`PipelineStage`) to un-comment the `ingestion` lines those files already have staged. No changes to Phases 2–16's own logic — only new call sites into their existing public service functions.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — this feature invokes the already-benchmarked, already-selected anomaly and risk models (Phases 7, 9); it selects nothing new | PASS |
| II. No Fabricated Values | Applies directly — FR-007/SC-004 require honest status reporting on partial failure; every score an uploaded batch produces comes from the real pipeline stages, never a placeholder | PASS |
| III. Deterministic-First, ML-Second | Applies — FR-003 orders cleaning and Great Expectations validation ahead of anomaly/risk scoring, same order every other phase already established | PASS |
| IV. Human-in-the-Loop | Not directly applicable — this feature stops at incident creation (Phase 12); it does not touch accept/reject/remediation | PASS |
| V. Constrained, Auditable Remediation | Related — FR-009 makes ingestion itself a fully audited step, completing the audit trail's coverage rather than leaving a gap at the very first stage | PASS |
| VI. Modular Backend, No Monolith | Applies directly — fills the existing `ingestion` module boundary named in Section 3; owns its own models/schemas/service/router; calls other modules' public functions rather than reaching into their internals | PASS |
| VII. Temporal Integrity | Applies — an uploaded batch is windowed and baseline-compared using the same chronological logic Phase 4/5 already enforce; this feature introduces no new time-ordering logic of its own | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/017-batch-file-ingestion/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md   # /speckit.tasks — not created here
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── models.py            # FR-004 — IngestedBatch ORM model (fills claims.py's twin placeholder for claim_batches)
│   │   ├── schemas.py           # IngestedBatch, BatchUploadRejection, BatchListing
│   │   ├── upload_validation.py # FR-001, FR-002, FR-010 — raw-schema conformance check, size/row-count bounds
│   │   ├── pipeline_runner.py   # FR-003 — orchestrates Phase 2-12's existing service calls in order
│   │   ├── batch_service.py     # FR-004, FR-005, FR-006, FR-007 — persist/list/status-track IngestedBatch
│   │   └── router.py            # POST /claims/upload, GET /claims/batches
│   ├── risk/
│   │   └── scoring/
│   │       └── inference.py     # NEW — loads Phase 9's persisted production model, scores one newly-assembled
│   │                             #   row the same shape `risk.dataset.row_assembly.assemble_rows` produces for
│   │                             #   training. Owned by `risk`, not `ingestion` (Principle VI); see research.md.
│   └── audit/
│       ├── registry.py          # FR-009 — un-comment `ingestion` in EXPECTED_AUDITED_MODULES (already staged)
│       └── schemas.py           # FR-009 — un-comment `ingestion` in PipelineStage (already staged)
└── tests/
    └── ingestion/
        ├── test_upload_validation.py     # SC-002
        ├── test_full_pipeline_upload.py  # SC-001
        ├── test_repeated_upload.py       # SC-003
        ├── test_partial_failure_status.py # SC-004
        └── test_audit_coverage.py         # SC-005, extends Phase 16's registry-completeness test
```

**Structure Decision**: Fills the existing `ingestion` module boundary in place — no new top-level directory. `watcher.py` (the third existing placeholder file) is left untouched: it names a folder-watching/continuous-ingestion concept that spec `015-continuous-ingestion`'s removal ruled out of scope (MVP_CONTEXT.md Section 4, constitution "Scope Discipline"), so this feature does not implement it and a follow-up decision to delete or repurpose the file is left for later rather than assumed here.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
