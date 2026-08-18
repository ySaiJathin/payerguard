# API Contracts: Data Profiling Foundation

Per the modular backend architecture (MVP_CONTEXT.md Section 3, constitution Principle VI), the `data_engineering` module owns its own router. These two endpoints are the module's external surface for this feature; internal service functions (`profiling_service`, `categorization`, `sampling_service`) are not part of the contract.

## `POST /data-engineering/profile`

Triggers a fresh profiling run against `data/raw/inpatient.csv` and persists the report artifacts.

**Request body**: none required (source file path is fixed to the in-scope dataset per constitution "Scope Discipline"); an optional `{"force_refresh": true}` may be accepted to bypass any future caching layer — not required for this MVP pass.

**Response `200 OK`**:
```json
{
  "generated_at": "2026-08-18T10:00:00Z",
  "total_rows": 58066,
  "total_columns": 197,
  "unique_claim_count": 20867,
  "unique_beneficiary_count": 5699,
  "duplicate_row_count": 0,
  "report_markdown_path": "data/reports/profiling_report.md",
  "report_json_path": "data/reports/profiling_report.json",
  "column_categories_path": "data/reports/column_categories.json"
}
```

**Response `422 Unprocessable Entity`**: source file missing, unreadable, or column count ≠ 197 (spec FR-013, Edge Cases).

## `GET /data-engineering/profile`

Returns the most recently generated `ProfilingReport` (see data-model.md) without re-running profiling.

**Response `200 OK`**: full `ProfilingReport` JSON body.

**Response `404 Not Found`**: no profiling run has been performed yet.

## `POST /data-engineering/sample`

Generates (or regenerates) the working sample under `data/sampled/`.

**Request body**:
```json
{
  "seed": 42,
  "target_claim_fraction": 0.08
}
```
Both fields optional; defaults per research.md ("Decision: Sampling by claim with a fixed seed").

**Response `200 OK`**: `SampleManifest` JSON body (see data-model.md).

**Response `422 Unprocessable Entity`**: `target_claim_fraction` would select zero claims, or source file is missing (spec Edge Cases).

## Notes

- All three endpoints are read-only with respect to `data/raw/inpatient.csv` — none of them accept a request body field capable of pointing at a different source file, matching the single-dataset MVP scope.
- No authentication/authorization contract is defined here — this MVP has no multi-tenant or external-user access model yet; these endpoints are for internal pipeline operation and human reviewers.
