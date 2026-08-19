# API Contracts: Audit & History

New `audit` module router.

## `GET /history/{entity_type}/{entity_id}`

Returns the complete, chronologically-ordered audit trail for a claim, incident, or batch.

**Query params**: `page`, `page_size`, `stage` (filter by `pipeline_stage`), `start_date`, `end_date` — all optional (spec FR-007).

**Response `200 OK`**: `HistoryQueryResult` with `found: true`.

**Response `200 OK`** (empty case): `HistoryQueryResult` with `found: false` and `entries: []` — distinguishable from a normal empty page via the `found` flag (spec FR-006, SC-006).

## `GET /audit/baseline`

Pass-through to Phase 4's current baseline.

**Query params**: `snapshot_id` — optional, returns that specific historical snapshot via Phase 4's provenance.

**Response `200 OK`**: `BaselineSnapshot` (identical shape/content to Phase 4's own `GET /baseline` — spec SC-003).

**Response `404 Not Found`**: unknown `snapshot_id`, or no baseline computed yet.

> **Path deviation, recorded during implementation.** This endpoint was originally specified as `GET /baseline`, but Phase 4's `baseline` router already registers that exact path on the same application. Mounting a duplicate would make the served handler depend on router *include order* rather than intent — FastAPI matches the first registered route and emits no warning — so the audit copy is mounted at `/audit/baseline`. The response content is unaffected: both paths call the same Phase 4 functions, which is what SC-003's parity requirement actually turns on.

## Notes

- No endpoint in this module accepts a caller-supplied `AuditTrailEntry` — entries are populated exclusively via the internal `audit.append_entry` utility called by other modules' write paths (spec FR-009).
- `GET /history/...` returns `200` for an unknown entity, with `found: false` — never `404`. That is deliberate: a `404` would be indistinguishable from a wrong URL, whereas the `found` flag answers "does this entity have any recorded activity" unambiguously (spec FR-006, SC-006).
- The `pipeline_stage` enum omits `ingestion`, which data-model.md lists. The continuous-ingestion phase was removed 2026-08-18 and `app/ingestion/` has no write path, so no entry could ever carry that stage.
