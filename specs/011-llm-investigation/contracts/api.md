# API Contracts: LLM Investigation (Mistral)

New `llm` module router.

## `POST /llm/investigate`

Builds the structured payload for a given incident and requests an investigation from Mistral.

**Request body**:
```json
{ "incident_id": "incident-123" }
```

**Response `200 OK`**: `LLMInvestigation`.

**Response `502 Bad Gateway`**: Mistral API failure — response body is `InvestigationFailure`.

**Response `422 Unprocessable Entity`**: Mistral responded but the response failed structural validation — response body is `InvestigationFailure` with `failure_type: "malformed_response"`.

**Response `404 Not Found`**: unknown `incident_id`.

## `GET /llm/investigations/{incident_id}`

Returns the full investigation history (all `LLMInvestigation` and `InvestigationFailure` records) for an incident, newest first.

**Response `200 OK`**:
```json
{ "investigations": ["...LLMInvestigation[]"], "failures": ["...InvestigationFailure[]"] }
```

## Notes

- No endpoint in this module accepts a request capable of mutating claim/incident state — `POST /llm/investigate` only ever creates a new `LLMInvestigation` or `InvestigationFailure` record (spec FR-009).
- `incident_id` in this contract assumes Phase 12's `Incident` entity exists; until Phase 12 ships, this endpoint can be exercised directly against a manually-constructed `StructuredIncidentPayload` for testing (see quickstart.md).
