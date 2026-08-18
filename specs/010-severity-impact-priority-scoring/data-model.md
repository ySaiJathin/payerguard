# Phase 1 Data Model: Severity, Business Impact, and Priority Scoring

## SeverityResult

| Field | Type | Notes |
|---|---|---|
| `quality_failure_severity` | float | 0-100, avg of CRITICAL=100/WARNING=50/PASS=0 across checks (spec FR-001) |
| `anomaly_magnitude_score` | float | 0-100, via Phase 7's percentile calibration (spec FR-002) |
| `materiality_score` | float | 0-100, from affected-claim % / amount percentile (spec FR-003) |
| `weights_used` | object | `{wq, wa, wm}`, default `{0.4, 0.4, 0.2}` |
| `severity` | float | `wq*qfs + wa*ams + wm*ms`, clamped [0,100] |
| `computed_at` | timestamp | |

## BusinessImpactResult

| Field | Type | Notes |
|---|---|---|
| `components` | array | `[{name, value: float\|null, status: "computed"\|"unavailable", reason}]` |
| `has_unavailable_components` | boolean | True if any component is `unavailable` |
| `business_impact` | float | Sum/aggregation of `status=="computed"` components only, 0-100 |
| `computed_at` | timestamp | |

**Validation rules**: A `member_harm_impact` (or equivalent) component is always present with `status: "unavailable"` unless a future dataset genuinely supports it (spec FR-006). `business_impact` never includes an `unavailable` component's implicit-zero contribution (spec SC-002).

## PriorityResult

| Field | Type | Notes |
|---|---|---|
| `severity` | float | From `SeverityResult.severity` |
| `risk` | float | Phase 9's production model score — required, no default (spec FR-009) |
| `business_impact` | float | From `BusinessImpactResult.business_impact` |
| `affected_claims_score` | float | 0-100, scaled from Phase 8's `affected_claim_pct` |
| `weights_used` | object | `{w_severity, w_risk, w_business_impact, w_affected_claims}`, default `{0.40, 0.30, 0.20, 0.10}` |
| `priority` | float | Weighted sum, clamped [0,100] |
| `computed_at` | timestamp | |

**Validation rules**: `priority` is exactly reproducible from `severity`/`risk`/`business_impact`/`affected_claims_score`/`weights_used` (spec SC-003). Computation raises a typed error rather than proceeding if `risk` is not supplied (spec FR-009, SC-004).

## Relationships

`PriorityResult` composes one `SeverityResult` and one `BusinessImpactResult` (by value, not by reference — the caller passes their computed values in) plus Phase 9's Risk Score and Phase 8's affected-claims percentage. All three result types are pure computation outputs with no owned persistent store in this feature — Phase 12 is responsible for attaching them to an `Incident` record.
