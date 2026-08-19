# Implementation Plan: Data Profiling Foundation

**Branch**: `001-data-profiling-foundation` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-data-profiling-foundation/spec.md`

## Summary

Build the `data_engineering` module's profiling capability: read `data/raw/inpatient.csv` (pipe-delimited, 197 columns, 58,066 rows), compute a full per-column and file-level statistical profile, categorize every column into one of six fixed categories using MVP_CONTEXT.md Section 2.3 as ground truth, persist both as durable report artifacts, and generate a reproducible, claim-consistent sample under `data/sampled/`. This is a read-only, file-in/report-out capability with no database writes and no ML — it is the foundation every later phase (cleaning, quality, baseline, features, models) reads from.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: pandas (profiling, distribution stats, sampling), numpy (numeric computation)

**Storage**: Filesystem only for this feature — `data/raw/inpatient.csv` (read-only input), `data/sampled/` (sample output), a reports directory for the profiling/categorization artifacts. No PostgreSQL tables are required for profiling itself (the `claims` table and friends are populated starting Phase 2/3); this phase only needs to reference the shared config/report locations later phases will also use.

**Testing**: pytest, with fixture-driven tests (a small synthetic pipe-delimited CSV fixture plus one test asserting real-file statistics match MVP_CONTEXT.md Section 2.2 ground truth)

**Target Platform**: Linux container (via Docker Compose per repo scaffolding) and local Windows/macOS/Linux dev execution before containerization (Phase 18 sequencing — containerization is not validated yet)

**Project Type**: Backend module within the single modular-monolith service (`backend/app/data_engineering/`) — no frontend or second service involved

**Performance Goals**: Full profiling run completes in under 2 minutes on the 58,066-row file on standard developer hardware (SC-001)

**Constraints**: Must never modify, move, or delete `data/raw/inpatient.csv`; sampling must be deterministic/reproducible given the same seed and configuration; no statistic may be hardcoded (constitution Principle II)

**Scale/Scope**: 197 columns, 58,066 rows today; profiling logic must not assume this exact row/column count is permanent (further batches may still be loaded; the continuous-ingestion phase was removed 2026-08-18), only that the schema shape is CMS Inpatient RIF-like

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — no anomaly/risk model in this phase | PASS |
| II. No Fabricated Values | Applies directly — every reported statistic (FR-001–FR-006) must be computed at run time from the current file; enforced by FR-012 and SC-003/SC-005 | PASS |
| III. Deterministic-First, ML-Second | Not applicable — Great Expectations layer is Phase 3 | PASS |
| IV. Human-in-the-Loop | Not applicable — no remediation/incidents in this phase | PASS |
| V. Constrained, Auditable Remediation | Not applicable | PASS |
| VI. Modular Backend, No Monolith | Applies — profiling/categorization/sampling implemented as their own files inside the `data_engineering` module, not folded into `app/main.py` | PASS |
| VII. Temporal Integrity | Applies loosely — sampling selects whole claims and must not silently bias the sample toward a time range; no train/val/test split exists yet at this phase | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-data-profiling-foundation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit.tasks — not created by this command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── data_engineering/
│   │   ├── __init__.py
│   │   ├── router.py            # /data-engineering/profile, /data-engineering/sample endpoints
│   │   ├── profiling_service.py # column + file-level statistics computation
│   │   ├── categorization.py    # fixed column → category mapping/logic
│   │   ├── sampling_service.py  # claim-consistent, seeded sampling
│   │   ├── schemas.py           # Pydantic models: ColumnProfile, ProfilingReport, SampleManifest
│   │   └── report_writer.py     # persists report artifacts (Markdown + JSON) to disk
│   └── main.py                   # wires data_engineering.router in (no business logic here)
└── tests/
    ├── data_engineering/
    │   ├── test_profiling_service.py
    │   ├── test_categorization.py
    │   └── test_sampling_service.py
    └── fixtures/
        └── inpatient_sample.csv  # small synthetic pipe-delimited fixture for fast unit tests

data/
├── raw/inpatient.csv    # existing, read-only input
├── sampled/              # sampling output (created by this feature)
└── reports/               # profiling_report.md + profiling_report.json + column_categories.json
```

**Structure Decision**: Single backend service (Option 1 pattern), with this feature living entirely inside a new `data_engineering` module per constitution Principle VI. No frontend involvement (Phase 17 is deferred). Report artifacts land under `data/reports/` so later phases (baseline, quality) and human reviewers can read them without hitting an API.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
