# Implementation Plan: Risk Dataset Construction

**Branch**: `008-risk-dataset-construction` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-risk-dataset-construction/spec.md`

## Summary

Build the `risk.dataset` sub-module: assemble one window-grain `RiskDatasetRow` per Phase 4/5 window from Phase 3 (GX failures), Phase 7 (anomaly_count), Phase 5 (deviations), and Phase 4 (historical quality-failure rate) outputs; define, document, and apply a single explicit `InvestigationRiskLabelFormula` combining quality-failure rate, anomaly frequency, and volume/amount deviation; report label distribution. This dataset is Phase 9's sole training input.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: pandas, numpy; reads Phase 3/4/5/7 persisted outputs directly (no independent recomputation, per FR-002)

**Storage**: `data/risk/risk_dataset.csv` + `data/risk/investigation_risk_label_formula.md` (the documented formula artifact, per FR-003) for the MVP file-based path; the `risk_predictions`-adjacent table structure (MVP_CONTEXT.md Section 3) formalizes later

**Testing**: pytest — a provenance test asserting every `RiskDatasetRow` field matches its upstream source exactly (SC-001); a label-reproducibility test (SC-002); a zero-claim-window label test (SC-004)

**Target Platform**: Same as prior phases

**Project Type**: Backend module — new `backend/app/risk/dataset/` sub-package (Section 3's `risk (logistic, random_forest, xgboost, benchmark, scoring)` module gains a `dataset` construction step feeding it)

**Performance Goals**: No phase-specific numeric target; this is a join/aggregation over already-computed data, expected to run in well under a minute at current scale

**Constraints**: Zero independently-recomputed fields (FR-002); label must reference Section 2.4's reasoning explicitly in a written artifact (FR-004, SC-003); fails fast if Phase 7 enrichment incomplete (FR-008)

**Scale/Scope**: One row per window (tens of rows at current data scale, matching Phase 4/5's window count)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — this feature builds the dataset, doesn't select a model (that's Phase 9) | PASS |
| II. No Fabricated Values | Applies with particular force — this is the exact judgment call the constitution names directly ("the SLA-breach label in Phase 8... must be written down and justified") | PASS |
| III. Deterministic-First, ML-Second | Applies — every input to this dataset is itself already-validated/deterministic (Phase 3) or empirically-benchmarked (Phase 7) output, not an assumption | PASS |
| IV. Human-in-the-Loop | Not applicable | PASS |
| V. Constrained, Auditable Remediation | Not applicable | PASS |
| VI. Modular Backend, No Monolith | Applies — `dataset` sub-package within the `risk` module, distinct from the `logistic`/`random_forest`/`xgboost`/`benchmark`/`scoring` sub-files Phase 9 adds | PASS |
| VII. Temporal Integrity | Applies — FR-007 carries chronological ordering explicitly so Phase 9's temporal split has no ambiguity | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/008-risk-dataset-construction/
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
│       └── dataset/
│           ├── __init__.py
│           ├── row_assembly.py         # FR-001, FR-002 — joins Phase 3/4/5/7 outputs
│           ├── label_formula.py        # FR-003, FR-004, FR-005, FR-006 — documented + versioned
│           ├── label_distribution.py   # FR-009
│           └── router.py               # POST /risk/dataset/build, GET /risk/dataset
└── tests/
    └── risk/
        └── dataset/
            ├── test_row_provenance.py
            ├── test_label_reproducibility.py
            └── test_zero_claim_window_label.py

data/
└── risk/
    ├── risk_dataset.csv
    └── investigation_risk_label_formula.md   # the documented, reviewable formula artifact
```

**Structure Decision**: `dataset` sub-package inside a new `risk` module, since Section 3 names `risk` as one module covering `logistic, random_forest, xgboost, benchmark, scoring` — this feature adds the `dataset` construction step that all of those will consume starting Phase 9.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
