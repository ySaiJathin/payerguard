# API Contracts: Audit & History

New `audit` module router.

## `GET /history/{entity_type}/{entity_id}`

Returns the complete, chronologically-ordered audit trail for a claim, incident, or batch.

**Query params**: `page`, `page_size`, `stage` (filter by `pipeline_stage`), `start_date`, `end_date` — all optional (spec FR-007).

**Response `200 OK`**: `HistoryQueryResult` with `found: true`.

**Response `200 OK`** (empty case): `HistoryQueryResult` with `found: false` and `entries: []` — distinguishable from a normal empty page via the `found` flag (spec FR-006, SC-006).

## `GET /baseline`

Pass-through to Phase 4's current baseline.

**Query params**: `snapshot_id` — optional, returns that specific historical snapshot via Phase 4's provenance.

**Response `200 OK`**: `BaselineSnapshot` (identical shape/content to Phase 4's own `GET /baseline` — spec SC-003).

**Response `404 Not Found`**: unknown `snapshot_id`, or no baseline computed yet.

## Notes

- No endpoint in this module accepts a caller-supplied `AuditTrailEntry` — entries are populated exclusively via the internal `audit.append_entry` utility called by other modules' write paths (spec FR-009).
