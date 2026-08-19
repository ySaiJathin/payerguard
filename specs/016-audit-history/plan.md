# Implementation Plan: Audit & History

**Branch**: `016-audit-history` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-audit-history/spec.md`

## Summary

Build the `audit` module: an audit-source registry and aggregation layer over every prior phase's own persisted records (Phase 2-14), a `GET /history` endpoint with pagination/filtering and stable deterministic ordering, a `GET /baseline` pass-through to Phase 4's baseline data, and a completeness check guaranteeing no future pipeline-stage module can silently skip audit registration. This closes out the 1-17 MVP build order.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: SQLAlchemy (read-only queries across `audit_logs` and the other modules' tables), pydantic; reads from every prior phase's persistence without introducing a new write path for their facts

**Storage**: `audit_logs` table (MVP_CONTEXT.md Section 3 core tables) — populated by an aggregation/indexing process (e.g., a lightweight event-append call each owning module already makes when it writes its own record) rather than this module writing other modules' facts on their behalf

**Testing**: pytest — a full-pipeline fixture test asserting every stage a claim/incident passed through appears (SC-001); a provenance test (SC-002); a `GET /baseline` parity test against Phase 4 (SC-003); a deterministic-ordering test with near-simultaneous events (SC-004); a registry-completeness test that fails on an unregistered new module (SC-005)

**Target Platform**: Same as prior phases

**Project Type**: Backend module — new `backend/app/audit/` module (MVP_CONTEXT.md Section 3's `audit` module boundary, the last one named)

**Performance Goals**: `GET /history` queries must remain responsive as history grows — pagination (FR-007) is the primary mechanism; no specific numeric target given current data scale

**Constraints**: No independently-duplicated facts (FR-001, SC-002); no external write path into the aggregated trail (FR-009); registry completeness enforced by a failing test, not just documentation (FR-008, SC-005)

**Scale/Scope**: Aggregates across all Phase 2-14 audit-relevant record types; grows as further batches are loaded over time (the continuous-ingestion phase was removed 2026-08-18)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable | PASS |
| II. No Fabricated Values | Applies — every `AuditTrailEntry` references a real, already-persisted upstream record (FR-001) | PASS |
| III. Deterministic-First, ML-Second | Applies — audit is itself a deterministic aggregation/indexing operation | PASS |
| IV. Human-in-the-Loop | Related — every human accept/reject/feedback event (Phase 12) is captured in the audit trail | PASS |
| V. Constrained, Auditable Remediation | This feature **is** the "every step... is written to the audit log" clause's direct implementation, completing the loop | PASS |
| VI. Modular Backend, No Monolith | Applies — new `audit` module that reads (never owns) other modules' data, respecting each module's ownership of its own facts | PASS |
| VII. Temporal Integrity | Applies — FR-004/FR-005's deterministic ordering and baseline-snapshot tracking preserve chronological accuracy in history | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/016-audit-history/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md   # /speckit.tasks — not created here
```

### Source Code (repository root)

```text
backend/
├── app/
│   └── audit/
│       ├── __init__.py
│       ├── registry.py             # FR-008 — AuditSourceRegistryEntry, completeness check
│       ├── aggregation_service.py  # FR-001, FR-004, FR-005 — builds AuditTrailEntry from source modules
│       ├── history_service.py      # FR-002, FR-006, FR-007
│       ├── baseline_passthrough.py # FR-003
│       ├── schemas.py              # AuditTrailEntry, HistoryQueryResult
│       └── router.py               # GET /history, GET /baseline
└── tests/
    └── audit/
        ├── test_full_pipeline_trail.py     # SC-001
        ├── test_provenance.py                # SC-002
        ├── test_baseline_parity.py            # SC-003
        ├── test_deterministic_ordering.py      # SC-004
        └── test_registry_completeness.py        # SC-005
```

**Structure Decision**: New `audit` module, the last named in Section 3's module list — a pure read/aggregation layer with `baseline_passthrough.py` explicitly delegating to Phase 4's existing endpoint rather than reimplementing baseline retrieval.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
