# Phase 1 Data Model: Quality Validation Layer

## ExpectationSuite

| Field | Type | Notes |
|---|---|---|
| `category` | enum | One of the six Phase 1 categories |
| `suite_name` | string | e.g., `amount_suite`, `date_suite` |
| `expectation_types` | string[] | Which of completeness/uniqueness/validity/dtype/range/code-set/freshness apply to this category |

## ExpectationCheckResult

| Field | Type | Notes |
|---|---|---|
| `check_id` | string | Unique per (suite, column, expectation_type, run) |
| `suite_name` | string | Parent suite |
| `column_name` | string \| null | Null for file-level checks (e.g., DuplicateRate) |
| `expectation_type` | enum | `completeness`, `uniqueness`, `validity`, `dtype`, `range`, `code_set`, `freshness` |
| `computed_rate_or_count` | float | The underlying measured value (e.g., MissingRate %, distinct-value count) |
| `band` | enum | `PASS`, `WARNING`, `CRITICAL` |
| `threshold_used` | object | The bound(s) applied, e.g., `{missing_rate_pct: {pass_lt: 2, warning_lt: 5}}` or the calibrated override for this column |
| `run_id` | string | Links back to the `QualityScoreResult` this contributed to |
| `evaluated_at` | timestamp | |

**Validation rules**: `band` is derived strictly from `computed_rate_or_count` and `threshold_used` — never assigned independently (spec FR-013). For calibrated-completeness columns, `threshold_used` records the calibration override actually applied, not the universal default, so the exception is auditable (spec FR-007).

## QualityScoreResult

| Field | Type | Notes |
|---|---|---|
| `run_id` | string | |
| `batch_source` | string | e.g., `data/cleaned/inpatient_cleaned.csv` |
| `composite_score` | float | 0-100, clamped |
| `weights_used` | object | Category → weight mapping applied for this run |
| `contributing_check_ids` | string[] | Every `ExpectationCheckResult.check_id` folded into this score — enables exact recomputation (spec SC-001) |
| `generated_at` | timestamp | |

**Validation rules**: `composite_score` MUST equal `weighted_proportion(contributing_check_ids' bands, weights_used)` — verified by a dedicated recomputation test (spec SC-001). `composite_score` is clamped to [0, 100]; any weight configuration that would push it outside that range surfaces a configuration error instead (spec Edge Cases).

## CompletenessCalibrationEntry

| Field | Type | Notes |
|---|---|---|
| `column_name` | string | |
| `expected_max_missing_pct` | float | Overrides the universal MissingRate band for this specific column |
| `source_note` | string | e.g., `"MVP_CONTEXT.md 2.2: 72.2% missing, principal diagnosis is the reliable field instead"` |

**Validation rules**: Every entry's `source_note` must reference a documented, measured fact (Principle II) — this table is not a place for arbitrary unexplained overrides.

## Relationships

`QualityScoreResult` aggregates many `ExpectationCheckResult` (via `contributing_check_ids`), each of which is produced by exactly one `ExpectationSuite`'s execution against one batch. `CompletenessCalibrationEntry` is consulted by the `completeness` expectation type at check-execution time and referenced in the resulting `ExpectationCheckResult.threshold_used`.
