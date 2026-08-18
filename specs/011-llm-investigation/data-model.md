# Phase 1 Data Model: LLM Investigation (Mistral)

## StructuredIncidentPayload

| Field | Type | Notes |
|---|---|---|
| `incident_context` | object | window/incident identifiers, date range |
| `quality_evidence` | object | Relevant Phase 3 `ExpectationCheckResult` entries (failing/warning checks) |
| `anomaly_evidence` | object | Phase 7 anomaly score/details for affected claims |
| `risk_evidence` | object | Phase 9 production model's score + top contributing features if available |
| `severity_business_impact` | object | Phase 10's `SeverityResult`/`BusinessImpactResult`, `unavailable` components represented as such, never coerced to a number |
| `affected_claims_sample` | array | A representative sample of affected claim identifiers/amounts (not necessarily all, for prompt size) |

**Validation rules**: Every `unavailable` Business Impact component is represented to the LLM as explicitly unavailable (e.g., `"member_harm_impact": "unavailable - not measurable from this dataset"`), never omitted or shown as `0` (spec FR-001, Edge Cases).

## LLMInvestigation

| Field | Type | Notes |
|---|---|---|
| `investigation_id` | string | |
| `incident_id` | string | |
| `evidence_snapshot_id` | string | Reference/hash of the `StructuredIncidentPayload` used |
| `summary` | string | Non-empty |
| `likely_root_cause` | string | Either a substantive finding or the explicit insufficiency statement |
| `insufficient_evidence` | boolean | Derived by `response_parser.py` (research.md) |
| `evidence` | string | |
| `business_impact_narrative` | string | |
| `recommended_fix` | string | |
| `prevention_recommendation` | string | |
| `model_version` | string | Mistral model identifier used |
| `generated_at` | timestamp | |

**Validation rules**: All six narrative fields are non-empty for a successful record (spec SC-001). Multiple `LLMInvestigation` records may share an `incident_id` (re-investigation history) — each is immutable once created (spec FR-006, SC-005).

## InvestigationFailure

| Field | Type | Notes |
|---|---|---|
| `failure_id` | string | |
| `incident_id` | string | |
| `failure_type` | enum | `api_error`, `timeout`, `malformed_response` |
| `error_detail` | string | |
| `occurred_at` | timestamp | |

**Validation rules**: Created instead of (never alongside) a successful `LLMInvestigation` for the same attempt (spec FR-004, FR-007, SC-004).

## Relationships

Each investigation attempt produces exactly one of `LLMInvestigation` or `InvestigationFailure`, both linked to `incident_id`. An incident may have many `LLMInvestigation`/`InvestigationFailure` records over its lifecycle (re-investigation on reject, per Phase 12) — all preserved, none overwritten.
