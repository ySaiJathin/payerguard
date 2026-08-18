# Phase 0 Research: Audit & History

## Decision: Each owning module appends a lightweight `AuditTrailEntry` reference at write time; `audit` module never scrapes/re-derives history after the fact

**Decision**: Phase 2-15's own write operations (e.g., `QualityIssueRecord` creation, `IncidentStatusTransition` creation) each make one additional, simple call — `audit.append_entry(entity_type, entity_id, pipeline_stage, source_module, source_record_id)` — at the moment they persist their own record; the `audit` module's `audit_logs` table is built up incrementally this way, not reconstructed retroactively by querying every other module's tables on each history request.

**Rationale**: FR-001/SC-002 require entries to reference real upstream records without duplicating facts, and FR-004 requires stable deterministic ordering — an append-at-write-time model naturally gives a correct, real-time sequence number, whereas reconstructing history after the fact from N different tables' timestamps would be slower per-query and more fragile in the face of clock-skew/near-simultaneous events (the exact problem FR-004's Edge Case calls out).

**Alternatives considered**: A pure aggregation query across all owning tables at `/history` request time, no incremental log table (rejected — every history query would need to join across ~10 tables and reconstruct ordering from potentially-imprecise per-table timestamps; the append-at-write-time model does this ordering work once, at write time, when it's guaranteed sequential).

## Decision: `append_entry` is a tiny, dependency-light shared utility each module calls — not a circular dependency

**Decision**: `audit.append_entry` lives in a minimal, low-level shared utility module with zero dependencies on any other pipeline-stage module (it only needs a DB connection and the four/five plain fields), so every other module (Phase 2 through 15) can safely import and call it without creating an import cycle back into their own domain logic.

**Rationale**: Since `audit` is the last module built (Phase 17) but needs to be called from every earlier module's write paths, avoiding a circular/heavy dependency is essential — a minimal utility function with no domain knowledge of any other module keeps this tractable and matches how a logging/telemetry utility is typically structured in a modular codebase.

**Alternatives considered**: `audit` module polling/subscribing to database change events (e.g., triggers or CDC) to build its log without requiring other modules to call it explicitly (rejected as unnecessary infrastructure complexity for the MVP — an explicit, tiny function call at each write site is simpler, more visible in code review, and sufficient at this project's scale).

## Decision: `GET /baseline` is a direct pass-through to Phase 4's `baseline` module's own service function

**Decision**: `baseline_passthrough.py` calls Phase 4's `snapshot_service.get_current_snapshot()` (or `get_snapshot(snapshot_id)`) directly and returns its result unchanged — `audit`'s `/baseline` endpoint exists purely to give this a documented, expected location per MVP_CONTEXT.md Phase 17's naming, without introducing a second baseline computation or cache.

**Rationale**: Spec FR-003/SC-003 explicitly require parity with Phase 4's own `GET /baseline` and forbid a second independently-computed baseline — a direct pass-through is the only implementation that structurally guarantees this (there's no code path where the two could diverge, since they're the same function call).

**Alternatives considered**: A cached/denormalized copy of the baseline stored in the `audit` module for faster reads (rejected — introduces exactly the staleness/divergence risk FR-003 warns against, for no clear benefit at this project's current data scale).

## Decision: Registry completeness enforced via an explicit `EXPECTED_AUDITED_MODULES` list checked against `registry.py`'s registered entries

**Decision**: `registry.py` defines `EXPECTED_AUDITED_MODULES = ["quality", "anomaly", "risk", "risk.scoring", "llm", "incidents", "hitl", "remediation", "revalidation", "ingestion"]` (the decision-producing modules per spec Assumptions, excluding pure computation modules like `data_engineering`/`features`), and each module's own test suite (or a single central test) asserts it has called `audit.append_entry` at least once for its primary decision-producing operation; `test_registry_completeness.py` fails if any `EXPECTED_AUDITED_MODULES` entry has zero registered audit sources.

**Rationale**: FR-008/SC-005 require the completeness guarantee be enforced by a failing test, not just documented intent — an explicit expected-list checked against actual registrations is straightforward to implement and directly satisfies "fails explicitly if a module... has no registered audit source."

**Alternatives considered**: Runtime enforcement (e.g., raising an exception if a module's write path completes without calling `append_entry`) — considered as a stronger guarantee, but harder to implement generically without instrumenting every module's write path with a decorator/hook; the test-based registry check is simpler and sufficient for the MVP while still being a real, executable, CI-visible guarantee rather than just a code comment.
