# Implementation Plan: Remediation Engine

**Branch**: `013-remediation-engine` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-remediation-engine/spec.md`

## Summary

Build the `remediation` module: three deterministic handlers (duplicate flagging, approved imputation, approved status mapping) driven by versioned configuration tables, gated strictly on Phase 12's "accepted" incident status and scoped to an incident's documented affected claims, with unhandled conditions explicitly marked "Manual Action Required" and zero LLM involvement at execution time.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: pandas/SQLAlchemy (claim record updates), pydantic (rule-table schemas); reads Phase 12's `Incident` (status, affected claims) and writes to the `remediations` table (MVP_CONTEXT.md Section 3)

**Storage**: `remediations` table for `RemediationAction`/`ManualActionRequired` records; rule tables (`duplicate_flagging_rules.yaml`/`imputation_rules.yaml`/`status_mapping_rules.yaml`) as versioned config files under `backend/app/remediation/config/`

**Testing**: pytest — full idempotency test (SC-005); precondition-invalidation test (SC-006); accepted-status-gate test (SC-002); LLM-dependency-absence static test (SC-004)

**Target Platform**: Same as prior phases

**Project Type**: Backend module — new `backend/app/remediation/` module with `duplicate/missing/invalid_status/manual` handler sub-files (MVP_CONTEXT.md Section 3's `remediation (duplicate/missing/invalid-status/manual handlers)` boundary)

**Performance Goals**: No phase-specific numeric target; remediation acts on a small, bounded set of affected claims per incident — sub-second per run

**Constraints**: Zero LLM call at execution time (FR-005, SC-004); strict accepted-only gate (FR-002, SC-002); idempotent (FR-008, SC-005)

**Scale/Scope**: Bounded to one incident's affected claims per run; three fixed handler types, no open-ended handler registration in this MVP

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — deterministic handlers, no model selection | PASS |
| II. No Fabricated Values | Applies — imputed/mapped values come only from pre-approved, documented rule tables, never invented ad hoc | PASS |
| III. Deterministic-First, ML-Second | Applies — this entire feature is deterministic by design, with zero ML/LLM involvement at execution (FR-005) | PASS |
| IV. Human-in-the-Loop | Applies directly — FR-002 enforces "no remediation without explicit accept" | PASS |
| V. Constrained, Auditable Remediation | This feature **is** the direct implementation of Principle V in full | PASS |
| VI. Modular Backend, No Monolith | Applies — new `remediation` module matching Section 3's sub-file naming | PASS |
| VII. Temporal Integrity | Not directly applicable | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/013-remediation-engine/
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
│   └── remediation/
│       ├── __init__.py
│       ├── config/
│       │   ├── duplicate_flagging_rules.yaml
│       │   ├── imputation_rules.yaml
│       │   └── status_mapping_rules.yaml
│       ├── duplicate_handler.py      # FR-001, FR-006
│       ├── imputation_handler.py     # FR-001, FR-006
│       ├── status_mapping_handler.py # FR-001, FR-006
│       ├── manual_handler.py         # FR-004 — ManualActionRequired
│       ├── precedence.py             # FR-007
│       ├── remediation_service.py    # FR-002, FR-003, FR-008, FR-009, FR-010 — orchestrator
│       ├── schemas.py                # RemediationRule, RemediationAction, ManualActionRequired, RemediationRun
│       └── router.py                 # POST /remediation/{incident_id}/run, GET /remediation/{incident_id}
└── tests/
    └── remediation/
        ├── test_accepted_gate.py         # SC-002
        ├── test_idempotency.py            # SC-005
        ├── test_precondition_revalidation.py  # SC-006
        ├── test_no_llm_dependency.py           # SC-004
        └── test_concurrent_claim_conflict.py    # FR-010
```

**Structure Decision**: New `remediation` module matching Section 3's `duplicate/missing/invalid-status/manual handlers` naming (mapped here to `duplicate_handler`/`imputation_handler`/`status_mapping_handler`/`manual_handler`).

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
