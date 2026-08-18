# Implementation Plan: Cleaning & Standardization

**Branch**: `002-cleaning-standardization` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-cleaning-standardization/spec.md`

## Summary

Build the `data_engineering` module's cleaning capability: validate the schema against Phase 1's categorization, convert every column to its category-implied dtype, standardize dates to ISO 8601, detect duplicates and invalid values, and record every actual correction as an `(original_value, cleaned_value, quality_issue)` audit entry — while never fabricating a replacement for a missing value. Output is a deduplicated, typed, standardized dataset plus a queryable audit trail that Phase 3 (Great Expectations) reads to compute the quality score.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: pandas (dtype conversion, dedup, groupby), numpy; reuses Phase 1's `column_categories.json` output as the schema source of truth

**Storage**: Filesystem for this feature's own outputs (`data/cleaned/inpatient_cleaned.parquet` or `.csv`, `data/reports/quality_issues.json` or a `quality_issues` table); a PostgreSQL `claims` table (per MVP_CONTEXT.md Section 3 "Database" core tables) becomes the eventual home for cleaned claim-line data, but this feature can be built and tested file-in/file-out first, with DB persistence wired in via the `claims`/`claim_batches` tables once ingestion (module boundary already named in Section 3) exists — this plan targets the file-based path for the MVP build order, matching Phase 1's file-based precedent.

**Testing**: pytest, with a synthetic fixture containing an injected duplicate row, an injected negative amount, a malformed date string, and a missing cell, asserting each produces exactly the expected `QualityIssueRecord`

**Target Platform**: Linux container (Docker Compose) / local dev, same as Phase 1 — containerization validation itself remains deferred to Phase 19

**Project Type**: Backend module, same `backend/app/data_engineering/` package as Phase 1, adding cleaning-specific files rather than a new module (constitution Principle VI: one module per domain, not one file per phase)

**Performance Goals**: Cleaning the full 58,066-row file completes in under 3 minutes (SC-003)

**Constraints**: Idempotent (SC-004); never fabricates values for missing cells (SC-005, constitution Principle II); never physically deletes rows from source files (only excludes duplicates from the deduplicated *working* dataset)

**Scale/Scope**: Same 58,066-row / 197-column scope as Phase 1; must also work against Phase 1's smaller `data/sampled/` output for fast iteration during development

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicability | Status |
|---|---|---|
| I. Empirical Model Selection | Not applicable — no models in this phase | PASS |
| II. No Fabricated Values | Applies directly — FR-006/FR-011 and SC-005 explicitly forbid fabricating replacements for missing/invalid values | PASS |
| III. Deterministic-First, ML-Second | Applies in spirit — this is deterministic cleaning logic feeding the deterministic GX layer (Phase 3), no ML involved | PASS |
| IV. Human-in-the-Loop | Not applicable — no remediation/incidents yet | PASS |
| V. Constrained, Auditable Remediation | Related but distinct — this feature's audit trail (`QualityIssueRecord`) is the data-level precedent for the incident-level remediation audit trail in Phase 13/17; not itself the remediation engine | PASS |
| VI. Modular Backend, No Monolith | Applies — cleaning logic added as new files inside the existing `data_engineering` module (`cleaning_service.py`, `dtype_conversion.py`, `date_standardization.py`, `duplicate_detection.py`, `invalid_value_detection.py`), not appended to `profiling_service.py` | PASS |
| VII. Temporal Integrity | Applies loosely — date standardization must not alter chronological ordering; no train/val/test split exists at this phase | PASS |

No violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-cleaning-standardization/
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
│   └── data_engineering/
│       ├── cleaning_service.py       # orchestrates schema validation → dtype → missing → dedup → invalid → date std.
│       ├── dtype_conversion.py       # category-driven dtype coercion (reads column_categories.json)
│       ├── date_standardization.py   # DD-Mon-YYYY -> ISO 8601
│       ├── duplicate_detection.py    # full-row duplicate detection/exclusion
│       ├── invalid_value_detection.py # amount>=0, date-range, code-set checks
│       ├── quality_issue_log.py      # QualityIssueRecord read/write
│       └── router.py                 # extended: POST /data-engineering/clean, GET /data-engineering/quality-issues
└── tests/
    └── data_engineering/
        ├── test_cleaning_service.py
        ├── test_date_standardization.py
        ├── test_duplicate_detection.py
        └── test_invalid_value_detection.py

data/
├── cleaned/inpatient_cleaned.csv   # output of this feature
└── reports/quality_issues.json      # QualityIssueRecord[] audit trail
```

**Structure Decision**: Extends the same `data_engineering` module from Phase 1 rather than creating a new module — cleaning is part of the same domain (constitution Principle VI groups "data_engineering (profiling/cleaning/standardization)" as one module). New files, not a growing `profiling_service.py`.

## Complexity Tracking

*No constitution violations — this section intentionally left empty.*
