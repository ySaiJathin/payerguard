# Phase 1 Data Model: Incident Management & Human-in-the-Loop

## Incident

| Field | Type | Notes |
|---|---|---|
| `incident_id` | string | |
| `window_id` | string | References Phase 4/5's window |
| `quality_score` / `anomaly_score` / `risk_score` | float | From Phase 3/7/9 |
| `severity_result` / `business_impact_result` / `priority_result` | object | From Phase 10 |
| `status` | enum | `pending_investigation`, `ready_for_review`, `accepted`, `rejected`, `resolved` (reserved, Phase 14), `reopened` (reserved, Phase 14) |
| `current_investigation_id` | string \| null | Latest `LLMInvestigation` (Phase 11) |
| `created_at` / `updated_at` | timestamp | |

**Validation rules**: `status` only ever changes via a validated transition in `state_machine.py` (spec FR-007). No field is fabricated — `severity_result`/`business_impact_result`/`priority_result` are exactly Phase 10's output (spec FR-010, SC-001).

## IncidentStatusTransition

| Field | Type | Notes |
|---|---|---|
| `transition_id` | string | |
| `incident_id` | string | |
| `from_status` / `to_status` | enum | Must be a valid pair per the transition table |
| `action` | enum | `accept`, `reject`, `recalculate`, `system` (for pipeline-driven transitions like Phase 14) |
| `reviewer_id` | string \| null | Present for human-driven actions |
| `occurred_at` | timestamp | |

## HumanFeedback

| Field | Type | Notes |
|---|---|---|
| `feedback_id` | string | |
| `incident_id` | string | |
| `investigation_id` | string | The specific `LLMInvestigation` being rejected |
| `reason_category` | enum | e.g., `incorrect_root_cause`, `insufficient_evidence_disagreement`, `false_positive`, `other` |
| `feedback_text` | string | Non-empty (spec FR-003) |
| `reviewer_id` | string | |
| `submitted_at` | timestamp | |

**Validation rules**: Every `reject` `IncidentStatusTransition` has exactly one corresponding `HumanFeedback` record with matching `incident_id`/`investigation_id` (spec FR-003, FR-004, SC-002). Records are immutable and cumulative across recalculation cycles (spec SC-004).

## Relationships

`Incident` has many `IncidentStatusTransition` (full history) and many `HumanFeedback` (one per reject cycle). `Incident.current_investigation_id` always points to the most recent `LLMInvestigation` (Phase 11), while all prior investigations remain queryable via Phase 11's own `GET /llm/investigations/{incident_id}`.
