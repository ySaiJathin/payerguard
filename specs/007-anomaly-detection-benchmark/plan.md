# Implementation Plan: Anomaly Detection Benchmark

**Branch**: `007-anomaly-detection-benchmark` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-anomaly-detection-benchmark/spec.md`

## Summary

Build the `anomaly` module: IQR/HBOS/Isolation Forest/LOF implementations fit on Phase 6's train split, calibrated on validation, evaluated once on test; a synthetic anomaly-injection harness (5 types) applied only to validation/test copies; a benchmark comparison producing precision/recall/F1/FPR/latency/execution-time per model; empirical production-model selection; and the one-time enrichment call that populates Phase 5's deferred `WindowFeatures.anomaly_count`.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: scikit-learn (`IsolationForest`, `LocalOutlierFactor`), pyod (HBOS reference implementation) or an equivalent HBOS implementation, numpy/pandas (IQR baseline, injection harness); reads Phase 6's `TemporalSplit` and `SelectedFeatureSet`

**Storage**: `data/models/anomaly/*.pkl` (fitted model artifacts), `data/reports/anomaly_benchmark_results.json` (`BenchmarkResult[]` + `ProductionModelSelection`) for the MVP file-based path; the `anomaly_results` table (MVP_CONTEXT.md Section 3 core tables) is the eventual DB home

**Testing**: pytest — a leakage test mirroring Phase 6's pattern (corrupt test split, assert fitted models/thresholds unchanged, SC-001); an injection-harness test asserting all 5 types produce labeled instances (SC-002); an idempotency test for the `anomaly_count` enrichment step (SC-006)

**Target Platform**: Same as prior phases

**Project Type**: Backend module — new `backend/app/anomaly/` module (`iqr`, `hbos`, `isolation_forest`, `lof`, `benchmark` per MVP_CONTEXT.md Section 3's explicit module boundary)

**Performance Goals**: No phase-specific numeric target in MVP_CONTEXT.md beyond "detection latency/execution time" being *measured* metrics, not targets; budget the full benchmark (4 models × fit + calibrate + evaluate) generously (e.g., under 10 minutes) given the ~20,867-claim scale

**Constraints**: Strict train/validation/test isolation (FR-002, FR-005); production selection must reflect real results even if HBOS loses (FR-007, constitution Principle I); `anomaly_count` enrichment idempotent (FR-011)

**Scale/Scope**: Four models × five injection types × per-model/per-injection-type metrics; one production selection; window-level enrichment across all windows from Phase 5

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | This feature **is** the direct implementation of this principle for the anomaly track — production selection must follow real benchmark results, not the "expected HBOS" assumption | PASS |
| II. No Fabricated Values | Applies — FR-012, every metric computed from real train/val/test runs | PASS |
| III. Deterministic-First, ML-Second | Applies — this ML layer runs on top of, and does not replace, Phase 3's deterministic quality floor | PASS |
| IV. Human-in-the-Loop | Not applicable — no remediation/incidents yet | PASS |
| V. Constrained, Auditable Remediation | Not applicable | PASS |
| VI. Modular Backend, No Monolith | Applies — new `anomaly` module with `iqr`/`hbos`/`isolation_forest`/`lof`/`benchmark` sub-files, matching Section 3 exactly | PASS |
| VII. Temporal Integrity | Applies directly — reuses Phase 6's chronological split, no shuffling, injection harness never touches training data | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/007-anomaly-detection-benchmark/
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
│   └── anomaly/
│       ├── __init__.py
│       ├── iqr.py
│       ├── hbos.py
│       ├── isolation_forest.py
│       ├── lof.py
│       ├── injection_harness.py     # 5 injection types, validation/test-only (FR-004, FR-005, FR-006)
│       ├── benchmark.py             # orchestrates fit/calibrate/evaluate across all 4 (FR-001-FR-003)
│       ├── model_selection.py       # empirical selection + tie-breaking (FR-007, FR-008)
│       ├── window_enrichment.py     # populates WindowFeatures.anomaly_count (FR-010, FR-011)
│       ├── schemas.py               # AnomalyModelCandidate, InjectedAnomalyInstance, BenchmarkResult, ProductionModelSelection
│       └── router.py                # POST /anomaly/benchmark, GET /anomaly/results, POST /anomaly/enrich-windows
└── tests/
    └── anomaly/
        ├── test_leakage_isolation.py
        ├── test_injection_harness.py
        ├── test_model_selection.py
        └── test_window_enrichment_idempotency.py

data/
├── models/anomaly/{iqr,hbos,isolation_forest,lof}.pkl
└── reports/anomaly_benchmark_results.json
```

**Structure Decision**: New `anomaly` module matching Section 3's exact sub-file naming (`iqr, hbos, isolation_forest, lof, benchmark`). `window_enrichment.py` is the bridge back to Phase 5's `features` module via its dedicated `PATCH /features/windows/{window_id}/anomaly-count` contract.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
