# Feature Specification: Historical Baseline

**Feature Branch**: `004-historical-baseline`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 4 — Historical baseline (MVP_CONTEXT.md Section 5): compute baseline statistics (claim volume per window, amount mean/median/std/percentiles, missingness rates, duplicate rate, status distribution) from the cleaned historical data — all real, computed values. No processing-time distribution (no genuine field exists per Section 2.4); length-of-stay (CLM_ADMSN_DT to NCH_BENE_DSCHRG_DT) tracked instead where a duration baseline is needed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Establish a computed baseline for volume and amounts (Priority: P1)

As the implementer of anomaly detection (Phase 7) and risk features (Phase 5/8), I need a historical baseline of claim volume per processing window and claim-amount distribution statistics, computed from the real cleaned historical data, so anomaly and deviation signals have something concrete to compare against instead of an assumed normal.

**Why this priority**: Every deviation-based signal downstream (volume deviation, amount deviation, feature engineering's "vs baseline" features) is meaningless without a real baseline to deviate from — this is the direct prerequisite for Phases 5, 7, and 8.

**Independent Test**: Can be tested by computing the baseline from Phase 2's cleaned output and confirming the amount statistics (mean, median, std, percentiles for `CLM_PMT_AMT`/`CLM_TOT_CHRG_AMT`) match the ground-truth values already measured in MVP_CONTEXT.md Section 2.2 when run against the same data.

**Acceptance Scenarios**:

1. **Given** the cleaned historical claims data, **When** the baseline is computed, **Then** it includes claim volume per defined processing window (e.g., per day or per N-claim batch), and amount mean/median/std/percentiles for every `amount`-category column.
2. **Given** the computed baseline, **When** its `CLM_PMT_AMT` statistics are compared to MVP_CONTEXT.md Section 2.2 (mean $13,638.31, median $1,481.72, std $35,993.91), **Then** they match when computed against the same underlying data (subject to any documented cleaning-driven adjustments from Phase 2, e.g., excluded duplicates).
3. **Given** the amount distribution is heavily right-skewed (per MVP_CONTEXT.md 2.2), **When** the baseline is used downstream, **Then** it exposes median/percentiles as first-class baseline values (not just mean), since the project's own data explicitly warns against mean-only baselining for this field.

---

### User Story 2 - Track data-health baseline (missingness, duplicates, status distribution) (Priority: P1)

As the implementer of the quality and anomaly layers, I need historical baseline rates for missingness, duplicates, and claim-status distribution, so a current batch's data-health metrics can be compared against what's normal for this dataset, not just against fixed absolute thresholds.

**Why this priority**: Complements Story 1 as the other half of "what does normal look like" — quality-check bands (Phase 3) are absolute thresholds, but detecting *drift* from this dataset's own historical norm needs a baseline, which is what Phase 22's monitoring ultimately builds on. Equal priority to Story 1 since both are direct prerequisites for later deviation-based signals.

**Independent Test**: Can be tested by confirming the baseline's duplicate rate and missingness-rate-per-column match what Phase 2/3 measured on the same historical batch, and that `PTNT_DSCHRG_STUS_CD`'s status distribution baseline reflects its documented near-constant nature (100% code `1` in the current extract, MVP_CONTEXT.md 2.2).

**Acceptance Scenarios**:

1. **Given** the cleaned historical data and Phase 3's quality results, **When** the baseline is computed, **Then** it records historical missingness rate per column and the historical duplicate rate, sourced from real computed values (not re-derived independently in a way that could drift from Phase 2/3's own numbers).
2. **Given** `PTNT_DSCHRG_STUS_CD`'s distribution, **When** the status-distribution baseline is computed, **Then** it reflects the actual observed distribution (currently ~100% code `1`) as a computed fact, not an assumed constant.
3. **Given** a future batch with a materially different status distribution, **When** compared against this baseline (by a downstream phase), **Then** the deviation is detectable because the baseline itself is a real, stored distribution to compare against — not a hardcoded expectation.

---

### User Story 3 - Track length-of-stay as the duration baseline (Priority: P2)

As the implementer, I need a length-of-stay baseline (`CLM_ADMSN_DT` → `NCH_BENE_DSCHRG_DT`) rather than a fabricated processing-time baseline, so duration-related deviation signals are grounded in a field that genuinely exists and means what it claims to mean.

**Why this priority**: This directly implements a specific correction already made in the project's documented reasoning (MVP_CONTEXT.md Section 2.4) — it's narrower in scope than Stories 1-2 (one derived field, not a whole statistics family), hence P2.

**Independent Test**: Can be tested by confirming the baseline includes length-of-stay distribution statistics (mean/median/percentiles) computed from `CLM_ADMSN_DT`/`NCH_BENE_DSCHRG_DT`, and that no "processing-time" or "SLA" baseline field is present anywhere in the output.

**Acceptance Scenarios**:

1. **Given** cleaned claims with valid `CLM_ADMSN_DT` and `NCH_BENE_DSCHRG_DT`, **When** the baseline is computed, **Then** length-of-stay (in days) distribution statistics (mean, median, percentiles) are included.
2. **Given** the full baseline output, **When** inspected for a processing-time or SLA-turnaround field, **Then** none exists — confirming MVP_CONTEXT.md Section 2.4's correction is respected end-to-end, not just documented.
3. **Given** a claim missing either admission or discharge date, **When** length-of-stay is computed, **Then** that claim is excluded from the length-of-stay baseline statistics (not assigned a fabricated duration) and the exclusion count is recorded.

### Edge Cases

