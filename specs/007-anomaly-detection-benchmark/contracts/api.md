# API Contracts: Anomaly Detection Benchmark

New `anomaly` module router.

## `POST /anomaly/benchmark`

Runs the full benchmark: fit all 4 models on train, calibrate on validation, inject synthetic anomalies into validation/test copies, evaluate on test, select the production model.

**Response `200 OK`**:
```json
{
  "benchmark_results": ["...BenchmarkResult[]"],
  "production_model_selection": "...ProductionModelSelection"
}
```

**Response `409 Conflict`**: Phase 6's `TemporalSplit`/`SelectedFeatureSet` not available yet.

## `GET /anomaly/results`

Returns the most recent benchmark's `BenchmarkResult[]` and `ProductionModelSelection`.

**Response `200 OK`**: same shape as above.

**Response `404 Not Found`**: no benchmark run yet.

## `POST /anomaly/enrich-windows`

Applies the selected production model to real window data and populates `WindowFeatures.anomaly_count` via Phase 5's `PATCH /features/windows/{window_id}/anomaly-count`.

**Response `200 OK`**:
```json
{ "windows_enriched": 42, "model_used": "hbos" }
```

**Response `409 Conflict`**: no `ProductionModelSelection` exists yet (benchmark hasn't run).

## Notes

- `POST /anomaly/enrich-windows` is idempotent (spec FR-011, SC-006) — safe to call repeatedly.
- The injected/synthetic evaluation data used inside `POST /anomaly/benchmark` is never persisted as if it were real claims data — it exists only within the benchmark run's scope and is not written to `data/cleaned/` or any claim-facing store.
