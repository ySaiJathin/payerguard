# Phase 1 Data Model: Audit & History

## AuditTrailEntry

| Field | Type | Notes |
|---|---|---|
| `entry_id` | string | |
| `entity_type` | enum | `claim`, `incident`, `batch` |
| `entity_id` | string | |
| `pipeline_stage` | enum | `cleaning`, `quality`, `anomaly`, `risk`, `severity_scoring`, `llm_investigation`, `incident_status`, `human_feedback`, `remediation`, `revalidation`, `ingestion` |
| `source_module` | string | e.g., `"quality"`, `"hitl"` |
| `source_record_id` | string | The owning module's own record id — never a copy of its content (spec FR-001, SC-002) |
| `baseline_snapshot_id_used` | string \| null | Set when this stage depended on a baseline comparison (spec FR-005) |
| `sequence_number` | integer | Monotonic, assigned at append time (spec FR-004) |
| `occurred_at` | timestamp | |

**Validation rules**: `sequence_number` is strictly increasing and never reused, guaranteeing deterministic ordering even for same-millisecond events (spec SC-004). `source_record_id` is always resolvable back to a real record in `source_module`'s own table (spec SC-002).

## AuditSourceRegistryEntry

| Field | Type | Notes |
|---|---|---|
| `module_name` | string | Matches `EXPECTED_AUDITED_MODULES` (research.md) |
| `record_types_contributed` | string[] | e.g., `["ExpectationCheckResult"]` for `quality` |
| `registered` | boolean | Set true once at least one real `AuditTrailEntry` from this module is observed |

**Validation rules**: Every `EXPECTED_AUDITED_MODULES` entry has `registered = true` before this feature is considered complete (spec FR-008, SC-005).

## HistoryQueryResult

| Field | Type | Notes |
|---|---|---|
| `entity_type` / `entity_id` | string | The query target |
| `entries` | AuditTrailEntry[] | Ordered by `sequence_number` |
| `page` / `page_size` / `total_count` | integer | Pagination metadata (spec FR-007) |
| `found` | boolean | `false` triggers the distinguishable "no history found" response (spec FR-006, SC-006) |

## Relationships

`AuditTrailEntry` records reference (never copy) records owned by every other module named in `AuditSourceRegistryEntry`. `HistoryQueryResult` is the response shape for `GET /history`, filtering/paginating over the full `AuditTrailEntry` set for a given `entity_id`.
