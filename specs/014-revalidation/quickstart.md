# Quickstart: Revalidation

## Prerequisites

- A completed `RemediationRun` (Phase 13) for an accepted incident.

## Run revalidation

```bash
curl -X POST http://localhost:8000/revalidation/<incident_id>/run
```

**Expected outcome**: `200 OK` with `revalidation_run`, `comparison`, `resolution`, and `incident_status` (`resolved` or `reopened`).

## Verify genuine recomputation

Run `backend/tests/revalidation/test_genuine_recomputation.py` — asserts Phase 3/7/9's functions were actually called (via mock/spy) rather than a cached value being reused (spec SC-001).

## Verify honest, possibly-unfavorable deltas

Run `backend/tests/revalidation/test_unfavorable_delta.py` against a fixture where remediation didn't actually help — asserts `risk_delta`/`anomaly_delta` can be positive (worse) and `incident_status` is `reopened` (spec SC-002).

## Verify Resolved is blocked by outstanding manual actions

Run `backend/tests/revalidation/test_resolved_blocked_by_manual_action.py` — a fixture with a `ManualActionRequired` record still outstanding; asserts `resolution.outcome != "resolved"` even if quality/anomaly/risk all clear (spec SC-003).

## Verify refusal on incomplete remediation

```bash
curl -X POST http://localhost:8000/revalidation/<incident_with_pending_remediation>/run
```

**Expected outcome**: `409 Conflict` (spec SC-006).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).
