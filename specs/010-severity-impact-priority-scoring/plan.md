# Implementation Plan: Severity, Business Impact, and Priority Scoring

**Branch**: `010-severity-impact-priority-scoring` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-severity-impact-priority-scoring/spec.md`

## Summary

Build the `risk.scoring` sub-module (the fifth piece of Section 3's `risk` module boundary): Severity (three-component formula reading Phase 3/7/8 outputs), Business Impact (measurable-only, with explicit `unavailable` component marking), and Final Incident Priority (combining Severity, Phase 9's Risk Score, Business Impact, and Affected Claims Score) — all as reusable, idempotent scoring functions Phase 12 (incident creation) and Phase 14 (revalidation) both call.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: pandas, numpy (pure computation, no ML training here); reads Phase 3's quality results, Phase 4's baseline, Phase 7's calibrated anomaly scores, Phase 8's `affected_claim_pct`, Phase 9's production risk model score

**Storage**: No new persistent store required beyond returning `SeverityResult`/`BusinessImpactResult`/`PriorityResult` for the caller (Phase 12) to persist alongside its `Incident` record — this feature is a computation library, not itself a data-owning module

**Testing**: pytest — a formula-reproducibility test for Severity and Priority (SC-001, SC-003); an "unavailable ≠ 0" test for Business Impact (SC-002); a missing-Risk-input failure test (SC-004); a reusability test simulating a Phase-14-style before/after call (SC-005)

**Target Platform**: Same as prior phases

**Project Type**: Backend module — `backend/app/risk/scoring/` sub-package, completing Section 3's `risk (logistic, random_forest, xgboost, benchmark, scoring)` module

**Performance Goals**: Pure arithmetic over already-computed inputs — sub-second per incident

**Constraints**: Business Impact must structurally distinguish "unavailable" from "0" (FR-006); weight configs validated (FR-010); no fabricated Risk default (FR-009)

**Scale/Scope**: Per-incident/per-window scoring; called on-demand by Phase 12 (creation) and Phase 14 (revalidation), not a standalone batch job

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — consumes Phase 7/9's already-selected production models, doesn't select anything itself | PASS |
| II. No Fabricated Values | Applies with particular force — FR-006/FR-009/FR-012, the "unavailable, not zero" distinction is a direct anti-fabrication mechanism | PASS |
| III. Deterministic-First, ML-Second | Applies — this is deterministic arithmetic combining already-validated (Phase 3) and already-benchmarked (Phase 7/9) signals | PASS |
| IV. Human-in-the-Loop | Not applicable directly — but Priority is what the human reviewer sees first in Phase 12, making correctness here high-stakes | PASS |
| V. Constrained, Auditable Remediation | Related — FR-011's reusability requirement is what makes Phase 14's before/after comparison possible | PASS |
| VI. Modular Backend, No Monolith | Applies — `scoring` sub-package completes the `risk` module alongside `dataset` (Phase 8) and `benchmark` (Phase 9) | PASS |
| VII. Temporal Integrity | Not directly applicable — no train/val/test split involved in pure scoring arithmetic | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/010-severity-impact-priority-scoring/
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
│   └── risk/
│       └── scoring/
│           ├── __init__.py
│           ├── severity.py          # FR-001-FR-004
│           ├── business_impact.py   # FR-005, FR-006
│           ├── priority.py          # FR-007, FR-008, FR-010
│           ├── schemas.py           # SeverityResult, BusinessImpactResult, PriorityResult
│           └── weight_config.py     # validated, configurable weight sets
└── tests/
    └── risk/
        └── scoring/
            ├── test_severity_formula.py
            ├── test_business_impact_unavailable.py
            ├── test_priority_formula.py
            ├── test_missing_risk_input.py
            └── test_reusability_post_remediation.py
```

**Structure Decision**: `scoring` sub-package inside the `risk` module — a pure computation library with no router of its own for this MVP pass (Phase 12 calls it directly as an internal service function); a thin `POST /risk/score` convenience endpoint is included in the contract for manual/testing invocation.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
