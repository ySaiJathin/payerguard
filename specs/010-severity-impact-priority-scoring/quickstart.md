# Quickstart: Severity, Business Impact, and Priority Scoring

## Score a sample incident

```bash
curl -X POST http://localhost:8000/risk/score -d '{
  "quality_check_results": [{"band":"CRITICAL"},{"band":"PASS"},{"band":"WARNING"}],
  "anomaly_score": 0.87,
  "affected_claim_pct": 0.12,
  "affected_claims_amounts": [1200.50, 3400.00],
  "risk_score": 0.65
}'
```

**Expected outcome**: `200 OK` with `severity_result.severity` reproducible by hand as `0.4*avg(100,0,50) + 0.4*anomaly_magnitude + 0.2*materiality`.

## Verify Business Impact "unavailable ≠ 0"

```bash
curl -X POST http://localhost:8000/risk/score -d '{...as above...}' | jq '.business_impact_result'
```

**Expected outcome**: `components` includes at least one entry with `status: "unavailable"` (e.g., member-harm), and `business_impact` is computed only from `status: "computed"` entries (spec SC-002).

## Verify missing Risk fails explicitly

```bash
curl -X POST http://localhost:8000/risk/score -d '{"quality_check_results": [], "anomaly_score": 0.1, "affected_claim_pct": 0.0, "affected_claims_amounts": []}'
```

**Expected outcome**: `422 Unprocessable Entity` — `risk_score` is required (spec SC-004).

## Verify Priority reproducibility

```bash
curl -X POST http://localhost:8000/risk/score -d '{...}' | jq '.priority_result'
```

**Expected outcome**: `priority = 0.40*severity + 0.30*risk + 0.20*business_impact + 0.10*affected_claims_score`, matching by hand computation (spec SC-003).

## Verify reusability post-remediation

Run `backend/tests/risk/scoring/test_reusability_post_remediation.py`, which calls the same scoring functions twice with pre- and post-remediation input values and asserts both calls succeed identically in shape (spec SC-005).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
