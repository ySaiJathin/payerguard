# Phase 1 Data Model: Historical Baseline

## VolumeBaseline

| Field | Type | Notes |
|---|---|---|
| `window_definition` | string | e.g., `"daily"`, `"weekly"`, `"1000-claim-batch"` |
| `windows` | array | `[{window_id, start, end, claim_count}]` — includes windows with `claim_count = 0` (spec FR-010) |

## AmountBaseline

| Field | Type | Notes |
|---|---|---|
| `column_name` | string | Every `amount`-category column |
| `mean` / `median` / `std` / `min` / `max` | float | |
| `percentiles` | object | `{p25, p50, p75, p95, p99}` |

## DataHealthBaseline

| Field | Type | Notes |
|---|---|---|
| `historical_missing_rate_by_column` | object | column → % missing, sourced from Phase 3 |
| `historical_duplicate_rate` | float | sourced from Phase 3 |
| `categorical_distributions` | object | field → `{value: count}`, at minimum `PTNT_DSCHRG_STUS_CD` |

## LengthOfStayBaseline

| Field | Type | Notes |
|---|---|---|
| `mean` / `median` | float | days |
| `percentiles` | object | `{p25, p50, p75, p95, p99}` |
| `claims_included` | integer | |
| `claims_excluded_missing_dates` | integer | Explicitly reported, never silently folded away (spec FR-005) |

## BaselineSnapshot

| Field | Type | Notes |
|---|---|---|
| `snapshot_id` | string | |
| `source_file` | string | e.g., `data/cleaned/inpatient_cleaned.csv` |
| `source_row_count` | integer | |
| `source_date_range` | object | `{min_date, max_date}` |
| `volume_baseline` | VolumeBaseline | |
| `amount_baselines` | AmountBaseline[] | |
| `data_health_baseline` | DataHealthBaseline | |
| `length_of_stay_baseline` | LengthOfStayBaseline | |
| `computed_at` | timestamp | |

**Validation rules**: No field anywhere in `BaselineSnapshot` or its sub-entities is named or semantically equivalent to "processing time," "SLA," or "turnaround" (spec FR-006, SC-005). Every numeric value is traceable to `source_file`/`source_row_count` — a test asserting output changes when the fixture changes enforces this (spec SC-002).

## Relationships

`BaselineSnapshot` is the sole aggregate root; all four baseline sub-entities are computed from, and scoped to, the same `source_file`/`source_row_count`/`source_date_range` — they are never mixed across snapshots from different source data.
