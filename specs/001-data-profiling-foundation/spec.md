# Feature Specification: Data Profiling Foundation

**Feature Branch**: `001-data-profiling-foundation`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 1 — Data engineering foundation (MVP_CONTEXT.md Section 5): full data profiling of inpatient.csv (row/col counts, dtypes, missingness, cardinality, duplicates, numeric/categorical distributions, date columns) producing a written report; column categorization (identifiers / dates / numerical / categorical / diagnosis-procedure codes) confirmed against the real columns; sampling strategy for fast local iteration (raw file stays intact under data/raw/, working sample generated under data/sampled/)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate the full data profiling report (Priority: P1)

As the implementer building the PayerGuard pipeline, I need a complete, computed profile of `inpatient.csv` — row/column counts, dtypes, missingness, cardinality, duplicates, and distribution statistics for every column — before writing any cleaning, quality, or modeling logic, so that every downstream design decision is based on the data's real shape instead of assumption.

**Why this priority**: Every later phase (cleaning, quality rules, baselines, features, models) depends on knowing what's actually in this file. Without this, later phases risk being built against imagined columns or wrong assumptions about missingness/dtypes.

**Independent Test**: Can be fully tested by running profiling against `data/raw/inpatient.csv` and confirming the report's file-level statistics (row count, unique claim count, unique beneficiary count) match the ground-truth values already measured in MVP_CONTEXT.md Section 2.2.

**Acceptance Scenarios**:

1. **Given** `inpatient.csv` present at `data/raw/inpatient.csv` (pipe-delimited), **When** profiling is run, **Then** a written report is produced covering all 197 columns with, per column: dtype, missing count and percentage, distinct-value count (cardinality), and — for numeric columns — mean/median/std/min/max/percentiles, or — for categorical columns — top value frequencies.
2. **Given** the generated report, **When** its file-level statistics are compared to MVP_CONTEXT.md Section 2.2, **Then** row count (58,066), unique `CLM_ID` count (20,867), unique `BENE_ID` count (5,699), and full-duplicate-row count (0) match exactly.
3. **Given** date-bearing columns (`CLM_FROM_DT`, `CLM_THRU_DT`, `CLM_ADMSN_DT`, `NCH_BENE_DSCHRG_DT`, the 25 paired `PRCDR_DTn` columns), **When** profiling inspects them, **Then** the report records each one's observed string format (`DD-Mon-YYYY`) and min/max date found, without attempting to parse or standardize the values (standardization is Phase 2's job).

---

### User Story 2 - Confirm column categorization (Priority: P2)

As the implementer, I need every one of the 197 columns assigned to exactly one category (identifier, date, amount/numerical, utilization/duration, categorical/code, or diagnosis/procedure code) so that Phases 2–6 can apply category-appropriate logic (e.g., dtype coercion for numerics, code-set validation for diagnosis codes) without re-deriving column meaning from scratch each time.

**Why this priority**: Categorization is what turns a raw profiling report into something the rest of the pipeline can programmatically consume. It is a direct, low-risk consequence of Story 1's output, which is why it ranks just below the profiling report itself.

**Independent Test**: Can be tested independently by checking that every column named in MVP_CONTEXT.md Section 2.3 receives the same category in the categorization output, and that every column NOT named there (the remainder of the 197) still receives exactly one category.

**Acceptance Scenarios**:

1. **Given** the profiling report, **When** categorization runs, **Then** every one of the 197 columns is assigned exactly one category from the fixed set {identifier, date, amount, utilization/duration, categorical/code, diagnosis/procedure code}.
2. **Given** a column explicitly categorized in MVP_CONTEXT.md Section 2.3 (e.g., `CLM_ID` → identifier, `CLM_PMT_AMT` → amount, `PRNCPAL_DGNS_CD` → diagnosis code), **When** categorization runs, **Then** the assigned category matches the documented one.
3. **Given** a fully-null column (e.g., `OT_PHYSN_UPIN`, `FI_NUM`), **When** categorization runs, **Then** the column is still assigned a category (based on its name/schema role) rather than being silently skipped — removal decisions belong to Feature Selection (Phase 6), not to profiling/categorization.

---

### User Story 3 - Produce a fast-iteration working sample (Priority: P3)

As the implementer, I need a smaller, claim-consistent sample of `inpatient.csv` so I can iterate on pipeline code locally without re-processing all 58,066 rows on every run, while the original file stays untouched as the source of truth.

**Why this priority**: This is a developer-productivity convenience, not something later phases have a hard functional dependency on (they can always run against the raw file) — hence P3.

**Independent Test**: Can be tested independently by generating the sample and verifying (a) `data/raw/inpatient.csv` is byte-identical before and after, and (b) every `CLM_ID` present in the sample has all of its line-item rows included (no claim is split across included/excluded rows).

**Acceptance Scenarios**:

1. **Given** `inpatient.csv` in `data/raw/`, **When** the sampling step runs, **Then** a new file is written under `data/sampled/` and the original file under `data/raw/` is not modified, moved, or deleted.
2. **Given** the sample is generated by selecting a subset of claims, **When** the sample is inspected, **Then** every included `CLM_ID`'s line items are all present (grouping by claim is preserved) and no partial claims exist.
3. **Given** the sample is regenerated on a later run, **When** compared to the prior sample, **Then** the sampling is reproducible (same seed/parameters yield the same claim subset) so debugging results stay comparable across runs.

### Edge Cases

