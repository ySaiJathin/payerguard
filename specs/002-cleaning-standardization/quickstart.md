# Quickstart: Cleaning & Standardization

## Prerequisites

- Phase 1 (`001-data-profiling-foundation`) profiling has been run at least once, so `data/reports/column_categories.json` exists.
- `data/raw/inpatient.csv` present.

## Run cleaning

```bash
curl -X POST http://localhost:8000/data-engineering/clean -d '{"source": "raw"}'
```

**Expected outcome**: `200 OK` with a `CleaningRunSummary`; `data/cleaned/inpatient_cleaned.csv` and `data/reports/quality_issues.json` are created. `duplicate_rows_excluded` should be `0` against the real file (spec SC-006, matching the measured 0 duplicates in MVP_CONTEXT.md 2.2).

## Verify date standardization

```bash
python -c "
import pandas as pd, re
df = pd.read_csv('data/cleaned/inpatient_cleaned.csv')
iso = re.compile(r'^\d{4}-\d{2}-\d{2}$')
bad = df['CLM_FROM_DT'].dropna().map(lambda v: not iso.match(str(v)))
assert not bad.any(), 'found non-ISO dates'
print('OK: all CLM_FROM_DT values are ISO 8601')
"
```

**Expected outcome**: `OK: all CLM_FROM_DT values are ISO 8601` (spec SC-001).

## Verify the audit trail matches actual changes

```bash
curl http://localhost:8000/data-engineering/quality-issues | jq 'length'
```

**Expected outcome**: A non-zero count, entirely explained by missing-value cells plus any genuinely reformatted dates — cross-check a few entries against the raw file manually to confirm `original_value` matches the source (spec SC-002).

## Verify idempotency

```bash
curl -X POST http://localhost:8000/data-engineering/clean -d '{"source": "raw"}' -o /tmp/run1.json
curl -X POST http://localhost:8000/data-engineering/clean -d '{"source": "raw"}' -o /tmp/run2.json
diff data/cleaned/inpatient_cleaned.csv data/cleaned/inpatient_cleaned.csv.bak 2>/dev/null || echo "compare against a saved copy from run 1"
```

**Expected outcome**: Cleaned output and `quality_issues.json` are identical across the two runs (spec SC-004) — save a copy after run 1 to diff against run 2's output.

## Verify no fabricated values

```bash
python -c "
import pandas as pd
raw = pd.read_csv('data/raw/inpatient.csv', sep='|')
clean = pd.read_csv('data/cleaned/inpatient_cleaned.csv')
assert raw['PRVDR_NUM'].isna().sum() == clean['PRVDR_NUM'].isna().sum(), 'missing count changed — a value may have been fabricated'
print('OK: missing-value count unchanged for PRVDR_NUM')
"
```

**Expected outcome**: `OK: missing-value count unchanged for PRVDR_NUM` (spec SC-005) — repeat for other known-missingness columns from MVP_CONTEXT.md 2.2 (e.g., `CLM_DRG_CD`, `ADMTG_DGNS_CD`) as needed.

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
