# API Contracts: Severity, Business Impact, and Priority Scoring

New convenience endpoint on the `risk` module router, primarily for manual invocation/testing — Phase 12 calls the underlying service functions directly, in-process.

## `POST /risk/score`

Computes Severity, Business Impact, and Priority for a given window/incident's already-resolved inputs.

**Request body**:
```json
{
  "quality_check_results": ["...from Phase 3"],
  "anomaly_score": 0.87,
  "affected_claim_pct": 0.12,
  "affected_claims_amounts": [1200.50, 3400.00],
  "risk_score": 0.65,
  "weights": { "severity": null, "priority": null }
}
```
`weights` fields are optional overrides; `null`/omitted uses the documented defaults.

**Response `200 OK`**:
```json
{
  "severity_result": "...SeverityResult",
  "business_impact_result": "...BusinessImpactResult",
  "priority_result": "...PriorityResult"
}
```

**Response `422 Unprocessable Entity`**: `risk_score` missing (spec FR-009), or a supplied weight set fails validation (spec FR-010).

## Notes

- This endpoint is a thin wrapper for manual testing/inspection; production usage is Phase 12 calling `severity()`/`business_impact()`/`priority()` directly as part of incident creation, and Phase 14 calling them again post-remediation (spec FR-011).
