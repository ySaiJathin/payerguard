# Quickstart: Historical Baseline

## Prerequisites

- Phase 2 cleaned output and Phase 3 quality results are available.

## Compute the baseline

```bash
curl -X POST http://localhost:8000/baseline/compute
```

**Expected outcome**: `200 OK` with a `BaselineSnapshot`.

## Verify amount statistics against documented ground truth

```bash
curl http://localhost:8000/baseline | jq '.amount_baselines[] | select(.column_name=="CLM_PMT_AMT")'
```

**Expected outcome**: `mean` ≈ 13638.31, `median` ≈ 1481.72, `std` ≈ 35993.91 (spec SC-001, allowing only for Phase 2 cleaning-driven adjustments such as excluded duplicates).

## Verify no processing-time/SLA field exists

```bash
curl http://localhost:8000/baseline | python -c "
import json, sys
snap = json.load(sys.stdin)
blob = json.dumps(snap).lower()
assert 'processing_time' not in blob and 'sla' not in blob and 'turnaround' not in blob
print('OK: no processing-time/SLA field present')
"
```

**Expected outcome**: `OK: no processing-time/SLA field present` (spec SC-005).

## Verify length-of-stay exclusion reporting

```bash
curl http://localhost:8000/baseline | jq '.length_of_stay_baseline'
```

**Expected outcome**: `claims_excluded_missing_dates` is present and is a real computed count (spec SC-004).

## Verify no hardcoding (mutate-and-recompute test)

Run the automated test `backend/tests/baseline/test_no_hardcoding.py`, which mutates a fixture's amount column and asserts the recomputed baseline's `mean`/`median` change accordingly (spec SC-002).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
