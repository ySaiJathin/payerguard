# Implementation Plan: Historical Baseline

**Branch**: `004-historical-baseline` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-historical-baseline/spec.md`

## Summary

Build the `baseline` module: compute volume-per-window, amount distribution, data-health (missingness/duplicate/status-distribution), and length-of-stay baselines from Phase 2's cleaned historical data (cross-checked against Phase 3's quality results for missingness/duplicate figures), persist them as a versioned `BaselineSnapshot` with source-data provenance, and expose recomputation without code changes as data grows (Phase 15). This is the "what does normal look like" reference that Phase 5 (window-level deviation features) and Phase 7 (anomaly detection) read from.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: pandas, numpy; reads Phase 2's `data/cleaned/inpatient_cleaned.csv` and Phase 3's `data/reports/quality_results.json`

**Storage**: `data/reports/baseline_snapshot.json` for the MVP file-based path; the `baseline_metrics` table (MVP_CONTEXT.md Section 3 core tables) is the eventual DB home, consistent with the file-first precedent from Phases 1-3

**Testing**: pytest — a determinism/no-hardcoding test that mutates a fixture's amount values and asserts the computed baseline changes accordingly (SC-002); a length-of-stay exclusion test with an injected missing discharge date (SC-004)

**Target Platform**: Same as Phases 1-3

**Project Type**: Backend module — new `backend/app/baseline/` module, matching Section 3's named module boundary (`baseline`)

**Performance Goals**: No phase-specific numeric target in MVP_CONTEXT.md; reuse the ~2-3 minute budget precedent from Phases 1-3 for the full historical file

**Constraints**: Must not fabricate any statistic (FR-009); must not resurrect a processing-time/SLA field (FR-006, SC-005); must record source-data provenance on every snapshot (FR-007, SC-006)

**Scale/Scope**: Full 58,066-row historical file today; must remain correct as Phase 15 adds more batches (FR-008)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — no models, pure statistics | PASS |
| II. No Fabricated Values | Applies directly — FR-009, SC-001, SC-002 | PASS |
| III. Deterministic-First, ML-Second | Applies — baseline is deterministic and computed after Phase 3's deterministic quality layer, feeding later ML phases | PASS |
| IV. Human-in-the-Loop | Not applicable | PASS |
| V. Constrained, Auditable Remediation | Not applicable | PASS |
| VI. Modular Backend, No Monolith | Applies — new `baseline` module, matching Section 3's list | PASS |
| VII. Temporal Integrity | Applies directly — this is the first phase computing anything window/time-based; volume-per-window MUST be ordered chronologically, no shuffling, consistent with the constitution's dataset-spans-2015-2022 note | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-historical-baseline/
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
│   └── baseline/
│       ├── __init__.py
│       ├── window_definition.py     # documented window config (date-based, not wall-clock)
│       ├── volume_baseline.py       # FR-001, FR-010
│       ├── amount_baseline.py       # FR-002
│       ├── data_health_baseline.py  # FR-003, FR-004 (reads Phase 3 quality_results.json)
│       ├── length_of_stay_baseline.py # FR-005
│       ├── schemas.py               # BaselineSnapshot and sub-entities
│       ├── snapshot_service.py      # assembles + persists BaselineSnapshot with provenance (FR-007)
│       └── router.py                # POST /baseline/compute, GET /baseline
└── tests/
    └── baseline/
        ├── test_amount_baseline.py
        ├── test_length_of_stay_baseline.py
        └── test_no_hardcoding.py    # SC-002: mutate fixture, assert output changes

data/
└── reports/baseline_snapshot.json
```

**Structure Decision**: New `baseline` module per Section 3's module list, reading (not duplicating) Phase 2/3 outputs to keep missingness/duplicate figures consistent with what those phases already measured (FR-003).

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
