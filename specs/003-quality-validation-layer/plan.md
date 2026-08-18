# Implementation Plan: Quality Validation Layer

**Branch**: `003-quality-validation-layer` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-quality-validation-layer/spec.md`

## Summary

Build the `quality` module: Great Expectations suites per column category (built from Phase 1's categorization), executed against Phase 2's cleaned output, producing both per-check `ExpectationCheckResult` records and a recomputable composite 0-100 `QualityScoreResult` using the MissingRate/DuplicateRate formulas and PASS/WARNING/CRITICAL bands from MVP_CONTEXT.md Section 3.1. This is the deterministic floor (constitution Principle III) that Phase 4 (baseline) and Phase 8 (risk dataset) read from.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: `great_expectations`, pandas; reads Phase 1's `column_categories.json` and Phase 2's `data/cleaned/inpatient_cleaned.csv` + `quality_issues.json`

**Storage**: `data/reports/quality_results.json` (ExpectationCheckResult[] + QualityScoreResult) for the MVP file-based path, consistent with Phases 1-2; the `quality_results` table named in MVP_CONTEXT.md Section 3 ("Database" core tables) is the eventual DB home once ingestion/ORM wiring lands, but this feature's own scope is producing correct results, not the persistence backend choice

**Testing**: pytest, with fixtures covering: a column with legitimately high missingness (must not tank the score), a negative-amount cell (must trigger the amount validity CRITICAL), and a full re-run for determinism (SC-004)

**Target Platform**: Same as Phases 1-2 (local dev now, Docker Compose validated later in Phase 19)

**Project Type**: Backend module — new `backend/app/quality/` module per constitution Principle VI ("quality (Great Expectations)" is its own named module boundary in MVP_CONTEXT.md Section 3)

**Performance Goals**: Full suite execution against the 58,066-row cleaned batch completes in a time budget consistent with the rest of the pipeline (no numeric target specified in MVP_CONTEXT.md for this phase specifically — plan should reuse the ~2-3 minute budget precedent from Phases 1-2 unless GX's own overhead requires a documented adjustment)

**Constraints**: Composite score must be exactly recomputable from persisted check results (SC-001); per-column completeness thresholds must be calibrated, not universal (FR-007); deterministic across repeated runs (SC-004)

**Scale/Scope**: Six column categories, ~197 columns, one suite per category (not per column) with column-specific expectation instances inside each suite

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — GX is deterministic, not a benchmarked model | PASS |
| II. No Fabricated Values | Applies directly — FR-013, SC-001 | PASS |
| III. Deterministic-First, ML-Second | This feature **is** the deterministic floor the principle describes — direct implementation of it | PASS |
| IV. Human-in-the-Loop | Not applicable | PASS |
| V. Constrained, Auditable Remediation | Not applicable — no remediation yet | PASS |
| VI. Modular Backend, No Monolith | Applies — new `quality` module, distinct from `data_engineering`, matching Section 3's module list | PASS |
| VII. Temporal Integrity | Applies loosely — freshness expectation must respect batch chronology; no leakage risk at this phase (no train/val/test split involved) | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-quality-validation-layer/
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
│   └── quality/
│       ├── __init__.py
│       ├── suite_builder.py       # category -> ExpectationSuite construction from column_categories.json
│       ├── expectations/
│       │   ├── completeness.py    # per-column-calibrated missingness checks (FR-007)
│       │   ├── uniqueness.py      # CLM_ID uniqueness (FR-002)
│       │   ├── validity.py        # amount >= 0, code-set membership (FR-003, FR-006)
│       │   ├── range_checks.py    # date range, utilization bounds (FR-005)
│       │   └── freshness.py       # ingestion-window freshness (FR-008)
│       ├── scoring_service.py     # MissingRate/DuplicateRate + composite score (FR-009, FR-010)
│       ├── schemas.py             # ExpectationCheckResult, QualityScoreResult
│       └── router.py              # POST /quality/validate, GET /quality/results
└── tests/
    └── quality/
        ├── test_suite_builder.py
        ├── test_scoring_service.py
        └── test_completeness_calibration.py

data/
└── reports/quality_results.json   # ExpectationCheckResult[] + QualityScoreResult
```

**Structure Decision**: New `quality` module (not folded into `data_engineering`), matching MVP_CONTEXT.md Section 3's explicit module list where `quality (Great Expectations)` is named separately from `data_engineering (profiling/cleaning/standardization)`.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
