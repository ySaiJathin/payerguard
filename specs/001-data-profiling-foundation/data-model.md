# Phase 1 Data Model: Data Profiling Foundation

This feature is file-in/report-out; nothing here is persisted to PostgreSQL yet (the `claims` table and related DB models are populated starting with Phase 2/3). These are the in-memory/serialized entities the profiling capability produces.

## ColumnProfile

Represents the computed profile of one source column.

| Field | Type | Notes |
|---|---|---|
| `column_name` | string | Exact source column name from `inpatient.csv` header |
| `category` | enum | One of: `identifier`, `date`, `amount`, `utilization_duration`, `categorical_code`, `diagnosis_procedure_code` |
| `dtype_observed` | string | pandas dtype as read (e.g., `object`, `int64`, `float64`) |
| `missing_count` | integer | ≥ 0 |
| `missing_pct` | float | `missing_count / total_rows * 100`, computed — never hardcoded |
| `cardinality` | integer | Distinct non-null value count |
| `numeric_stats` | object \| null | Present only when `category` implies numeric content (`amount`, `utilization_duration`): `{mean, median, std, min, max, p25, p50, p75, p95, p99}` |
| `categorical_top_values` | array \| null | Present only for `categorical_code`/`diagnosis_procedure_code`/`identifier`: list of `{value, count}` for the most frequent values |
| `date_format_observed` | string \| null | Present only for `date` category, e.g., `DD-Mon-YYYY` |
| `date_min` / `date_max` | string \| null | Raw min/max date string observed, present only for `date` category |

**Validation rules**: `category` must be exactly one of the six fixed values (spec FR-007). `missing_pct` must be internally consistent with `missing_count` and the report's `total_rows`. Exactly one of `numeric_stats` / `categorical_top_values` / (`date_format_observed`+`date_min`+`date_max`) is populated, matching `category`.

## ProfilingReport

The aggregate output of a single profiling run.

| Field | Type | Notes |
|---|---|---|
| `source_file` | string | Path to the file profiled, e.g., `data/raw/inpatient.csv` |
| `generated_at` | timestamp | Run time of this report |
| `total_rows` | integer | File-level row count |
| `total_columns` | integer | Must equal 197 for the current `inpatient.csv` schema shape; validated at read time (FR-001) |
| `unique_claim_count` | integer | Distinct `CLM_ID` count |
| `unique_beneficiary_count` | integer | Distinct `BENE_ID` count |
| `lines_per_claim_mean` / `lines_per_claim_median` | float | Computed from grouping by `CLM_ID` |
| `duplicate_row_count` | integer | Full-row duplicate count |
| `columns` | ColumnProfile[] | One entry per source column, length must equal `total_columns` |

**Validation rules**: `len(columns) == total_columns` (SC-002). No field on this entity is ever a literal constant in code — all are computed at run time from `source_file` (constitution Principle II).

## SampleManifest

Describes a generated sample so later runs and reviewers know how it was produced.

| Field | Type | Notes |
|---|---|---|
| `output_file` | string | Path under `data/sampled/`, e.g., `data/sampled/inpatient_sample.csv` |
| `source_file` | string | Always `data/raw/inpatient.csv` |
| `seed` | integer | Random seed used for claim selection |
| `target_claim_fraction` | float | Configured sampling fraction (default ~0.10) |
| `claims_included` | integer | Actual count of distinct `CLM_ID` selected |
| `rows_included` | integer | Total line-item rows written to the sample |
| `generated_at` | timestamp | Run time of this sampling operation |

**Validation rules**: Every `CLM_ID` present in the output file has 100% of its line-item rows present (no partial claims — FR-009, SC-004). `claims_included` and `rows_included` are computed, not assumed. Re-running with the same `seed` and `target_claim_fraction` against an unchanged source file must reproduce an identical `claims_included` set (FR-011, SC-005).

## Relationships

`ProfilingReport` and `SampleManifest` are independent outputs of the same source file — a `SampleManifest` does not depend on a `ProfilingReport` having been generated first, and vice versa. Both reference `source_file` = `data/raw/inpatient.csv` for this MVP (single-dataset scope, constitution "Scope Discipline").
