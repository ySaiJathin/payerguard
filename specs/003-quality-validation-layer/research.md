# Phase 0 Research: Quality Validation Layer

## Decision: Great Expectations as the suite/execution engine

**Decision**: Use the `great_expectations` Python library to define and run expectation suites, wrapping its results into this project's own `ExpectationCheckResult`/`QualityScoreResult` schemas rather than exposing GX's native result objects directly.

**Rationale**: The phase is explicitly named "Great Expectations quality layer" in MVP_CONTEXT.md Section 5, and GX provides battle-tested expectation primitives (completeness, uniqueness, value ranges, set membership) that would otherwise need to be hand-rolled. Wrapping its output in project-owned schemas keeps the composite-score formula (Section 3.1) fully under this project's control rather than coupled to GX's own scoring conventions.

**Alternatives considered**: Hand-rolled pandas-based checks (rejected — reinvents a well-established deterministic-validation library for no benefit, and the project's own naming already commits to GX); pandera (a lighter schema-validation alternative, rejected because it's schema/dtype-focused and weaker on the descriptive statistical checks like code-set membership and calibrated completeness this phase needs).

## Decision: Per-column completeness calibration via an exceptions table, not per-column bespoke code

**Decision**: Completeness expectations read a calibration table (column name → expected max missingness, defaulting to the Section 3.1 MissingRate bands unless overridden) seeded from MVP_CONTEXT.md Section 2.2's documented known-high-missingness columns (fully-null columns, `ADMTG_DGNS_CD` at 72.2%, `CLM_DRG_CD` at ~5.5%, `PRVDR_NUM` at ~4.4%, procedure-code slots with position-increasing missingness).

**Rationale**: FR-007 requires calibrated-not-universal completeness thresholds. A data-driven table (rather than per-column bespoke conditional code) keeps the logic uniform, auditable, and consistent with Principle II (the exceptions are documented, measured facts from Section 2.2, not arbitrary carve-outs).

**Alternatives considered**: A single universal missingness threshold applied everywhere (rejected — explicitly the failure mode FR-007/SC-003 rule out, would misclassify `ADMTG_DGNS_CD` and the fully-null columns as CRITICAL every run); per-column hardcoded if/else branches (rejected — harder to audit/extend than a data table, and risks embedding "magic" exceptions without a documented source).

## Decision: Freshness expectation scoped to ingestion recency, not claims-processing turnaround

**Decision**: The freshness check validates that a batch's ingestion timestamp (recorded by the ingestion step, not derived from `NCH_WKLY_PROC_DT`) falls within a configured expected window (e.g., "this batch was ingested within the last N days of the pipeline's expected cadence").

**Rationale**: MVP_CONTEXT.md Section 2.4 conclusively rules out `NCH_WKLY_PROC_DT` as a genuine operational-timestamp signal (it's a fixed weekly batch-cutoff date, always a Friday, carrying no claim-specific information). Reusing it for "freshness" would silently reintroduce the same fabrication problem the project already caught and corrected once for the SLA-breach label.

**Alternatives considered**: Deriving freshness from `NCH_WKLY_PROC_DT` (rejected — directly contradicted by Section 2.4's findings); skipping freshness entirely (rejected — Phase 3's task description explicitly lists freshness as one of the expectation categories; scoping it to ingestion recency satisfies the requirement without resurrecting a debunked field).

## Decision: Composite score formula implemented as an explicit, testable pure function

**Decision**: `scoring_service.py` implements the composite score as `score = Σ(category_weight × category_pass_proportion)` over all executed checks, with category weights read from configuration (default equal-weighted per Section 3.1's "weights per check category are configurable"), and the function takes the full `ExpectationCheckResult[]` list as its only input (no hidden state).

**Rationale**: This directly satisfies SC-001 (the score must be exactly recomputable from persisted check results) — a pure function of persisted inputs is trivially re-verifiable by re-calling it with the same results.

**Alternatives considered**: Computing the score inline during suite execution without persisting the intermediate results separately (rejected — would violate FR-011's requirement that individual results be independently persisted and queryable, and would make SC-001's recomputability claim unverifiable after the fact).
