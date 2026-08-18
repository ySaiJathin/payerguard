# Quickstart: Incident Management & Human-in-the-Loop

## Create an incident

```bash
curl -X POST http://localhost:8000/incidents -d '{"window_id": "window-42"}'
```

**Expected outcome**: `201 Created`, `Incident` with real Phase 10 scores and a linked investigation (spec SC-001).

## Reject requires feedback

```bash
curl -X POST http://localhost:8000/hitl/<incident_id>/reject -d '{"reviewer_id": "r1"}'
```

**Expected outcome**: `422 Unprocessable Entity` — `feedback_text` missing (spec SC-002).

```bash
curl -X POST http://localhost:8000/hitl/<incident_id>/reject -d '{"reviewer_id": "r1", "reason_category": "false_positive", "feedback_text": "This window is a known holiday volume dip."}'
```

**Expected outcome**: `200 OK`, status → `rejected`, `HumanFeedback` persisted.

## Verify invalid transitions are rejected

```bash
curl -X POST http://localhost:8000/hitl/<incident_id>/accept -d '{"reviewer_id": "r1"}'
```

**Expected outcome**: `409 Conflict` — an already-rejected incident cannot be directly accepted without recalculation (spec SC-003, SC-006, run the full `test_state_machine.py` suite for complete coverage).

## Recalculate and re-review

```bash
curl -X POST http://localhost:8000/hitl/<incident_id>/recalculate
curl http://localhost:8000/hitl/<incident_id>/feedback | jq 'length'
```

**Expected outcome**: a new `LLMInvestigation` is produced, and the feedback history still shows the original reject's feedback (spec SC-004).

## Verify no auto-retraining

Run `backend/tests/hitl/test_no_auto_retrain.py` — a static import-graph check that `reject_service.py` has no dependency path to Phase 7/9's model-fitting functions (spec SC-005).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
