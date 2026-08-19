# API Contracts: Risk Model Benchmark

New endpoints on the `risk` module router (alongside Phase 8's `dataset` endpoints).

## `POST /risk/benchmark`

Runs the full benchmark: fit all 3 models on train, tune on validation, evaluate on test, select production model.

**Response `200 OK`**:
```json
{
  "benchmark_results": ["...RiskBenchmarkResult[]"],
  "production_model_selection": "...ProductionRiskModelSelection"
}
```

**Response `409 Conflict`**: Phase 8's risk dataset or Phase 6's `TemporalSplit` not available.

## `GET /risk/benchmark/results`

Returns the most recent benchmark's results, or a specific versioned run.

**Query params**: `risk_dataset_version` (optional).

**Response `200 OK`**: same shape as above.

**Response `404 Not Found`**: no benchmark run yet (for the requested version, if specified).

## Notes

- Consistent with Phase 8, re-running `POST /risk/benchmark` after new data is loaded (the continuous-ingestion phase was removed 2026-08-18) produces a new versioned result set (spec FR-009) rather than silently overwriting prior results.
