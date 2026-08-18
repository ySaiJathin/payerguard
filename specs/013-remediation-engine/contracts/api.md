# API Contracts: Remediation Engine

New `remediation` module router.

## `POST /remediation/{incident_id}/run`

Executes remediation for an accepted incident.

**Response `200 OK`**: `RemediationRun`.

**Response `409 Conflict`**: incident status is not `accepted` (spec FR-002, SC-002).

## `GET /remediation/{incident_id}`

Returns the most recent `RemediationRun` for an incident (including all prior runs' history if remediation was re-triggered).

**Response `200 OK`**: `RemediationRun[]`.

**Response `404 Not Found`**: remediation never run for this incident.

## Notes

- `POST /remediation/{incident_id}/run` is safe to call repeatedly (idempotent, spec FR-008) — re-running after a partial failure resumes rather than restarts or duplicates actions.
- No endpoint in this module accepts a caller-specified remediation action — every action taken is derived solely from the incident's affected claims matched against the versioned rule tables (spec FR-005).
