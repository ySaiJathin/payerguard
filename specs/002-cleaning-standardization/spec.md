# Feature Specification: Cleaning & Standardization

**Feature Branch**: `002-cleaning-standardization`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 2 — Cleaning & standardization (MVP_CONTEXT.md Section 5): schema validation → dtype conversion → missing-value handling → duplicate detection → invalid-value detection → date standardization (DD-Mon-YYYY → ISO). Preserve original_value / cleaned_value / quality_issue for every correction."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Produce a standardized, type-correct dataset (Priority: P1)

As the implementer of downstream phases (quality checks, baseline, features, models), I need `inpatient.csv` converted into a dataset where every column has the correct dtype for its category and every date is in ISO format, so that later phases can rely on consistent types instead of re-parsing raw strings.

**Why this priority**: Every phase from Phase 3 onward assumes typed, standardized data. Without this, Great Expectations rules, baseline statistics, and feature engineering would each have to re-implement ad hoc parsing, and inconsistently.

**Independent Test**: Can be tested by running cleaning against `data/raw/inpatient.csv` (or the Phase 1 sample) and asserting every date column contains only ISO-format (`YYYY-MM-DD`) values and every amount/utilization column is numeric.

**Acceptance Scenarios**:

1. **Given** the raw file with dates as `01-Apr-2015` strings, **When** cleaning runs, **Then** the cleaned output represents those dates in ISO 8601 (`2015-04-01`) format for `CLM_FROM_DT`, `CLM_THRU_DT`, `CLM_ADMSN_DT`, `NCH_BENE_DSCHRG_DT`, `NCH_WKLY_PROC_DT`, and every populated `PRCDR_DTn` column.
2. **Given** columns categorized as `amount` or `utilization_duration` in Phase 1's categorization output, **When** cleaning runs, **Then** those columns are numeric (float/int) in the cleaned output, not strings.
3. **Given** the cleaned output, **When** its column set and dtypes are checked against Phase 1's categorization, **Then** every column matches its expected category-implied dtype.

---

### User Story 2 - Preserve a full correction audit trail (Priority: P1)

As someone who must be able to justify every value the system reports (constitution Principle II — No Fabricated Values), I need every value that cleaning changes to be recorded with its original value, its cleaned value, and the specific quality issue that triggered the change, so nothing is silently altered or lost.

**Why this priority**: This is a non-negotiable project principle, not a nice-to-have — it's what makes the whole "evidence-first" narrative (MVP_CONTEXT.md Section 1) defensible. It ties for P1 with Story 1 because a cleaned dataset without this trail is not acceptable output for this project.

**Independent Test**: Can be tested by cleaning a fixture with known bad values (a malformed date, a stray whitespace-padded code) and confirming each shows up as a `(original_value, cleaned_value, quality_issue)` record, with the count of trail records matching exactly the count of cells that actually changed.

**Acceptance Scenarios**:

1. **Given** a date value that needed reformatting, **When** cleaning runs, **Then** an audit record exists with `original_value = "01-Apr-2015"`, `cleaned_value = "2015-04-01"`, `quality_issue = "date_format_standardized"`.
2. **Given** a cell whose value did not need any change, **When** cleaning runs, **Then** no audit record is created for that cell (the trail contains only actual corrections, not a copy of the whole dataset).
3. **Given** a missing value in any column, **When** cleaning runs, **Then** the cell remains null/missing in the cleaned output (never replaced with a fabricated or default value) and an audit record with `quality_issue = "missing_value"` is created referencing the row and column.

---

### User Story 3 - Detect duplicates and invalid values without silent deletion (Priority: P2)

As the implementer, I need duplicate rows and invalid values (e.g., negative amounts, out-of-range dates) detected and flagged so quality issues are visible, without the cleaning step silently deleting or guessing corrected values for them.

**Why this priority**: Detection and flagging matter for the quality score (Phase 3) and later investigation (Phase 8+), but this dataset's measured duplicate rate is currently 0% (MVP_CONTEXT.md Section 2.2) — so this is lower-frequency-triggered than Stories 1–2, hence P2.

**Independent Test**: Can be tested with a fixture file containing an injected exact-duplicate row and an injected negative `CLM_PMT_AMT`, confirming both are flagged with the correct `quality_issue` label and neither is silently dropped from the audit trail.

**Acceptance Scenarios**:

1. **Given** a fixture with one exact-duplicate row (identical values across all columns), **When** cleaning runs, **Then** the duplicate is flagged with `quality_issue = "duplicate_row"`, and the duplicate row is excluded from the deduplicated working dataset used by downstream phases while the original row remains recoverable via the audit trail (never physically deleted from any input file).
2. **Given** a fixture with a negative value in an amount column (which should never be negative), **When** cleaning runs, **Then** the cell is flagged with `quality_issue = "invalid_value_negative_amount"`, and the original value is preserved unchanged in the cleaned dataset (flagging, not guessing a correction).
3. **Given** the real `inpatient.csv` (measured 0 full-row duplicates per MVP_CONTEXT.md 2.2), **When** cleaning runs, **Then** the duplicate count in the output matches 0, confirming the detection logic doesn't produce false positives on real data.

### Edge Cases

