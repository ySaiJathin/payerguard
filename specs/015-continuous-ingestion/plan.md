# Implementation Plan: Continuous Ingestion

**Branch**: `015-continuous-ingestion` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-continuous-ingestion/spec.md`

## Summary

Build the `ingestion` module (the first module named in Section 3's architecture but the last to be implemented, since it needed the full pipeline to exist first): manual batch upload and a watched-folder poller, both routing through Phase 2-9's existing service functions unchanged, with schema/empty/duplicate-file validation, overlap detection against existing historical data, and large-file handling — explicitly file-based, never a live streaming endpoint.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI's `UploadFile` (streaming/chunked upload support for FR-010), `watchdog` or a simple polling loop for the folder-watch mode, hashlib for duplicate-content detection; calls Phase 2/3/5/7/9/12's existing service functions directly

**Storage**: `claim_batches` table (MVP_CONTEXT.md Section 3 core tables) for `IngestedBatch` records; watched-folder processed-file tracking via a small persisted set (DB table or a `data/ingestion/processed_files.json` manifest)

**Testing**: pytest — a code-reuse audit test asserting no duplicated pipeline logic exists in this module (SC-001); malformed/empty/duplicate upload tests (SC-002, SC-003); an end-to-end watcher test (SC-004); an API-surface audit for zero streaming endpoints (SC-005); a large-file fixture test (SC-006)

**Target Platform**: Same as prior phases; watched-folder mode runs as a background task/process within the same containerized backend service (no separate service)

**Performance Goals**: Large-file handling via chunked reads, avoiding loading the entire file into memory at once where the underlying pandas/file operations allow it

**Constraints**: Zero live socket/streaming surface (FR-011, SC-005); no duplicated pipeline logic (FR-001, SC-001); overlap detection before silent conflict (FR-007)

**Scale/Scope**: Batch sizes ranging from small test uploads to significantly-larger-than-`inpatient.csv` fixtures for the large-file test

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — reuses already-selected production models unchanged | PASS |
| II. No Fabricated Values | Applies — new batches are scored with the same real, computed pipeline, no shortcuts | PASS |
| III. Deterministic-First, ML-Second | Applies — new batches go through Phase 3's deterministic floor before any ML scoring, same as historical data | PASS |
| IV. Human-in-the-Loop | Applies indirectly — findings from new batches still flow through Phase 12's HITL gate unchanged | PASS |
| V. Constrained, Auditable Remediation | Not directly applicable | PASS |
| VI. Modular Backend, No Monolith | Applies — new `ingestion` module, calling into (never duplicating) every prior module's logic | PASS |
| VII. Temporal Integrity | Applies — FR-007's overlap detection directly protects chronological data integrity; FR-008 keeps new-batch scoring from silently redefining "historical" | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/015-continuous-ingestion/
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
│   └── ingestion/
│       ├── __init__.py
│       ├── upload_handler.py       # FR-001, FR-002, FR-003, FR-010
│       ├── duplicate_detection.py  # FR-004 — content-hash based
│       ├── watched_folder.py       # FR-005, FR-006 — polling loop, no sockets
│       ├── overlap_detection.py    # FR-007
│       ├── pipeline_orchestrator.py # FR-001, FR-008, FR-009 — calls existing Phase 2-9/12 functions
│       ├── schemas.py              # IngestedBatch, BatchProcessingResult, DateRangeOverlapFlag
│       └── router.py               # POST /ingestion/upload, GET /ingestion/batches
└── tests/
    └── ingestion/
        ├── test_pipeline_reuse_audit.py   # SC-001
        ├── test_malformed_empty_rejection.py  # SC-002
        ├── test_duplicate_detection.py         # SC-003
        ├── test_watched_folder_e2e.py            # SC-004
        ├── test_no_streaming_endpoints.py         # SC-005
        └── test_large_file_handling.py             # SC-006

data/
├── incoming/          # watched folder
└── ingestion/processed_files.json
```

**Structure Decision**: New `ingestion` module that is purely an orchestration layer — `pipeline_orchestrator.py` imports and calls Phase 2/3/5/7/9/12's existing functions rather than reimplementing any of them, directly satisfying SC-001's reuse-audit requirement.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
