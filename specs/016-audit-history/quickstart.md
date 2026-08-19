# Quickstart: Audit & History

## Query a claim/incident's history

```bash
curl "http://localhost:8000/history/incident/<incident_id>"
curl "http://localhost:8000/history/claim/<claim_id>"
```

**Expected outcome**: `200 OK`, `found: true`, `entries` in chronological order covering every stage the entity actually passed through (spec SC-001).

Filtering and pagination (spec FR-007):

```bash
curl "http://localhost:8000/history/incident/<incident_id>?stage=remediation"
curl "http://localhost:8000/history/incident/<incident_id>?page=2&page_size=10"
curl "http://localhost:8000/history/incident/<incident_id>?start_date=2026-08-01T00:00:00Z"
```

## Verify provenance (no duplicated facts)

```bash
pytest backend/tests/audit/test_provenance.py -v
```

Resolves every entry's `source_record_id` against its owning module's own store (SQL table, or Phase 11's file-based investigation log), and asserts the `audit_logs` table has no column capable of holding a copy of upstream content (spec SC-002).

## Verify baseline parity

```bash
diff <(curl -s http://localhost:8000/audit/baseline) <(curl -s http://localhost:8000/baseline)
```

Or run `backend/tests/audit/test_baseline_parity.py`, which asserts both endpoints return identical JSON, that a specific historical snapshot is retrievable by `snapshot_id`, and that the pass-through never serves a stale cached copy (spec SC-003).

**Note the path**: the audit copy is `/audit/baseline`, not `/baseline`. Phase 4's `baseline` router already owns `/baseline`, and registering a duplicate would make the served handler depend on router include order. See [contracts/api.md](./contracts/api.md) for the full rationale.

## Verify deterministic ordering under near-simultaneous events

```bash
pytest backend/tests/audit/test_deterministic_ordering.py -v
```

Appends entries sharing an identical timestamp, then queries twice and asserts identical ordering both times — plus that bulk appends assign contiguous, non-reused sequence numbers (spec SC-004).

## Verify "no history found" is distinguishable

```bash
curl "http://localhost:8000/history/claim/does-not-exist"
```

**Expected outcome**: `200 OK` with `found: false` (spec SC-006). Note this is deliberately **not** a `404` — see contracts/api.md.

A page past the end of a *real* history, by contrast, returns `found: true` with empty `entries`. Distinguishing those two is the whole point of the flag.

## Verify registry completeness enforcement

```bash
pytest backend/tests/audit/test_registry_completeness.py -v
```

Drives every expected module's real write path and asserts each registered an audit source; then injects a mock pipeline-stage module with no audit source and asserts the check reports it unregistered — proving the guarantee is enforced rather than vacuous (spec SC-005).

Two registry decisions are asserted directly by that file:

- **`ingestion` is absent** from `EXPECTED_AUDITED_MODULES`. The continuous-ingestion phase was removed 2026-08-18 and `backend/app/ingestion/` has no write path to instrument, so keeping it would mean a permanently failing check.
- **`data_engineering` is present**, though research.md's list omitted it — FR-001 and User Story 1's first acceptance scenario both require Phase 2 cleaning corrections in a claim's trail.

Full endpoint contracts: [contracts/api.md](./contracts/api.md). Entity definitions: [data-model.md](./data-model.md).

---

This closes out the Phase 1-16 MVP build order (Phases 17-21 remain explicitly deferred per MVP_CONTEXT.md Section 5).
