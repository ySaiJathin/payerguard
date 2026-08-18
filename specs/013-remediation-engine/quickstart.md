# Quickstart: Remediation Engine

## Prerequisites

- An incident in "accepted" status (Phase 12).

## Run remediation

```bash
curl -X POST http://localhost:8000/remediation/<incident_id>/run
```

**Expected outcome**: `200 OK` with a `RemediationRun` — every affected claim has an `action` or `manual_action_required` entry (spec SC-003).

## Verify the accepted-status gate

```bash
curl -X POST http://localhost:8000/remediation/<pending_incident_id>/run
```

**Expected outcome**: `409 Conflict` (spec SC-002).

## Verify idempotency

```bash
curl -X POST http://localhost:8000/remediation/<incident_id>/run
curl -X POST http://localhost:8000/remediation/<incident_id>/run
curl http://localhost:8000/remediation/<incident_id> | jq '.[-1].actions | length'
```

**Expected outcome**: the second run produces no duplicate `RemediationAction` records for already-completed claims (spec SC-005).

## Verify no LLM dependency

Run `backend/tests/remediation/test_no_llm_dependency.py` — a static import-graph check confirming `remediation_service.py` never imports Phase 11's `mistral_client.py` (spec SC-004).

## Verify precondition re-verification

Run `backend/tests/remediation/test_precondition_revalidation.py`, which selects a handler, invalidates its precondition in the fixture, then executes — expects a `ManualActionRequired` record with `reason_code: "precondition_invalidated"` (spec SC-006).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
