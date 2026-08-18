# Quickstart: Risk Model Benchmark

## Prerequisites

- Phase 8's risk dataset and Phase 6's `TemporalSplit` are available.

## Run the benchmark

```bash
curl -X POST http://localhost:8000/risk/benchmark
```

**Expected outcome**: `200 OK` with 3 `RiskBenchmarkResult` entries and a `ProductionRiskModelSelection`.

## Verify leakage isolation

Run `backend/tests/risk/benchmark/test_leakage_isolation.py` (spec SC-001).

## Verify selection matches the documented ranking rule

```bash
curl http://localhost:8000/risk/benchmark/results | python -c "
import json, sys
data = json.load(sys.stdin)
results = {r['model_type']: r for r in data['benchmark_results']}
selected = data['production_model_selection']['selected_model']
print('selected:', selected)
for m, r in results.items():
    print(m, 'recall=', r['recall'], 'pr_auc=', r['pr_auc'])
"
```

**Expected outcome**: `selected` is the highest-recall model among those clearing the PR-AUC floor (spec SC-003).

## Verify split consistency with Phase 6

Run `backend/tests/risk/benchmark/test_split_consistency.py`, which asserts every row's split assignment in this benchmark matches Phase 6's `TemporalSplit` directly (spec SC-006).

## Verify calibration is reported

```bash
curl http://localhost:8000/risk/benchmark/results | jq '[.benchmark_results[].calibration_brier_score]'
```

**Expected outcome**: three numeric values, one per model (spec SC-005).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
