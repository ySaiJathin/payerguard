# API Contracts: Incident Management & Human-in-the-Loop

## `incidents` module

### `POST /incidents`
Creates an incident from a window's Phase 10 scores (triggers Phase 11 investigation as part of creation). **Response `201 Created`**: `Incident`.

### `GET /incidents`
Lists incidents. **Query params**: `status`, `min_priority` — optional. **Response `200 OK`**: `Incident[]`.

### `GET /incidents/{incident_id}`
**Response `200 OK`**: `Incident`. **Response `404 Not Found`**.

### `PATCH /incidents/{incident_id}`
Updates non-status fields only (status changes go through `hitl` endpoints, never this one) — spec FR-001.

## `hitl` module

### `POST /hitl/{incident_id}/accept`
**Request body**: `{ "reviewer_id": "reviewer-1" }`
**Response `200 OK`**: updated `Incident` (status → `accepted`).
**Response `409 Conflict`**: invalid transition (e.g., already accepted) — spec FR-007, SC-006.

### `POST /hitl/{incident_id}/reject`
**Request body**: `{ "reviewer_id": "reviewer-1", "reason_category": "incorrect_root_cause", "feedback_text": "..." }`
**Response `200 OK`**: updated `Incident` (status → `rejected`), `HumanFeedback` created.
**Response `422 Unprocessable Entity`**: missing `feedback_text` — spec FR-003, SC-002.
**Response `409 Conflict`**: invalid transition.

### `POST /hitl/{incident_id}/recalculate`
**Response `200 OK`**:
```json
{ "incident": "...Incident", "new_investigation": "...LLMInvestigation", "evidence_changed": false }
```
**Response `409 Conflict`**: incident not in `rejected` status.

### `GET /hitl/{incident_id}/feedback`
Returns full `HumanFeedback[]` history for the incident. **Response `200 OK`**: `HumanFeedback[]`.

## Notes

- Only `hitl` endpoints can change `Incident.status` — `incidents` module's own `PATCH` is structurally prevented from touching the `status` field, keeping the state machine the single source of truth for transitions.
