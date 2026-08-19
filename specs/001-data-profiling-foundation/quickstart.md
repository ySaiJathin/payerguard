# Quickstart: Data Profiling Foundation

Validates that profiling, categorization, and sampling work end-to-end against the real dataset.

## Prerequisites

- `data/raw/inpatient.csv` present (already delivered per Phase 0 scaffolding).
- Backend dependencies installed (`pandas`, `numpy` at minimum) per `requirements.txt`.
- Run from the `backend/` app context (or via `docker-compose run backend ...` once Phase 18 containerization is validated — not required for this local check).

## Run profiling

```bash
curl -X POST http://localhost:8000/data-engineering/profile
```

**Expected outcome**: `200 OK` with `total_rows: 58066`, `total_columns: 197`, `unique_claim_count: 20867`, `unique_beneficiary_count: 5699`, `duplicate_row_count: 0` — matching MVP_CONTEXT.md Section 2.2 (spec SC-003). `data/reports/profiling_report.md` and `.json` and `column_categories.json` exist on disk.

## Inspect the report

```bash
curl http://localhost:8000/data-engineering/profile | jq '.columns | length'
```

**Expected outcome**: `197` — every column present with a category assigned (spec SC-002).

## Generate the working sample

```bash
curl -X POST http://localhost:8000/data-engineering/sample -d '{"seed": 42, "target_claim_fraction": 0.08}'
```

**Expected outcome**: `200 OK`, `data/sampled/inpatient_sample.csv` created, `claims_included` ≈ 1,669 (8% of 20,867), and `data/raw/inpatient.csv` unchanged (byte-for-byte — verify with a checksum before/after, spec SC-004).

## Verify reproducibility

Re-run the same sample request with the same `seed`/`target_claim_fraction` and diff the two output files.

**Expected outcome**: identical `claims_included` and identical file contents (spec SC-005).

## Verify claim consistency

```bash
python -c "
import pandas as pd
df = pd.read_csv('data/sampled/inpatient_sample.csv', sep='|')
raw = pd.read_csv('data/raw/inpatient.csv', sep='|')
sampled_claims = set(df['CLM_ID'])
for cid in sampled_claims:
    assert (raw[raw.CLM_ID == cid].shape[0]) == (df[df.CLM_ID == cid].shape[0]), f'claim {cid} split across sample boundary'
print('OK: no split claims')
"
```

**Expected outcome**: `OK: no split claims` — confirms no claim was partially included (spec SC-004, Edge Cases).

Full endpoint request/response shapes are defined in [contracts/api.md](./contracts/api.md); entity field definitions are in [data-model.md](./data-model.md).
