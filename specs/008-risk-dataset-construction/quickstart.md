# Quickstart: Risk Dataset Construction

## Prerequisites

- Phase 7's `POST /anomaly/enrich-windows` has been run (no null `anomaly_count` remains).

## Build the dataset

```bash
curl -X POST http://localhost:8000/risk/dataset/build
```

**Expected outcome**: `200 OK` with `rows_built` matching Phase 4/5's window count and a `label_distribution`.

## Verify provenance (no independently recomputed fields)

Run `backend/tests/risk/dataset/test_row_provenance.py`, which cross-checks each `RiskDatasetRow` field against the exact upstream phase output it should equal (spec SC-001).

## Verify label reproducibility

```bash
curl http://localhost:8000/risk/dataset/label-formula > /tmp/formula.json
curl http://localhost:8000/risk/dataset | python -c "
import json, sys
rows = json.load(sys.stdin)
formula = json.load(open('/tmp/formula.json'))
w = formula['weights']
# recompute IRI by hand for the first row and compare
r = rows[0]
print('stored label:', r['investigation_risk_label'])
"
```

**Expected outcome**: manual recomputation using the documented formula matches the stored label for every row (spec SC-002) — the full check is automated in `backend/tests/risk/dataset/test_label_reproducibility.py`.

## Verify the formula document references Section 2.4

```bash
curl http://localhost:8000/risk/dataset/label-formula | jq -r '.rationale_text' | grep -i "section 2.4"
```

**Expected outcome**: a match, confirming the artifact explicitly cites the no-SLA-field reasoning (spec SC-003).

## Verify zero-claim windows are labeled 0

Run `backend/tests/risk/dataset/test_zero_claim_window_label.py` against a fixture window with `claim_count = 0` (spec SC-004).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
