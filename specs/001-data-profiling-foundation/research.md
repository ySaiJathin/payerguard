# Phase 0 Research: Data Profiling Foundation

No [NEEDS CLARIFICATION] markers were left in the Technical Context — MVP_CONTEXT.md and the constitution already fix the language, storage, and structural decisions for this feature. The research below documents the choices made and why, per the plan workflow's requirement to record decisions even when they weren't open questions.

## Decision: pandas as the profiling engine

**Decision**: Use pandas (`read_csv(sep="|")`, `describe()`, `nunique()`, `isna()`, `value_counts()`) as the core computation layer for column and file-level statistics.

**Rationale**: pandas is already the implied stack for this project (Python backend, CSV-grain data, later feature engineering and model training all pandas-native). It handles mixed dtypes, percentile computation, and groupby-based claim aggregation (needed for lines-per-claim and claim-consistent sampling) without extra dependencies.

**Alternatives considered**: Polars (faster on large files, but the current file is 58,066 rows — well within pandas' comfortable range — and introducing a second dataframe library this early adds dependency-management cost with no measured benefit at this scale); raw `csv` module (would require hand-rolling percentile/statistics logic pandas already provides correctly).

## Decision: Column categorization as a static mapping, not inferred

**Decision**: Implement categorization as an explicit, version-controlled mapping (column name → category) seeded from MVP_CONTEXT.md Section 2.3, with a small set of pattern rules (e.g., `ICD_DGNS_CD\d+` → diagnosis/procedure code, `PRCDR_DT\d+` → date) for the repeated-pattern columns not individually named in Section 2.3.

**Rationale**: The spec (FR-007) requires the categorization to match Section 2.3 exactly for the columns it covers — an inferred/heuristic categorizer risks silently drifting from that ground truth. A static mapping plus documented pattern rules is auditable and testable (User Story 2, Acceptance Scenario 2).

**Alternatives considered**: dtype-based auto-inference (e.g., "numeric dtype → amount category") was rejected because it cannot distinguish an amount column from a utilization/duration column or an identifier stored as an integer (`CLM_ID` is numeric-looking but is an identifier, not an amount) — it would violate FR-007's exactness requirement.

## Decision: Sampling by claim (`CLM_ID`) with a fixed seed

**Decision**: Sample a configurable fraction (default 8%) of distinct `CLM_ID` values using a fixed random seed, then include every line-item row belonging to each selected claim. The default was tuned down from the originally-proposed ~10% during implementation (permitted by spec Assumptions): since claims average 2.82 line-items each, a 10%-of-claims sample has an *expected* row-reduction ratio of only ~10.0x, so ordinary sampling variance can land the actual ratio under SC-004's "at least 10x smaller" bar (observed on a real run: 9.87x). 8% builds in headroom (~12.5x expected).

**Rationale**: The dataset's grain is claim-line, not claim (mean 2.82 lines/claim, MVP_CONTEXT.md 2.2). Sampling individual rows would frequently split claims across included/excluded rows, breaking any downstream logic that aggregates by claim. Sampling by `CLM_ID` guarantees claim consistency (FR-009, SC-004) and a fixed seed guarantees reproducibility (FR-011, SC-005).

**Alternatives considered**: Row-level random sampling (rejected — breaks claim consistency); time-windowed sampling (rejected for this phase — continuous-ingestion windowing would have been the right place for time-based batching (the continuous-ingestion phase was removed 2026-08-18); this sample's only job is fast local iteration, not temporal representativeness).

## Decision: Report artifacts as Markdown + JSON pair

**Decision**: Persist the profiling report as both a human-readable Markdown narrative (`data/reports/profiling_report.md`) and a machine-readable JSON summary (`data/reports/profiling_report.json`), with column categorization emitted as its own JSON file (`data/reports/column_categories.json`) so later phases can load it programmatically without re-parsing the Markdown.

**Rationale**: Phase 1.1 explicitly calls for a "written report" (human-reviewable), while Phases 2–6 need the same information consumable by code (e.g., Phase 2's cleaning step needs to know which columns are dates to standardize, without re-deriving that from scratch). A dual-format artifact satisfies both without duplicating logic.

**Alternatives considered**: JSON-only (fails the "written report" readability intent); Markdown-only (would force every downstream phase to parse prose to get categorization, which is fragile).