- What happens when a processing window has zero claims (e.g., a genuinely quiet period in the historical data)? The baseline MUST record a real zero/window-count of zero rather than omitting the window or interpolating an assumed value.
- What happens when `CLM_ADMSN_DT` or `NCH_BENE_DSCHRG_DT` is missing or invalid for a claim? That claim MUST be excluded from length-of-stay statistics with the exclusion counted and reported, not defaulted to zero or the dataset mean.
- What happens if the baseline is computed from a small/sampled subset (Phase 1's sample) versus the full historical file? The baseline output MUST record which source it was computed from, so downstream consumers know whether they're comparing against a full-fidelity or sampled baseline.
- How does the baseline handle re-computation as more historical data becomes available (Phase 15 continuous ingestion)? The feature MUST support recomputing the baseline from an updated historical window without requiring code changes — the computation is data-driven, not tied to the specific 58,066-row snapshot.
- What happens to `amount` statistics if `CLM_TOT_CHRG_AMT` is identical to `CLM_PMT_AMT` in the current extract (as documented in MVP_CONTEXT.md 2.2)? Both are still computed and stored independently — the baseline does not assume they'll always be identical for future data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute claim volume per processing window from the cleaned historical data, using a documented, configurable window definition (e.g., daily or N-claim batches).
- **FR-002**: System MUST compute mean, median, std, min, max, and percentiles (at least 25th/50th/75th/95th/99th) for every `amount`-category column from the cleaned historical data.
- **FR-003**: System MUST compute historical missingness rate per column and the historical full-row duplicate rate, sourced from (or consistent with) Phase 2/3's own measurements rather than independently re-derived in a way that could diverge.
- **FR-004**: System MUST compute the historical distribution (value → frequency) for claim-status and other low-cardinality categorical fields relevant to downstream deviation checks (at minimum `PTNT_DSCHRG_STUS_CD`).
- **FR-005**: System MUST compute a length-of-stay (`NCH_BENE_DSCHRG_DT` − `CLM_ADMSN_DT`, in days) distribution baseline (mean, median, percentiles), excluding claims with missing or invalid admission/discharge dates and recording the exclusion count.
- **FR-006**: System MUST NOT compute, store, or expose any "processing-time" or "SLA-turnaround" baseline field derived from `NCH_WKLY_PROC_DT` or `FI_CLM_PROC_DT`, per MVP_CONTEXT.md Section 2.4.
- **FR-007**: System MUST record, alongside every baseline output, the source data it was computed from (file/batch identity, row count, date range) so consumers know what "historical" means for that specific baseline snapshot.
- **FR-008**: System MUST support recomputing the baseline against an updated/extended historical dataset without requiring code changes to accommodate new data volume.
- **FR-009**: System MUST NOT hardcode any baseline statistic — every value is computed at run time from the actual cleaned historical data supplied (constitution Principle II); values that happen to match MVP_CONTEXT.md Section 2.2's documented figures do so because they were computed from the same data, not because they were copied in as constants.
- **FR-010**: System MUST record a genuine zero (not omit or interpolate) for any processing window with no claims in the historical data.

### Key Entities

- **VolumeBaseline**: Claim count per processing window across the historical period, with the window definition used.
- **AmountBaseline**: Per-amount-column distribution statistics (mean/median/std/min/max/percentiles).
- **DataHealthBaseline**: Historical missingness rate per column, historical duplicate rate, and categorical/status-field distributions.
- **LengthOfStayBaseline**: Length-of-stay distribution statistics plus the count of claims excluded for missing/invalid dates.
- **BaselineSnapshot**: The aggregate container tying together Volume/Amount/DataHealth/LengthOfStay baselines with source-data provenance (file identity, row count, date range, computed-at timestamp).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `AmountBaseline` statistics computed from the full cleaned historical file match MVP_CONTEXT.md Section 2.2's documented `CLM_PMT_AMT` figures (mean $13,638.31, median $1,481.72, std $35,993.91) within a tolerance attributable only to Phase 2 cleaning adjustments (e.g., excluded duplicates), not to computation error.
- **SC-002**: Zero baseline statistics in the output are literal hardcoded constants — every value changes correctly when the feature is re-run against a modified/extended historical dataset (verified by a test that mutates a fixture and confirms the baseline output changes accordingly).
- **SC-003**: 100% of processing windows in the historical period appear in `VolumeBaseline`, including any windows with zero claims.
- **SC-004**: `LengthOfStayBaseline` excludes 100% of claims with missing/invalid admission or discharge dates from its statistics while still reporting the exclusion count as a first-class output field.
- **SC-005**: No field named or semantically equivalent to "processing time," "SLA," or "turnaround" appears anywhere in this feature's output schema.
- **SC-006**: Every `BaselineSnapshot` records its source data's identity (file/batch, row count, date range), enabling any consumer to know exactly what historical period a given baseline represents.

## Assumptions

- The processing-window definition (e.g., daily windows vs. N-claim batches) is a configurable parameter; this spec requires *a* documented, consistent window definition to exist, not a specific window size — exact default is an implementation choice for `/speckit-plan`, consistent with MVP_CONTEXT.md Section 3's "5/15/30-min or N-claim batches" phrasing (adapted here to claims data with no real-time arrival timestamps, so window semantics are batch-index/date-based rather than wall-clock-based).
- This feature computes and stores the baseline; it does not itself compare a *new* batch against the baseline (that comparison/deviation-scoring responsibility belongs to Phase 5's window-level features and Phase 7's anomaly detection, which consume this baseline as an input).
- "Historical data" for the initial baseline computation is the full Phase 2 cleaned output of `inpatient.csv` (2015-04-01 to 2022-10-31); as Phase 15 continuous ingestion adds new batches, recomputing/extending the baseline is explicitly supported (FR-008) but the policy for *when* to recompute (every batch vs. periodic) is left to implementation, not fixed here.
