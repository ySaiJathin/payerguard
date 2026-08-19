# API Contracts: Batch File Ingestion

New `ingestion` module router. Fills the placeholder named in `backend/app/ingestion/router.py`'s existing docstring ("POST /claims/upload and related ingestion endpoints").

## `POST /claims/upload`

Accepts a raw claims file (multipart upload), validates it against the raw 197-column schema (spec FR-001, FR-002, FR-010), and — if accepted — runs it synchronously through the full existing pipeline (spec FR-003).

**Request**: `multipart/form-data`, field `file` — a pipe-delimited (or comma-delimited; the loader sniffs both, matching `app/demo/upload.py`'s existing precedent) text file.

**Response `201 Created`**: `IngestedBatch` with `status = completed` (or `failed`, if a later stage broke after acceptance — still `201` because the *upload* succeeded; the batch's own `status` field is the source of truth for pipeline outcome, never the HTTP status).

**Response `422 Unprocessable Entity`**: the file failed raw-schema validation — body includes `reason_code` and `detail` naming exactly what's wrong (spec FR-002, SC-002). An `IngestedBatch` with `status = rejected` is still persisted and audited.

**Response `413 Payload Too Large`**: exceeds the configured maximum size (spec FR-010).

## `GET /claims/batches`

Lists previously ingested batches (spec FR-006).

**Query params**: `page`, `page_size` — optional.

**Response `200 OK`**: `BatchListing`, newest-first, including rejected attempts (spec User Story 3, Acceptance Scenario 2).

## `GET /claims/batches/{batch_id}`

Returns one batch's full tracked record, including its current `status` and, once reached, references to its quality/anomaly/risk results and any incidents it produced.

**Response `200 OK`**: `IngestedBatch`.

**Response `404 Not Found`**: unknown `batch_id`.

## Notes

- No endpoint in this module accepts a caller-supplied pipeline result — every `quality_result_id`/`anomaly_result_id`/`risk_result_id`/`incident_ids` reference is populated only by this module's own orchestration calling each phase's real service function (spec FR-003, data-model.md's no-duplication rule).
- This module does not expose or modify anything under `/demo/*` — `POST /demo/upload` (existing) remains the demo/synthetic-schema upload path; `POST /claims/upload` (this feature) is the raw-schema production path. See research.md's first decision for why these are deliberately separate.
- No streaming/socket endpoint is added anywhere in this module (spec FR-008, constitution "Scope Discipline"). `watcher.py`'s existing placeholder is left as-is — out of scope per plan.md's Structure Decision.
