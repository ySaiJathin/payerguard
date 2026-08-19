# Quickstart: Audit & History

## Query a claim/incident's history

```bash
curl "http://localhost:8000/history/incident/<incident_id>"
```

**Expected outcome**: `200 OK`, `found: true`, `entries` in chronological order covering every stage the incident actually passed through (spec SC-001).

## Verify provenance (no duplicated facts)

Run `backend/tests/audit/test_provenance.py` — for each `AuditTrailEntry`, resolves `source_record_id` against `source_module`'s own table and confirms it exists and matches (spec SC-002).

## Verify baseline parity

```bash
diff <(curl -s http://localhost:8000/history/../baseline) <(curl -s http://localhost:8000/../baseline)
```

Or more directly, run `backend/tests/audit/test_baseline_parity.py`, which calls both `GET /baseline` (audit module) and `GET /baseline` (Phase 4's `baseline` module) and asserts byte-identical responses (spec SC-003).

## Verify deterministic ordering under near-simultaneous events

Run `backend/tests/audit/test_deterministic_ordering.py` — a fixture that appends two entries within the same millisecond, then queries history twice and asserts identical ordering both times (spec SC-004).

## Verify "no history found" is distinguishable

```bash
curl "http://localhost:8000/history/claim/does-not-exist"
```

**Expected outcome**: `found: false` (spec SC-006).

## Verify registry completeness enforcement

Run `backend/tests/audit/test_registry_completeness.py` — registers a mock new pipeline-stage module without wiring `audit.append_entry`, and asserts the completeness check fails (spec SC-005).

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).

---

This closes out the Phase 1-16 MVP build order (Phases 17-21 remain explicitly deferred per MVP_CONTEXT.md Section 5).
