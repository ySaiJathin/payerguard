# Phase 1 Data Model: Testing Suite

## CoverageMapEntry

| Field | Type | Notes |
|---|---|---|
| `category` | enum | `Data`, `Anomaly`, `Risk`, `LLM`, `HITL`, `Ingestion` |
| `scenario` | string | The exact named scenario from MVP_CONTEXT.md Phase 16 |
| `status` | enum | `covered_by_prior_phase`, `new_test_added`, `limitation_documented` |
| `reference` | string | e.g., `"Phase 9 SC-001 (leakage isolation)"` or `"backend/tests/anomaly/test_model_stability.py"` |

**Validation rules**: Every scenario listed in MVP_CONTEXT.md Phase 16's description has exactly one `CoverageMapEntry` (spec FR-001, SC-001). `status: "limitation_documented"` always pairs with a non-empty explanation in `reference` (spec FR-008).

## IntegrationTestScenario

| Field | Type | Notes |
|---|---|---|
| `scenario_name` | string | e.g., `"accept_remediate_revalidate"`, `"large_file_ingestion"` |
| `modules_exercised` | string[] | Real module names touched (e.g., `["incidents", "hitl", "remediation", "revalidation"]`) — never mocked at the module boundary |
| `outcome` | enum | `pass`, `fail`, `limitation_documented` |
| `last_run_at` | timestamp | |

## Relationships

`CoverageMapEntry` records are the audit trail for FR-001; `IntegrationTestScenario` records are a subset of the `new_test_added` entries specifically covering HITL/Ingestion cross-module flows (FR-004, FR-005). No relationship to application data models — this feature is purely test-infrastructure.
