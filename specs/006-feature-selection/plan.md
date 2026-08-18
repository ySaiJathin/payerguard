# Implementation Plan: Feature Selection

**Branch**: `006-feature-selection` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-feature-selection/spec.md`

## Summary

Build the `features.selection` sub-module: establish the shared temporal 70/15/15 split (reused by Phases 7 and 9), then run three-stage selection — structural (Stage 1: constant/near-constant/duplicate/raw-ID/high-missingness/leakage drops), statistical (Stage 2: correlation/MI/variance/cardinality/missingness thresholds), and model-based (Stage 3: XGBoost/permutation importance/RFE) — fit exclusively on train+validation, with every drop decision recorded for audit and the deferred `anomaly_count` field exempted from missingness-based dropping.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: pandas, numpy, scikit-learn (`mutual_info_classif`/`VarianceThreshold`/`RFE`), xgboost; reads Phase 5's `ClaimFeatures`/`WindowFeatures`, Phase 1's categorization, Phase 3's quality results, Phase 4's baseline

**Storage**: `data/features/temporal_split.json`, `data/features/selected_feature_set.json`, `data/features/feature_drop_decisions.json` for the MVP file-based path

**Testing**: pytest — a test-set-isolation test that corrupts the test-split portion and asserts Stage 2/3 outputs are byte-identical (SC-003); a known-constant-column drop test (SC-002); an `anomaly_count`-exemption test (SC-005)

**Target Platform**: Same as prior phases

**Project Type**: Backend module — `backend/app/features/selection/` sub-package, extending the `features` module from Phase 5 (Section 3's combined `features (claim-level, window-level, selection)` boundary)

**Performance Goals**: No phase-specific numeric target in MVP_CONTEXT.md; Stage 3's XGBoost/RFE step is the most compute-intensive — budget generously (e.g., under 5 minutes) given the modest scale (~20,867 claims)

**Constraints**: Zero leakage from test split into any Stage 2/3 statistic (FR-010, SC-003); every drop decision recorded (FR-009, SC-004); `anomaly_count` exempted from missingness-based drops (FR-008, SC-005)

**Scale/Scope**: Starts from Phase 5's full claim-level/window-level feature set (dozens of engineered features plus encoded categoricals); narrows to the final modeling feature set feeding Phases 7 and 9

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Related but distinct — Stage 3's importance ranking informs feature choice, not model choice; the actual model benchmark is Phase 7/9 | PASS |
| II. No Fabricated Values | Applies — every threshold/statistic/importance score is computed from real train+validation data (FR-006, FR-007) | PASS |
| III. Deterministic-First, ML-Second | Applies — Stage 1/2 are deterministic; Stage 3 uses XGBoost but only for importance ranking, not as a production model decision (that's Phase 9) | PASS |
| IV. Human-in-the-Loop | Not applicable | PASS |
| V. Constrained, Auditable Remediation | Not applicable | PASS |
| VI. Modular Backend, No Monolith | Applies — `selection/` sub-package within the existing `features` module | PASS |
| VII. Temporal Integrity | This feature is the **direct implementation** of this principle for the whole pipeline — establishes the shared temporal split every later ML phase reuses | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/006-feature-selection/
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
│   └── features/
│       └── selection/
│           ├── __init__.py
│           ├── temporal_split.py       # FR-001, FR-002 — shared by Phase 7/9
│           ├── stage1_structural.py     # FR-003, FR-004, FR-005
│           ├── stage2_statistical.py    # FR-006
│           ├── stage3_model_based.py    # FR-007, uses provisional target per research.md
│           ├── drop_decision_log.py     # FR-009
│           └── router.py                # POST /features/select, GET /features/selected, GET /features/split
└── tests/
    └── features/
        └── selection/
            ├── test_temporal_split.py
            ├── test_stage1_structural.py
            ├── test_leakage_isolation.py   # SC-003
            └── test_anomaly_count_exempt.py # SC-005
```

**Structure Decision**: `selection/` sub-package inside the existing `features` module (not a new top-level module), matching Section 3's combined module boundary and Phase 5's plan which anticipated this addition.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
