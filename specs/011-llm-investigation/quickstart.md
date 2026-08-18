# Quickstart: LLM Investigation (Mistral)

## Prerequisites

- `MISTRAL_API_KEY` set in `.env` (never committed).
- A structured incident available (real, from Phase 10, or a fixture for isolated testing before Phase 12 ships).

## Run an investigation

```bash
curl -X POST http://localhost:8000/llm/investigate -d '{"incident_id": "incident-123"}'
```

**Expected outcome**: `200 OK` with all six sections populated (spec SC-001).

## Verify insufficient-evidence handling

Run `backend/tests/llm/test_insufficient_evidence.py` against a fixture incident with deliberately sparse evidence (e.g., a single WARNING check, low anomaly score, no strong deviation) — asserts `insufficient_evidence: true` and the literal phrase appears (spec SC-002).

## Verify the write-access boundary

Run `backend/tests/llm/test_write_access_boundary.py` — a static import-graph check confirming `investigation_service.py` has no dependency path to any write-capable `claims`/`remediation` function (spec SC-003).

## Verify API-failure handling

Run `backend/tests/llm/test_api_failure_handling.py` with a mocked Mistral client raising a timeout — asserts an `InvestigationFailure` record is created, not a fabricated `LLMInvestigation` (spec SC-004).

## Verify re-investigation history

```bash
curl -X POST http://localhost:8000/llm/investigate -d '{"incident_id": "incident-123"}'
curl -X POST http://localhost:8000/llm/investigate -d '{"incident_id": "incident-123"}'
curl http://localhost:8000/llm/investigations/incident-123 | jq '.investigations | length'
```

**Expected outcome**: `2` — both preserved (spec SC-005).

## Verify no secret leakage

Run `backend/tests/llm/test_no_secret_leakage.py` — scans source/log output for the literal `MISTRAL_API_KEY` value (spec SC-006).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
