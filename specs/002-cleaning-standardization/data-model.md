# Phase 1 Data Model: Cleaning & Standardization

## CleanedClaimLine

The cleaned, typed, standardized output row — same grain as the input (one row per claim line), minus rows flagged as full-row duplicates.

| Field | Type | Notes |
|---|---|---|
| *(all 197 source columns)* | typed per category | `amount`/`utilization_duration` → numeric; `date` → ISO 8601 string/date; `identifier`/`categorical_code`/`diagnosis_procedure_code` → string; missing cells remain null |
| `row_identifier` | string | Derived key for audit linkage, e.g., `f"{CLM_ID}:{CLM_LINE_NUM}"` |

**Validation rules**: Every date-typed cell, if non-null, is a valid ISO 8601 date (spec SC-001). Every amount/utilization cell, if non-null, matches the dtype implied by its category. No cell holds a value invented to fill a gap (spec FR-006).

## QualityIssueRecord

One audit-trail entry for an actual correction, flag, or missing-value observation.

| Field | Type | Notes |
|---|---|---|
| `row_identifier` | string | Matches `CleanedClaimLine.row_identifier` |
| `column_name` | string | Source column affected |
| `original_value` | string \| null | Raw value as read from source (null if the cell was empty) |
| `cleaned_value` | string \| null | Value after cleaning (null if left missing, or if invalid value was flagged-not-corrected) |
| `quality_issue` | enum | `date_format_standardized`, `missing_value`, `duplicate_row`, `invalid_value_negative_amount`, `unrecognized_code`, `date_unparseable`, or another category-specific label documented in the cleaning-rules config |
| `detected_at` | timestamp | Run time this record was produced |

**Validation rules**: A record exists if and only if `original_value != cleaned_value` OR the cell was missing OR the row/value was flagged invalid (spec FR-007/FR-008) — never one record per cell unconditionally. Re-running cleaning on unmodified input produces an identical set of records (spec SC-004).

## SchemaValidationResult

| Field | Type | Notes |
|---|---|---|
| `passed` | boolean | Whether the input matched the expected 197-column schema |
| `expected_column_count` | integer | 197, sourced from Phase 1's categorization output — not a literal constant duplicated in this feature's code |
| `actual_column_count` | integer | Computed from the input file at run time |
| `missing_columns` / `unexpected_columns` | string[] | Present only when `passed = false` |

## CleaningRunSummary

| Field | Type | Notes |
|---|---|---|
| `source_file` | string | Input file cleaned (raw or sampled) |
| `output_file` | string | `data/cleaned/inpatient_cleaned.csv` |
| `rows_in` / `rows_out` | integer | `rows_out = rows_in - duplicate_rows_excluded` |
| `duplicate_rows_excluded` | integer | Computed, not assumed |
| `quality_issue_count` | integer | Total `QualityIssueRecord` entries produced |
| `generated_at` | timestamp | Run time |

## Relationships

`CleaningRunSummary` is the run-level parent of many `QualityIssueRecord` entries (one run produces zero-to-many records) and exactly one `CleanedClaimLine` output set. `SchemaValidationResult` gates whether a `CleaningRunSummary` is produced at all — a failed validation aborts before any `CleanedClaimLine`/`QualityIssueRecord` is written (spec FR-001, Edge Cases).
