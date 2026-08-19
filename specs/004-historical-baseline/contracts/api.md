# API Contracts: Historical Baseline

New `baseline` module router.

## `POST /baseline/compute`

Computes a fresh `BaselineSnapshot` from the current cleaned historical data (Phase 2 output) plus Phase 3's quality results.

**Request body**: none required by default; optional `{"window_definition": "daily"}` override.

**Response `200 OK`**: `BaselineSnapshot` (see data-model.md).

**Response `409 Conflict`**: Phase 2 cleaned output or Phase 3 quality results not available yet.

## `GET /baseline`

Returns the most recent `BaselineSnapshot`.

**Response `200 OK`**: `BaselineSnapshot`.

**Response `404 Not Found`**: no baseline computed yet.

## `GET /baseline/history`

Lists prior `BaselineSnapshot` provenance records (`snapshot_id`, `source_file`, `source_row_count`, `computed_at`) — supports recomputation over time as further batches are loaded (the continuous-ingestion phase was removed 2026-08-18) and Phase 21's future drift comparisons.

**Response `200 OK`**: `BaselineSnapshot[]` (provenance fields only, not full statistics, to keep the listing response light).

## Notes

- `/baseline` and `/history` and `/baseline` read endpoints named in MVP_CONTEXT.md Phase 16 ("`/history` and `/baseline` read endpoints") are the audit-facing counterparts to these; Phase 16's feature is responsible for exposing the full historical/audit view, while this module owns computing and storing the snapshots themselves.