- What happens when a date string doesn't match the expected `DD-Mon-YYYY` pattern at all (e.g., corrupted value)? It MUST be flagged with a distinct `quality_issue` (e.g., `"date_unparseable"`) and left as-is in `cleaned_value` (null-equivalent) rather than guessing a date.
- What happens when re-running cleaning on data that has already been cleaned (idempotency)? Running cleaning twice on the same unmodified raw input MUST produce identical cleaned output and an identical audit trail both times — no accumulating duplicate audit records.
- What happens to a categorical/code column value that doesn't belong to any known valid code set (e.g., an unrecognized `CLM_IP_ADMSN_TYPE_CD`)? It MUST be flagged (`quality_issue = "unrecognized_code"`) but not deleted or replaced.
- What happens when the input to this feature doesn't have the expected 197-column schema (i.e., Phase 1's schema validation failure case recurs here)? Cleaning MUST fail fast with a clear error rather than attempting to clean a malformed input.
- How does cleaning handle a column that's 100% missing (e.g., `OT_PHYSN_UPIN`)? Every cell is flagged `quality_issue = "missing_value"`, the column stays entirely null in the cleaned output — no fabricated default is introduced just because the whole column is empty.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate the input against the expected schema (197 columns matching Phase 1's column categorization) before cleaning, and MUST fail fast with a clear error if the schema doesn't match.
- **FR-002**: System MUST convert every column to the dtype implied by its Phase 1 category: `amount`/`utilization_duration` → numeric, `date` → parsed date, `identifier`/`categorical_code`/`diagnosis_procedure_code` → string.
- **FR-003**: System MUST standardize all populated date values from the observed `DD-Mon-YYYY` string format to ISO 8601 (`YYYY-MM-DD`).
- **FR-004**: System MUST detect full-row duplicates and flag them with a distinct quality-issue label, excluding them from the deduplicated working dataset without deleting the original row from any source file.
- **FR-005**: System MUST detect invalid values per documented, category-appropriate rules (amounts must be ≥ 0; dates must fall within a plausible claim-processing range; categorical/code values must belong to a known or observed code set) and flag them without altering the underlying value.
- **FR-006**: System MUST leave missing values as missing (null) in the cleaned output — cleaning MUST NOT fabricate, impute, or default a replacement value for a missing cell (constitution Principle II).
- **FR-007**: System MUST record, for every cell whose value actually changes during cleaning (e.g., date reformatting), an audit entry containing `original_value`, `cleaned_value`, and `quality_issue`, keyed to the specific row and column.
- **FR-008**: System MUST NOT create an audit entry for cells that required no change — the audit trail reflects only actual corrections/flags, not a full copy of the dataset.
- **FR-009**: Cleaning MUST be idempotent: running it twice on the same unmodified input produces byte-identical cleaned output and an identical audit trail, with no duplicate or accumulating audit entries across runs.
- **FR-010**: System MUST preserve claim-line grain in the cleaned output (one row per line item, matching the input grain) except for rows flagged and excluded as full-row duplicates per FR-004.
- **FR-011**: Validity rules used for invalid-value detection (amount ≥ 0, plausible date range, known code sets) MUST be documented and configurable, not embedded as unexplained magic numbers, and any rate/count reported about them MUST be computed from the actual data being cleaned.

### Key Entities

- **CleanedClaimLine**: One cleaned, type-converted, date-standardized output row, at the same claim-line grain as the input, with `duplicate_row` rows excluded from this dataset (but not deleted from the source).
- **QualityIssueRecord**: One audit-trail entry — `row_identifier` (e.g., `CLM_ID` + `CLM_LINE_NUM`), `column_name`, `original_value`, `cleaned_value`, `quality_issue` (one of: `date_format_standardized`, `missing_value`, `duplicate_row`, `invalid_value_negative_amount`, `unrecognized_code`, `date_unparseable`, or similar category-specific labels), `detected_at`.
- **SchemaValidationResult**: Pass/fail outcome of the pre-cleaning schema check, referencing Phase 1's column categorization as the expected schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of populated date-column values in the cleaned output are valid ISO 8601 dates; zero `DD-Mon-YYYY`-formatted strings remain.
- **SC-002**: The count of `QualityIssueRecord` entries with a value change exactly equals the count of cells whose `cleaned_value` differs from `original_value` — no missed corrections, no duplicate records.
- **SC-003**: Cleaning the full 58,066-row file completes in under 3 minutes on standard developer hardware.
- **SC-004**: Running cleaning twice on the same unmodified input produces byte-identical cleaned output and audit trail both times (idempotency).
- **SC-005**: Zero missing cells in the cleaned output contain a fabricated or defaulted value — every missing cell remains null and has a corresponding `missing_value` audit record.
- **SC-006**: On the real `inpatient.csv`, the detected duplicate-row count and invalid-value counts are fully explainable by inspecting the audit trail (no unexplained discrepancy between reported counts and trail contents).

## Assumptions

- "Excluding duplicates from the deduplicated working dataset" means downstream phases (baseline, features, quality scoring) consume the deduplicated dataset by default, while the full original file and the audit trail remain available for anyone who needs to see what was excluded and why — consistent with the "never silently delete bad records" scope statement (MVP_CONTEXT.md Section 4).
- The plausible date range for invalid-value detection is derived from the data's own observed range (01-Apr-2015 to 31-Oct-2022 per MVP_CONTEXT.md 2.2) with reasonable slack, not an arbitrarily chosen fixed range — exact tolerance is an implementation/tuning detail for `/speckit-plan`, not fixed here.
- "Known code set" for categorical/code columns is built from the set of values actually observed in the current data during Phase 1 profiling (there is no external CMS code-set reference file in scope for this MVP) — a value outside that observed set is flagged, not necessarily wrong, since CMS code sets are broader than what happens to appear in this one file; this label is advisory input to the quality score in Phase 3, not a hard rejection.
- This feature does not compute the 0–100 quality score itself (that's Phase 3, a separate feature) — it only produces the cleaned dataset and the flags/audit trail Phase 3 consumes.
