# Phase 0 Research: Historical Baseline

## Decision: Date-based/batch-index window definition, not wall-clock windows

**Decision**: Processing windows are defined by claim date grouping (e.g., calendar day/week bucket of `CLM_FROM_DT`) or fixed-size sequential batches of N claims, not real-time wall-clock intervals (the "5/15/30-min" windows mentioned in MVP_CONTEXT.md Section 3's architecture diagram).

**Rationale**: This dataset has no live arrival timestamps — claims arrive as a static historical file, and the planned "continuous ingestion" was repeated batch upload, not a live stream (the continuous-ingestion phase was removed 2026-08-18) (constitution "Scope Discipline"). Wall-clock windows would be meaningless against a historical CSV; date-based or batch-index windows are the only semantically valid interpretation for this data shape.

**Alternatives considered**: Literal 5/15/30-minute wall-clock windows (rejected — no timestamp in the data supports this; would require fabricating arrival times, violating Principle II); a single "whole file = one window" (rejected — defeats the purpose of a volume-per-window baseline, which needs multiple windows to establish a distribution to deviate from).

## Decision: Baseline reads Phase 3's quality_results.json for missingness/duplicate rate rather than recomputing independently

**Decision**: `data_health_baseline.py` sources historical MissingRate and DuplicateRate from Phase 3's persisted `ExpectationCheckResult` entries (filtered to the historical batch) rather than re-running its own missingness/duplicate computation from scratch.

**Rationale**: FR-003 requires these figures be "sourced from or consistent with Phase 2/3's own measurements." Recomputing independently risks the two figures silently diverging if cleaning/dedup logic changes in Phase 2/3 but this baseline isn't updated in lockstep — reading the persisted result is the single-source-of-truth approach.

**Alternatives considered**: Independent recomputation directly from the cleaned file (rejected — duplicated logic, drift risk); recomputation with a cross-check assertion against Phase 3's numbers (considered viable but adds complexity without clear benefit over simply reading Phase 3's output — noted as a fallback if Phase 3's API/schema proves awkward to consume directly).

## Decision: Length-of-stay computed and stored independently from amount/volume baselines, with explicit exclusion tracking

**Decision**: `length_of_stay_baseline.py` computes `(NCH_BENE_DSCHRG_DT - CLM_ADMSN_DT).days` per claim, excludes claims with either date missing/unparseable, and separately reports the exclusion count as a named field (not folded silently into a smaller denominator elsewhere).

**Rationale**: MVP_CONTEXT.md Section 2.4 specifically calls out length-of-stay as the replacement duration signal after ruling out processing-time; the spec's FR-005/SC-004 require the exclusion to be visible, not silently absorbed, so anyone reading the baseline understands exactly how much of the data contributed to this specific statistic.

**Alternatives considered**: Imputing a default length-of-stay for missing dates (rejected — direct violation of Principle II); silently excluding without reporting the count (rejected — spec FR-005 explicitly requires the exclusion count as an output).

## Decision: BaselineSnapshot always carries source-data provenance

**Decision**: Every computed baseline is wrapped in a `BaselineSnapshot` envelope recording the exact source file/batch, row count, and date range it was computed from, rather than baseline statistics being returned as bare numbers.

**Rationale**: FR-007/SC-006 require this so that as more historical batches are loaded over time (the continuous-ingestion phase was removed 2026-08-18), a consumer of "the baseline" always knows which historical period it reflects — critical for Phase 21's future drift-monitoring work to compare like-for-like.

**Alternatives considered**: A single global mutable baseline with no versioning/provenance (rejected — would make it impossible to know what "historical" meant at the time a given downstream decision was made, undermining the audit trail principle that runs through the whole project).
