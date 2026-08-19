# Quickstart: Anomaly Detection Benchmark

## Prerequisites

- Phase 6's `TemporalSplit` and `SelectedFeatureSet` are available.

## Run the benchmark
curl -X POST http://localhost:8000/anomaly/benchmark

```bash
```

**Expected outcome**: `200 OK` with 4 `BenchmarkResult` entries and a `ProductionModelSelection`.

## Verify leakage isolation

Run `backend/tests/anomaly/test_leakage_isolation.py` — corrupts the test-split portion, re-fits all 4 models, asserts fitted parameters/thresholds are unchanged (spec SC-001).

## Verify all 5 injection types produced ground truth

```bash
curl http://localhost:8000/anomaly/results | jq '.benchmark_results[0].per_injection_type_breakdown | keys'
```

**Expected outcome**: `["amount_spike", "distribution_shift", "duplicate_spike", "missing_value_spike", "volume_drop"]` (spec SC-002).

## Verify selection matches its own recorded numbers

```bash
curl http://localhost:8000/anomaly/results | python -c "
import json, sys
data = json.load(sys.stdin)
results = {r['model_type']: r for r in data['benchmark_results']}
selected = data['production_model_selection']['selected_model']
best_f1 = max(results.values(), key=lambda r: r['f1'])['model_type']
print('selected:', selected, '| best F1:', best_f1)
"
```

**Expected outcome**: `selected` matches `best F1` (or the documented tie-break chain if F1 ties) — spec SC-004.

## Enrich window anomaly counts

```bash
curl -X POST http://localhost:8000/anomaly/enrich-windows
curl http://localhost:8000/features/windows | jq '[.[] | .anomaly_count] | unique'
```

**Expected outcome**: no `null` values remain (spec SC-005 from Phase 5, closed out here).

## Verify enrichment idempotency

Run the enrichment call twice and diff `GET /features/windows` output before/after the second call — expect zero difference (spec SC-006).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
