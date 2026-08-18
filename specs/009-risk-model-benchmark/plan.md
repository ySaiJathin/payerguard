# Implementation Plan: Risk Model Benchmark

**Branch**: `009-risk-model-benchmark` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-risk-model-benchmark/spec.md`

## Summary

Build the `risk.benchmark` sub-module: Logistic Regression/Random Forest/XGBoost fit on Phase 8's risk dataset using Phase 6's exact `TemporalSplit`, evaluated on accuracy/precision/recall/F1/ROC-AUC/PR-AUC/calibration/FNR, with production selection prioritizing recall+PR-AUC per a documented ranking rule — mirroring Phase 7's benchmark discipline for the risk track.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: scikit-learn (`LogisticRegression`, `RandomForestClassifier`, calibration curve utilities), xgboost; reads Phase 8's `risk_dataset.csv` and Phase 6's `temporal_split.json`

**Storage**: `data/models/risk/*.pkl`, `data/reports/risk_benchmark_results.json` for the MVP file-based path; `risk_predictions` table (MVP_CONTEXT.md Section 3) is the eventual DB home

**Testing**: pytest — a leakage test mirroring Phase 7's pattern (SC-001); a selection-reproducibility test (SC-003); a split-consistency cross-check against Phase 6 (SC-006)

**Target Platform**: Same as prior phases

**Project Type**: Backend module — `backend/app/risk/benchmark/` sub-package (Section 3's `risk (logistic, random_forest, xgboost, benchmark, scoring)` module)

**Performance Goals**: No phase-specific numeric target; three-model fit+tune+evaluate expected well under 5 minutes at current data scale

**Constraints**: Strict train/validation/test isolation reusing Phase 6's exact split (FR-002, FR-003); selection must reflect real results even if XGBoost loses (FR-006); calibration always reported (FR-004, SC-005)

**Scale/Scope**: Three models × Phase 8's window-grain rows (tens of rows at current scale, explicitly acknowledged as a data-scale limitation in spec Assumptions)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | This feature **is** the direct implementation of this principle for the risk track | PASS |
| II. No Fabricated Values | Applies — FR-010 | PASS |
| III. Deterministic-First, ML-Second | Applies — built entirely on top of Phase 3's deterministic floor and Phase 7's already-benchmarked anomaly signal | PASS |
| IV. Human-in-the-Loop | Not applicable — no remediation/incidents yet | PASS |
| V. Constrained, Auditable Remediation | Not applicable | PASS |
| VI. Modular Backend, No Monolith | Applies — `benchmark` sub-package within `risk`, alongside `dataset` (Phase 8) and future `scoring` (Phase 10) | PASS |
| VII. Temporal Integrity | Applies with particular force — FR-002 explicitly forbids recomputing/reshuffling Phase 6's split; this is the phase constitution Principle VII names directly ("dataset spans 2015–2022... temporal split... never a random shuffle") | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/009-risk-model-benchmark/
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
│       └── benchmark/
│           ├── __init__.py
│           ├── logistic.py
│           ├── random_forest.py
│           ├── xgboost_model.py
│           ├── calibration.py          # FR-004, FR-005 calibration metric
│           ├── benchmark_runner.py     # orchestrates fit/tune/evaluate (FR-001-FR-004)
│           ├── model_selection.py      # FR-005, FR-006, FR-007
│           ├── schemas.py              # RiskModelCandidate, RiskBenchmarkResult, ProductionRiskModelSelection
│           └── router.py               # POST /risk/benchmark, GET /risk/benchmark/results
└── tests/
    └── risk/
        └── benchmark/
            ├── test_leakage_isolation.py
            ├── test_model_selection.py
            └── test_split_consistency.py   # SC-006

data/
├── models/risk/{logistic,random_forest,xgboost}.pkl
└── reports/risk_benchmark_results.json
```

**Structure Decision**: `benchmark` sub-package inside the `risk` module, alongside `dataset` (Phase 8) and reserving `scoring` for Phase 10 — matches Section 3's `risk (logistic, random_forest, xgboost, benchmark, scoring)` naming exactly.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
