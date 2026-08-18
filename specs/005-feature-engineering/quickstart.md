# Quickstart: Feature Engineering

## Prerequisites

- Phase 2 cleaned output, Phase 3 quality results, and Phase 4 baseline snapshot are available.

## Compute features

```bash
curl -X POST http://localhost:8000/features/compute
```

**Expected outcome**: `200 OK` with `claims_processed` ≈ 20,867.

## Verify no fabricated claim features

```bash
curl "http://localhost:8000/features/claims?claim_id=<a-claim-with-missing-discharge-date>" | jq '.length_of_stay_days'
```

**Expected outcome**: `null`, not a defaulted number (spec SC-001).

## Verify anomaly_count is null, not zero, pre-Phase-7

```bash
curl http://localhost:8000/features/windows | jq '[.[] | .anomaly_count] | unique'
```

**Expected outcome**: `[null]` — every window's `anomaly_count` is null (spec SC-004).

## Verify unseen-category handling

Run the automated test `backend/tests/features/test_categorical_encoding.py`, which fits an encoder on a fixture then encodes a claim with a category value not present during fitting, asserting it maps to the documented unknown bucket without error (spec SC-005).

## Verify deviation features trace back to the baseline

```bash
curl http://localhost:8000/features/windows | jq '.[0].volume_deviation'
curl http://localhost:8000/baseline | jq '.volume_baseline.windows[0].claim_count'
```

**Expected outcome**: the deviation figure is consistent with recomputing `(window.claim_count - baseline.expected_count)` by hand from the two responses (spec SC-003).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
