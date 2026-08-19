# API Contracts: Quality Validation Layer

New `quality` module router.

## `POST /quality/validate`

Runs all category expectation suites against the most recent Phase 2 cleaned batch and computes the composite score.

**Request body**: none required (operates on the latest `data/cleaned/inpatient_cleaned.csv`); optional `{"batch_source": "..."}` to target a specific cleaned batch if continuous ingestion is ever built (the continuous-ingestion phase was removed 2026-08-18).

**Response `200 OK`**: `QualityScoreResult` (see data-model.md).

**Response `409 Conflict`**: no cleaned batch available (Phase 2 hasn't run yet) — spec FR-012.

## `GET /quality/results`

Returns the most recent `QualityScoreResult` plus its full contributing `ExpectationCheckResult[]`.

**Query params**: `band` (filter check results by PASS/WARNING/CRITICAL), `category` (filter by column category) — both optional.

**Response `200 OK`**:
```json
{
  "quality_score_result": { "...": "QualityScoreResult" },
  "check_results": [ "...ExpectationCheckResult[]" ]
}
```

**Response `404 Not Found`**: no quality run has been performed yet.

## `GET /quality/checks/{check_id}`

Returns one individual `ExpectationCheckResult` in full detail (for drill-down from the composite score, and for Phase 8's risk-dataset construction to reference specific GX failures).

**Response `200 OK`**: `ExpectationCheckResult`.

**Response `404 Not Found`**: unknown `check_id`.

## Notes

- `POST /quality/validate` is idempotent per unmodified input batch (spec SC-004) — re-running against the same cleaned batch produces a new `run_id` but identical `composite_score` and check results.
- No endpoint here writes back to `data/cleaned/`; this module is read-only with respect to Phase 2's output.
