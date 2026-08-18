# Phase 1 Data Model: Remediation Engine

## RemediationRule

| Field | Type | Notes |
|---|---|---|
| `rule_id` | string | |
| `handler_type` | enum | `duplicate_flagging`, `approved_imputation`, `approved_status_mapping` |
| `precondition` | object | Handler-specific — e.g., for status mapping: `{column: "PTNT_DSCHRG_STUS_CD", from_value: "9", to_value: "1"}` |
| `precedence_rank` | integer | 1 = duplicate_flagging, 2 = status_mapping, 3 = imputation (research.md) |
| `rule_table_version` | string | Source YAML file's version field |

## RemediationAction

| Field | Type | Notes |
|---|---|---|
| `action_id` | string | |
| `incident_id` | string | |
| `claim_id` | string | |
| `rule_id` | string | References `RemediationRule` |
| `before_value` / `after_value` | string \| null | |
| `applied_at` | timestamp | |

**Validation rules**: Unique on `(incident_id, claim_id, rule_id)` — enforces idempotency (spec FR-008, SC-005).

## ManualActionRequired

| Field | Type | Notes |
|---|---|---|
| `record_id` | string | |
| `incident_id` | string | |
| `claim_id` | string | |
| `description` | string | Why no handler applied (unmatched condition, invalidated precondition, or concurrent-incident conflict) |
| `reason_code` | enum | `no_matching_rule`, `precondition_invalidated`, `concurrent_incident_conflict` |
| `flagged_at` | timestamp | |

## RemediationRun

| Field | Type | Notes |
|---|---|---|
| `run_id` | string | |
| `incident_id` | string | |
| `actions` | RemediationAction[] | |
| `manual_actions_required` | ManualActionRequired[] | |
| `started_at` / `completed_at` | timestamp | |

**Validation rules**: Every affected claim on the incident (per Phase 12's `Incident` affected-claims list) appears in exactly one of `actions` or `manual_actions_required` for a completed run (spec FR-009, SC-003).

## Relationships

`RemediationRun` aggregates the `RemediationAction`/`ManualActionRequired` records produced by one execution against one accepted `Incident`. Every `RemediationAction` references exactly one `RemediationRule`, which in turn belongs to exactly one of the three versioned rule tables.