- What happens when a column is 100% missing (e.g., `OT_PHYSN_UPIN`, `FI_CLM_PROC_DT`)? Profiling still reports it (missing % = 100, cardinality = 0) rather than erroring or omitting the column.
- What happens if the file is accidentally read as comma-delimited instead of pipe-delimited? Profiling MUST detect the resulting column-count mismatch (expected 197) and fail fast with a clear error rather than silently producing a garbled report.
- What happens when `inpatient.csv` is missing from `data/raw/` entirely? Profiling MUST fail with a clear, actionable error rather than a stack trace or a silently empty report.
- How does the sampling strategy behave if the configured sample fraction would select zero claims (e.g., misconfigured to 0%)? It MUST refuse to produce an empty/degenerate sample and report the configuration error.
- What happens on re-running profiling after the underlying `inpatient.csv` changes (e.g., a corrected file is dropped in)? The report MUST be regenerated fresh from the current file's contents, not merged with or appended to a stale prior report.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read `data/raw/inpatient.csv` using the pipe delimiter (`|`), never comma, and MUST verify the resulting column count is 197 before proceeding.
- **FR-002**: System MUST compute, for every column, the dtype observed, the missing-value count and percentage, and the distinct-value count (cardinality).
- **FR-003**: System MUST compute distribution statistics (mean, median, std, min, max, and at least the 25th/50th/75th/95th/99th percentiles) for every numeric column.
- **FR-004**: System MUST compute frequency counts (value → count, at minimum the top values) for every categorical/code column.
- **FR-005**: System MUST detect and report all date-formatted columns, including their observed string format and the min/max date value present, without transforming the values.
- **FR-006**: System MUST compute file-level statistics: total row count, unique `CLM_ID` count, unique `BENE_ID` count, mean/median lines-per-claim, and full-duplicate-row count.
- **FR-007**: System MUST assign every one of the 197 columns to exactly one category from {identifier, date, amount, utilization/duration, categorical/code, diagnosis/procedure code}, using the categorization already confirmed in MVP_CONTEXT.md Section 2.3 as the source of truth for the columns it covers.
- **FR-008**: System MUST persist the profiling report and categorization output as durable, reviewable artifacts (not just console/log output) that later phases and human reviewers can reference.
- **FR-009**: System MUST generate a sampled dataset under `data/sampled/` by selecting whole claims (all line items for a selected `CLM_ID`) so no claim is split across included/excluded rows.
- **FR-010**: System MUST leave `data/raw/inpatient.csv` unmodified — sampling and profiling are read-only with respect to the source file.
- **FR-011**: Sampling MUST be reproducible: the same configuration (seed, target size/fraction) run twice MUST produce the same sampled claim set.
- **FR-012**: System MUST NOT hardcode any statistic that this feature reports (row counts, missingness, cardinality, etc.) — every reported number is computed from the current contents of `inpatient.csv` at run time, per the project's no-fabrication principle (constitution Principle II).
- **FR-013**: System MUST fail fast with a clear, actionable error when the source file is missing, unreadable, or does not have the expected column count, rather than producing a partial or misleading report.

### Key Entities

- **Column Profile**: Per-source-column metadata — column name, assigned category, observed dtype, missing count/percentage, cardinality, and (for numeric columns) distribution statistics or (for categorical columns) value-frequency counts.
- **Data Profiling Report**: The aggregate output artifact combining file-level statistics (row/claim/beneficiary counts, duplicate count) with the full set of Column Profiles for all 197 columns.
- **Sampled Dataset**: A reduced, claim-consistent subset of `inpatient.csv`, written to `data/sampled/`, generated deterministically from a documented seed/configuration and never overwriting the raw source file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The profiling report is generated from the full 58,066-row file in under 2 minutes on standard developer hardware.
- **SC-002**: 100% of the file's 197 columns appear in the profiling report with a dtype, missingness figure, cardinality figure, and exactly one assigned category.
- **SC-003**: The report's file-level counts (total rows, unique claims, unique beneficiaries, duplicate rows) match the ground-truth figures in MVP_CONTEXT.md Section 2.2 exactly, with zero discrepancy.
- **SC-004**: The generated sample is at least 10x smaller than the raw file (by row count) while every included claim's line items are 100% present (zero split claims).
- **SC-005**: Re-running profiling and sampling twice on the same unchanged `inpatient.csv` with the same configuration produces identical report statistics and an identical sampled claim set, both times.

## Assumptions

- The profiling report is written in a durable, human-and-machine-readable format (e.g., Markdown for narrative review plus a machine-readable JSON/CSV summary) rather than console-only output, consistent with Phase 1.1's "written report" requirement — the exact file format is an implementation choice for `/speckit-plan`, not fixed here.
- Column categories not explicitly enumerated in MVP_CONTEXT.md Section 2.3 (columns outside the ones already called out, e.g., additional `ICD_DGNS_CDn`/`ICD_PRCDR_CDn` slots or `CLM_PPS_CPTL_*` amount components) are categorized by applying the same category definitions used for the columns that are already confirmed (e.g., all `ICD_DGNS_CDn` are diagnosis/procedure codes, all `CLM_PPS_CPTL_*` are amounts).
- Default sample target is roughly 10% of unique claims (a configurable parameter), sampled by `CLM_ID` with a fixed random seed for reproducibility; the exact default fraction can be tuned during implementation without changing this spec's intent (fast local iteration, claim-consistent, reproducible).
- This feature covers profiling, categorization, and sampling only — it does not clean, standardize, or validate the data (that is Phase 2 / Phase 3, tracked as separate features).
