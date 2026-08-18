# Implementation Plan: Feature Engineering

**Branch**: `005-feature-engineering` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-feature-engineering/spec.md`

## Summary

Build the `features` module's claim-level and window-level feature computation: amount ratios, length-of-stay (reusing Phase 4's derivation), date-derived attributes, encoded categoricals (with an explicit unseen-category policy), and provider frequency at claim grain; claim count, amount stats, missingness/duplicate/invalid-status %, and volume/amount deviation-vs-baseline at window grain, reusing Phase 4's `BaselineSnapshot` and window definition. The window schema reserves a nullable `anomaly_count` field for Phase 7 to populate later, per the resolved clarification.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: pandas, numpy, scikit-learn (`OneHotEncoder`/category encoding utilities); reads Phase 2's cleaned data, Phase 3's quality results, Phase 4's `BaselineSnapshot`

**Storage**: `data/features/claim_features.parquet` (or `.csv`) and `data/features/window_features.parquet` for the MVP file-based path; the `features` table (MVP_CONTEXT.md Section 3 core tables) is the eventual DB home, consistent with the file-first precedent

**Testing**: pytest — a missing-input-produces-null test (SC-001), an unseen-category encoding test (SC-005), a schema/contract test asserting `anomaly_count` is present and null pre-Phase-7 (SC-004)

**Target Platform**: Same as prior phases

**Project Type**: Backend module — new `backend/app/features/` module (claim-level, window-level, selection sub-areas per MVP_CONTEXT.md Section 3's `features (claim-level, window-level, selection)` module boundary — this feature covers claim-level + window-level; Phase 6 adds selection to the same module)

**Performance Goals**: No phase-specific numeric target in MVP_CONTEXT.md; reuse the ~2-3 minute budget precedent for full-file runs

**Constraints**: No fabricated feature values (FR-010); `anomaly_count` must be genuinely null, not zero, pre-Phase-7 (FR-008, SC-004); window definition must match Phase 4's exactly or the mismatch must be surfaced (FR-007)

**Scale/Scope**: ~20,867 claims, window count per Phase 4's window definition; feature count driven by the categorical encoding scheme chosen per column cardinality

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — feature engineering precedes model benchmarking | PASS |
| II. No Fabricated Values | Applies directly — FR-001, FR-002, FR-004, FR-010 | PASS |
| III. Deterministic-First, ML-Second | Applies — features are deterministic transformations of already-validated (Phase 3) data | PASS |
| IV. Human-in-the-Loop | Not applicable | PASS |
| V. Constrained, Auditable Remediation | Not applicable | PASS |
| VI. Modular Backend, No Monolith | Applies — new `features` module, matching Section 3's list | PASS |
| VII. Temporal Integrity | Applies — window-level features must respect chronological window definitions from Phase 4; no future-window information may leak into a past window's deviation calculation | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-feature-engineering/
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
│       ├── __init__.py
│       ├── claim_level/
│       │   ├── amount_ratios.py
│       │   ├── length_of_stay.py       # reuses Phase 4's derivation logic (shared util)
│       │   ├── date_features.py
│       │   ├── categorical_encoding.py # EncodingScheme + unseen-category policy
│       │   └── provider_frequency.py
│       ├── window_level/
│       │   ├── window_aggregates.py    # claim count, amount stats, missingness/dup/invalid %
│       │   └── deviation_features.py   # vs Phase 4 BaselineSnapshot
│       ├── schemas.py                   # ClaimFeatures, WindowFeatures, EncodingScheme
│       └── router.py                    # POST /features/compute, GET /features/claims, GET /features/windows
└── tests/
    └── features/
        ├── test_amount_ratios.py
        ├── test_categorical_encoding.py
        ├── test_deviation_features.py
        └── test_window_schema_anomaly_count.py  # SC-004

data/
└── features/
    ├── claim_features.csv
    └── window_features.csv
```

**Structure Decision**: New `features` module with `claim_level/` and `window_level/` sub-packages, anticipating Phase 6 adding a `selection/` sub-package to the same module (per Section 3's combined `features (claim-level, window-level, selection)` boundary) rather than three separate top-level modules.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
