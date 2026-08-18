# API Contracts: Continuous Ingestion

New `ingestion` module router.

## `POST /ingestion/upload`

Uploads a new batch file for processing.

**Request**: multipart file upload (`inpatient`-schema pipe-delimited file); optional `force_reprocess: bool` field.

**Response `202 Accepted`**: `IngestedBatch` (status `processing`) — processing runs asynchronously; poll `GET /ingestion/batches/{batch_id}`.

**Response `422 Unprocessable Entity`**: malformed schema or empty file — `IngestedBatch` with `processing_status: "rejected_malformed"` or `"rejected_empty"`.

**Response `409 Conflict`**: duplicate content hash without `force_reprocess` — `IngestedBatch` with `processing_status: "rejected_duplicate"`.

## `GET /ingestion/batches`

Lists all `IngestedBatch` records.

**Query params**: `processing_status`, `ingestion_method` — optional.

**Response `200 OK`**: `IngestedBatch[]`.

## `GET /ingestion/batches/{batch_id}`

**Response `200 OK`**: `IngestedBatch` plus its `BatchProcessingResult` if completed.

## `GET /ingestion/overlap-flags`

Lists unreviewed `DateRangeOverlapFlag` records.

**Response `200 OK`**: `DateRangeOverlapFlag[]`.

## `POST /ingestion/watched-folder/start` / `POST /ingestion/watched-folder/stop`

Starts/stops the watched-folder polling loop (for operator control / testing).

**Response `200 OK`**: `{ "watching": true, "poll_interval_seconds": 60, "folder": "data/incoming" }`.

## Notes

- No endpoint in this module accepts a persistent socket connection or streams claims one-at-a-time — every ingestion path is a discrete file (spec FR-011, SC-005).
