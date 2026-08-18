# Quickstart: Feature Selection

## Prerequisites

- Phase 5 `ClaimFeatures`/`WindowFeatures` are available.

## Compute the split and run selection

```bash
curl -X POST http://localhost:8000/features/split
curl -X POST http://localhost:8000/features/select
```

**Expected outcome**: `200 OK` on both; `SelectedFeatureSet` returned with `stage1_drop_count`/`stage2_drop_count`/`stage3_drop_count` all > 0.

## Verify known constant/null columns were dropped

```bash
curl http://localhost:8000/features/drop-decisions?stage=1 | jq '[.[] | .feature_name]' | grep -E "NCH_CLM_TYPE_CD|OT_PHYSN_UPIN"
```

**Expected outcome**: both appear in Stage 1's drop list with a specific reason (spec SC-002).

## Verify test-set isolation

Run the automated test `backend/tests/features/selection/test_leakage_isolation.py`, which corrupts the test-split portion of a fixture and asserts Stage 2/3 outputs and the final `SelectedFeatureSet` are byte-identical to a run against the uncorrupted fixture (spec SC-003).

## Verify anomaly_count exemption

```bash
curl http://localhost:8000/features/drop-decisions | jq '[.[] | .feature_name] | index("anomaly_count")'
```

**Expected outcome**: `null` (not found in any drop list) — confirms `anomaly_count` was never dropped for missingness despite being 100% null pre-Phase-7 (spec SC-005).

## Verify every drop has a specific reason

```bash
curl http://localhost:8000/features/drop-decisions | jq '[.[] | select(.reason == null or .reason == "")] | length'
```

**Expected outcome**: `0` (spec SC-004).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
