# Phase 1 Data Model: Revalidation

## RevalidationRun

| Field | Type | Notes |
|---|---|---|
| `revalidation_id` | string | |
| `incident_id` | string | |
| `remediation_run_id` | string | The specific `RemediationRun` (Phase 13) being revalidated |
| `recomputed_quality_results` | ExpectationCheckResult[] | Fresh, from Phase 3 (spec FR-001) |
| `recomputed_anomaly_score` | float | Fresh, from Phase 7 (spec FR-002) |
| `recomputed_risk_score` | float | Fresh, from Phase 9 (spec FR-003) |
| `recomputed_severity_business_impact_priority` | object | Fresh, from Phase 10 (spec FR-004) |
| `anomaly_model_version` / `risk_model_version` | string | From Phase 7/9's `ProductionModelSelection` (spec FR-010) |
| `started_at` / `completed_at` | timestamp | |

## BeforeAfterComparison

| Field | Type | Notes |
|---|---|---|
| `revalidation_id` | string | |
| `quality_before` / `quality_after` / `quality_delta` | float | |
| `anomaly_before` / `anomaly_after` / `anomaly_delta` | float | |
| `risk_before` / `risk_after` / `risk_delta` | float | |
| `severity_before` / `severity_after` / `severity_delta` | float | |
| `priority_before` / `priority_after` / `priority_delta` | float | |

**Validation rules**: `*_delta` fields may be positive, negative, or zero — never forced positive (spec SC-002).

## ResolutionDetermination

| Field | Type | Notes |
|---|---|---|
| `revalidation_id` | string | |
| `outcome` | enum | `resolved`, `reopened` |
| `criteria_evaluated` | object | `{no_critical_gx: bool, anomaly_in_normal_band: bool, risk_below_threshold: bool, no_outstanding_manual_actions: bool}` |
| `blocked_by_manual_actions` | boolean | True if `resolved` was withheld solely due to outstanding `ManualActionRequired` records (spec FR-007, SC-003) |

**Validation rules**: `outcome = "resolved"` only if every field in `criteria_evaluated` is `true` (spec FR-007, SC-003).

## Relationships

`RevalidationRun` is 1:1 with a `BeforeAfterComparison` and a `ResolutionDetermination`, and many-to-one with a specific `RemediationRun` (an incident may be revalidated multiple times, each a distinct `RevalidationRun`, spec FR-011/SC-005). `ResolutionDetermination.outcome` drives the incident's status transition via Phase 12's extended state machine.
