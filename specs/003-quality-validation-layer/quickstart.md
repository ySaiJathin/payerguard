# Quickstart: Quality Validation Layer

## Prerequisites

- Phase 2 (`002-cleaning-standardization`) has produced `data/cleaned/inpatient_cleaned.csv`.

## Run quality validation

```bash
curl -X POST http://localhost:8000/quality/validate
```

**Expected outcome**: `200 OK` with a `QualityScoreResult` whose `composite_score` is between 0 and 100.

## Verify the score is recomputable

```bash
curl http://localhost:8000/quality/results | python -c "
import json, sys
data = json.load(sys.stdin)
result = data['quality_score_result']
checks = data['check_results']
assert set(result['contributing_check_ids']) == {c['check_id'] for c in checks}, 'contributing_check_ids does not match persisted checks'
print('OK: composite score is traceable to', len(checks), 'persisted checks')
"
```

**Expected outcome**: `OK: composite score is traceable to N persisted checks` (spec SC-001, SC-005).

## Verify calibrated completeness doesn't misclassify known-sparse columns

```bash
curl "http://localhost:8000/quality/results?category=diagnosis_procedure_code" | jq '.check_results[] | select(.column_name=="ADMTG_DGNS_CD")'
```

**Expected outcome**: the `ADMTG_DGNS_CD` completeness check's `band` is `PASS` (or a documented, non-CRITICAL band) despite ~72.2% missingness, with `threshold_used` showing the calibration override rather than the universal <2%/2-5%/>5% MissingRate bands (spec SC-003).

## Verify determinism

```bash
curl -X POST http://localhost:8000/quality/validate | jq '.composite_score' > /tmp/score1
curl -X POST http://localhost:8000/quality/validate | jq '.composite_score' > /tmp/score2
diff /tmp/score1 /tmp/score2 && echo "OK: deterministic"
```

**Expected outcome**: `OK: deterministic` (spec SC-004).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
