# Implementation Plan: Incident Management & Human-in-the-Loop

**Branch**: `012-incident-management-hitl` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-incident-management-hitl/spec.md`

## Summary

Build the `incidents` and `hitl` modules: `Incident` CRUD backed by Phase 10 scores and Phase 11 investigations, an explicit accept/reject state machine, mandatory feedback capture on reject, and a recalculation action that re-invokes Phase 11 (and relevant upstream scoring) without discarding history — with a structural guarantee that feedback never triggers automatic retraining.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI (per MVP_CONTEXT.md Section 3's implied backend stack), SQLAlchemy/pydantic for the `incidents`/`human_feedback` tables; calls Phase 10's scoring functions and Phase 11's `POST /llm/investigate`

**Storage**: `incidents` and `human_feedback` tables (MVP_CONTEXT.md Section 3 core tables) — this feature is the natural point where the pipeline moves from file-based artifacts to genuine relational persistence, since incidents have a real lifecycle (multiple state transitions over time) that a flat file poorly represents

**Testing**: pytest — a full state-machine test covering every valid/invalid transition (SC-003, SC-006); a reject-without-feedback rejection test (SC-002); a recalculation-preserves-history test (SC-004); a retraining-isolation test (SC-005)

**Target Platform**: Same as prior phases

**Project Type**: Backend modules — new `backend/app/incidents/` and `backend/app/hitl/` modules (Section 3 lists them as distinct module boundaries: `incidents` and `hitl (accept/reject)`)

**Performance Goals**: No phase-specific numeric target; CRUD/state-transition operations are simple DB operations, sub-second

**Constraints**: Reject always requires feedback (FR-003); invalid transitions always rejected explicitly (FR-007); zero automatic retraining trigger (FR-006, SC-005)

**Scale/Scope**: Incident volume scales with Phase 10's Priority-flagged findings — modest at current data scale (tens of windows), designed to remain correct as Phase 15 adds more historical batches

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable | PASS |
| II. No Fabricated Values | Applies — FR-010, incidents carry only real Phase 10/11 outputs | PASS |
| III. Deterministic-First, ML-Second | Not directly applicable — this is orchestration/state-management, not a scoring layer itself | PASS |
| IV. Human-in-the-Loop | This feature **is** the direct implementation of Principle IV in full: explicit accept before remediation, mandatory feedback on reject, recalculation not silent-drop | PASS |
| V. Constrained, Auditable Remediation | Sets up the gate Phase 13 checks (accepted status) but performs no remediation itself | PASS |
| VI. Modular Backend, No Monolith | Applies — two distinct modules (`incidents`, `hitl`) matching Section 3's naming exactly | PASS |
| VII. Temporal Integrity | Not directly applicable | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/012-incident-management-hitl/
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
│   ├── incidents/
│   │   ├── __init__.py
│   │   ├── models.py           # Incident SQLAlchemy model
│   │   ├── schemas.py          # pydantic schemas
│   │   ├── service.py          # create/read/list/update (FR-001)
│   │   └── router.py           # POST/GET/PATCH /incidents
│   └── hitl/
│       ├── __init__.py
│       ├── state_machine.py    # valid transition rules (FR-007, FR-008)
│       ├── accept_service.py   # FR-002
│       ├── reject_service.py   # FR-003, FR-004
│       ├── recalculation_service.py  # FR-005 — calls Phase 11
│       ├── models.py           # HumanFeedback, IncidentStatusTransition
│       └── router.py           # POST /hitl/{incident_id}/accept, /reject, /recalculate
└── tests/
    ├── incidents/
    │   └── test_incident_crud.py
    └── hitl/
        ├── test_state_machine.py         # SC-003, SC-006
        ├── test_reject_requires_feedback.py  # SC-002
        ├── test_recalculation_history.py     # SC-004
        └── test_no_auto_retrain.py            # SC-005
```

**Structure Decision**: Two separate modules (`incidents` owns the record; `hitl` owns the accept/reject/recalculate workflow acting on it) — matches Section 3's explicit module list rather than merging them into one.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
