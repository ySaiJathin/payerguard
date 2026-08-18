# API Contracts: Cleaning & Standardization

Extends the `data_engineering` module router established in Phase 1.

## `POST /data-engineering/clean`

Runs schema validation → dtype conversion → missing-value handling → duplicate detection → invalid-value detection → date standardization against `data/raw/inpatient.csv` (or, optionally, the Phase 1 sample for fast iteration), and persists the cleaned dataset plus the audit trail.

**Request body**:
```json
{ "source": "raw" }
```
`source` is `"raw"` (default) or `"sampled"` — selects between `data/raw/inpatient.csv` and Phase 1's `data/sampled/inpatient_sample.csv`.

**Response `200 OK`**: `CleaningRunSummary` (see data-model.md).

**Response `422 Unprocessable Entity`**: `SchemaValidationResult.passed = false` — response body includes `missing_columns`/`unexpected_columns`.

## `GET /data-engineering/quality-issues`

Returns the `QualityIssueRecord[]` audit trail from the most recent cleaning run, with optional filtering.

**Query params**: `quality_issue` (filter by issue type), `column_name` (filter by column) — both optional.

**Response `200 OK`**: `QualityIssueRecord[]`.

**Response `404 Not Found`**: no cleaning run has been performed yet.

## `GET /data-engineering/clean`

Returns the most recent `CleaningRunSummary` without re-running cleaning.

**Response `200 OK`**: `CleaningRunSummary`.

**Response `404 Not Found`**: no cleaning run has been performed yet.

## Notes

- These endpoints depend on `POST /data-engineering/profile` (Phase 1) having produced `column_categories.json` at least once — if absent, `POST /data-engineering/clean` responds `409 Conflict` with a message directing the caller to run profiling first.
- No endpoint accepts an arbitrary file path — matches the single-dataset MVP scope (constitution "Scope Discipline").
