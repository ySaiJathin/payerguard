# API Contracts: Revalidation

New `revalidation` module router.

## `POST /revalidation/{incident_id}/run`

Recomputes Quality/Anomaly/Risk/Severity/Business Impact/Priority for the incident's remediated claims, produces the before/after comparison, and determines Resolved/Reopened.

**Response `200 OK`**:
```json
{
  "revalidation_run": "...RevalidationRun",
  "comparison": "...BeforeAfterComparison",
  "resolution": "...ResolutionDetermination",
  "incident_status": "resolved"
}
```

**Response `409 Conflict`**: the incident's most recent `RemediationRun` is incomplete/pending (spec FR-009, SC-006).

## `GET /revalidation/{incident_id}`

Returns full revalidation history for the incident.

**Response `200 OK`**: `RevalidationRun[]` (each with its `BeforeAfterComparison` and `ResolutionDetermination`).

## Notes

- This endpoint updates the incident's status via Phase 12's `hitl` state machine (transition action `system: revalidation_result`) — it does not bypass that state machine.
