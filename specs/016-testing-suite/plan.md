# Implementation Plan: Testing Suite

**Branch**: `016-testing-suite` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-testing-suite/spec.md`

## Summary

Produce the Phase 16 coverage map (every named scenario → citation or new test), implement the genuinely new tests (Anomaly model-stability, Risk drift-sensitivity, LLM evidence-grounding checks), implement the cross-module integration tests (HITL round-trips, Ingestion large/malformed/repeated scenarios), and consolidate the Data-category suite by reference — all living in `backend/tests/`, not a new `app/` module, since this feature adds no production code.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: pytest, pytest's fixture/parametrize machinery for the consolidated Data suite; httpx/TestClient for real (non-mocked) integration tests against FastAPI's test app

**Storage**: `docs/testing/phase16_coverage_map.md` (the FR-001 artifact) plus the test files themselves — no new application data store

**Testing**: This feature *is* tests — its own "testing" is the coverage-map completeness check (FR-001/SC-001) and confirming every new/integration test actually executes and reports a real pass/fail/limitation

**Target Platform**: Same test environment as all prior phases (pytest run locally and in CI once Phase 20 exists)

**Project Type**: Test suite only — no new backend module; organized under `backend/tests/integration/` and `backend/tests/coverage_map/`

**Performance Goals**: No phase-specific numeric target; integration tests should complete in a reasonable CI-friendly time (e.g., full suite under 5 minutes) given the modest current data scale

**Constraints**: Zero duplicated test logic for already-covered scenarios (FR-009, SC-005); honest reporting of data-scale limitations, never silent skips (FR-008, SC-006)

**Scale/Scope**: Six categories × their named scenarios, cross-referenced against 15 prior features' Success Criteria sections

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Related — the new stability/drift tests exercise Phase 7/9's empirically-selected production models directly | PASS |
| II. No Fabricated Values | Applies — FR-008 requires honest reporting of data-scale limitations rather than fabricated confidence | PASS |
| III. Deterministic-First, ML-Second | Applies — Data-category consolidation centers on Phase 3's deterministic floor | PASS |
| IV. Human-in-the-Loop | Applies directly — FR-004's HITL integration tests are the strongest real-world proof of Principle IV working end-to-end | PASS |
| V. Constrained, Auditable Remediation | Applies — the accept→remediate→revalidate integration test directly proves Principle V's full loop | PASS |
| VI. Modular Backend, No Monolith | Applies — tests exercise real module boundaries (FR-004), proving the modular architecture actually composes | PASS |
| VII. Temporal Integrity | Related — drift-sensitivity and temporal-split-correctness scenarios directly test this principle's enforcement | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/016-testing-suite/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md   # /speckit.tasks — not created here
```

### Source Code (repository root)

```text
docs/
└── testing/
    └── phase16_coverage_map.md    # FR-001 — the CoverageMapEntry list, human-reviewable

backend/
└── tests/
    ├── coverage_map/
    │   └── test_coverage_map_completeness.py   # SC-001 — validates the map itself
    ├── anomaly/
    │   └── test_model_stability.py               # FR-002, SC-002
    ├── risk/
    │   └── test_drift_sensitivity.py               # FR-003, SC-002
    ├── llm/
    │   └── test_evidence_grounding.py                # FR-007
    ├── integration/
    │   ├── test_hitl_accept_remediate_revalidate.py  # FR-004, SC-003
    │   ├── test_hitl_reject_feedback_recalculate.py  # FR-004, SC-003
    │   ├── test_ingestion_large_file.py               # FR-005, SC-004
    │   ├── test_ingestion_malformed_batch.py           # FR-005, SC-004
    │   └── test_ingestion_repeated_uploads.py           # FR-005, SC-004
    └── data_suite/
        └── test_data_category_suite.py    # FR-006, SC-005 — imports/references Phase 1/2/3 tests
```

**Structure Decision**: No new `app/` module — this feature is entirely `tests/` and one `docs/testing/` artifact, reflecting that it adds test coverage and a coverage-gap analysis, not production functionality.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
