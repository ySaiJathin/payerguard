# API Contracts: Feature Engineering

New `features` module router (claim-level + window-level; Phase 6 adds selection endpoints to the same module).

## `POST /features/compute`

Computes both `ClaimFeatures` (claim grain) and `WindowFeatures` (window grain) from the current cleaned data, quality results, and baseline.

**Request body**: none required by default.

**Response `200 OK`**:
```json
{ "claims_processed": 20867, "windows_processed": 42, "generated_at": "2026-08-18T10:00:00Z" }
```

**Response `409 Conflict`**: Phase 2/3/4 outputs not available, or a window-definition mismatch was detected (spec FR-007).

## `GET /features/claims`

Returns `ClaimFeatures[]`, optionally filtered.

**Query params**: `claim_id` (single claim lookup) — optional.

**Response `200 OK`**: `ClaimFeatures[]` (or single object if `claim_id` given).

## `GET /features/windows`

Returns `WindowFeatures[]`.

**Response `200 OK`**: `WindowFeatures[]` — every row's `anomaly_count` is `null` until Phase 7/8's enrichment step runs (spec SC-004).

## `PATCH /features/windows/{window_id}/anomaly-count`

Internal enrichment endpoint, called by Phase 7/8 once anomaly scoring exists, to populate `anomaly_count` for a window without requiring this feature to recompute anything else.

**Request body**: `{ "anomaly_count": 3 }`

**Response `200 OK`**: updated `WindowFeatures` row.

## Notes

- This module does not expose a way to set `anomaly_count` to anything other than via the dedicated enrichment endpoint — it can never be set as part of `POST /features/compute` itself, keeping the "deferred until Phase 7 exists" guarantee structurally enforced, not just conventionally followed.
