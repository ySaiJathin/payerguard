# Implementation Plan: Revalidation

**Branch**: `014-revalidation` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-revalidation/spec.md`

## Summary

Build the `revalidation` module: re-invoke Phase 3 (quality), Phase 7 (anomaly), Phase 9 (risk), and Phase 10 (Severity/Business Impact/Priority) against a completed `RemediationRun`'s affected claims, produce an honest `BeforeAfterComparison`, and drive the incident to "Resolved" or "Reopened" via Phase 12's extended state machine — never assuming remediation succeeded.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Reuses Phase 3/7/9/10's existing service functions directly (no reimplementation); SQLAlchemy for `revalidation_results` persistence

**Storage**: `revalidation_results` table (MVP_CONTEXT.md Section 3 core tables)

**Testing**: pytest — a genuine-recomputation test (not-reused-values, SC-001); an unfavorable-delta fixture test (SC-002); a resolved-blocked-by-manual-action test (SC-003); an incomplete-remediation-refusal test (SC-006)

**Target Platform**: Same as prior phases

**Project Type**: Backend module — new `backend/app/revalidation/` module (MVP_CONTEXT.md Section 3's `revalidation` module boundary)

**Performance Goals**: No phase-specific numeric target; scoped to one incident's affected claims/window, expected sub-minute given Phase 3/7/9's own per-run budgets at this scale

**Constraints**: Genuine recomputation only (FR-001-FR-004, SC-001); Resolved blocked by outstanding manual actions (FR-007, SC-003); full history preserved (FR-011, SC-005)

**Scale/Scope**: One revalidation per completed remediation run, re-touching a small, bounded claim/window set

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Applies indirectly — FR-010 records which production model version was used, respecting that Phase 7/9's selections can change over time | PASS |
| II. No Fabricated Values | Applies with particular force — FR-012, genuine recomputation is the entire point, and honest (possibly unfavorable) deltas are required | PASS |
| III. Deterministic-First, ML-Second | Applies — Phase 3's deterministic re-check runs as part of this feature alongside the ML re-scores | PASS |
| IV. Human-in-the-Loop | Related — this feature completes the accept → remediate → revalidate loop constitution Principle V describes | PASS |
| V. Constrained, Auditable Remediation | This feature **is** the explicit "revalidation with before/after comparison" the constitution's Principle V mandates | PASS |
| VI. Modular Backend, No Monolith | Applies — new `revalidation` module, calling into (not duplicating) Phase 3/7/9/10's existing functions | PASS |
| VII. Temporal Integrity | Not directly applicable | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/014-revalidation/
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
│   └── revalidation/
│       ├── __init__.py
│       ├── recompute_service.py     # FR-001-FR-004 — calls Phase 3/7/9/10 directly
│       ├── comparison_service.py    # FR-005, FR-006
│       ├── resolution_criteria.py   # FR-007, FR-008 — documented thresholds
│       ├── schemas.py               # RevalidationRun, BeforeAfterComparison, ResolutionDetermination
│       └── router.py                # POST /revalidation/{incident_id}/run, GET /revalidation/{incident_id}
└── tests/
    └── revalidation/
        ├── test_genuine_recomputation.py    # SC-001
        ├── test_unfavorable_delta.py          # SC-002
        ├── test_resolved_blocked_by_manual_action.py  # SC-003
        └── test_incomplete_remediation_refused.py       # SC-006
```

**Structure Decision**: New `revalidation` module that calls Phase 3/7/9/10's service functions directly rather than duplicating their logic — the "reusable, idempotent functions" contract Phase 10 explicitly designed for (FR-011 there) is exercised here for real.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
