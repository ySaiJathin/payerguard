# API Contracts: Feature Selection

New endpoints on the existing `features` module router.

## `POST /features/split`

Computes (or returns the existing) shared `TemporalSplit`.

**Response `200 OK`**: `TemporalSplit`.

## `POST /features/select`

Runs Stage 1 → Stage 2 → Stage 3 selection against Phase 5's feature output, using the `TemporalSplit` from the prior endpoint (computed automatically if not already present).

**Response `200 OK`**: `SelectedFeatureSet` (see data-model.md).

**Response `409 Conflict`**: Phase 5 features not available yet.

## `GET /features/selected`

Returns the most recent `SelectedFeatureSet`.

**Response `200 OK`**: `SelectedFeatureSet`.

## `GET /features/drop-decisions`

Returns the full `FeatureDropDecision[]` audit trail.

**Query params**: `stage` (filter by 1/2/3) — optional.

**Response `200 OK`**: `FeatureDropDecision[]`.

## Notes

- `GET /features/split` (no `POST`) returns the current `TemporalSplit` for Phase 7/9 to consume directly, without recomputing it.
- No endpoint here allows selection to be re-run against a caller-specified subset that includes the test-split portion — the test-isolation guarantee (spec FR-010) is enforced at the service layer, not just left to caller discipline.
