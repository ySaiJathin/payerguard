# Feature Specification: Feature Engineering

**Feature Branch**: `005-feature-engineering`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 5 — Feature engineering (MVP_CONTEXT.md Section 5): claim-level features (amount ratios, length-of-stay, date-derived features, encoded categoricals, provider frequency) and window-level features (claim count, amount stats, missingness %, duplicate %, invalid-status %, volume/amount deviation vs baseline, anomaly count per window)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute claim-level features (Priority: P1)

As the implementer of anomaly detection (Phase 7) and risk modeling (Phase 9), I need each claim enriched with derived features (amount ratios, length-of-stay, date-derived attributes, encoded categoricals, provider frequency) computed from the cleaned data, so models have informative, real-valued signals to learn from instead of raw categorical/date strings.

**Why this priority**: Claim-level features are the direct input to both benchmark tracks (anomaly and risk); nothing in Phases 7-9 can proceed meaningfully without them.

**Independent Test**: Can be tested by running feature engineering against Phase 2's cleaned output and confirming every claim receives the full documented feature set with no missing feature columns and no fabricated values for claims lacking the underlying source data.

**Acceptance Scenarios**:

1. **Given** a cleaned claim with `CLM_PMT_AMT` and `CLM_TOT_CHRG_AMT` populated, **When** claim-level features are computed, **Then** an amount-ratio feature (e.g., payment-to-charge ratio) is produced from the real values.
2. **Given** a cleaned claim with valid `CLM_ADMSN_DT` and `NCH_BENE_DSCHRG_DT`, **When** claim-level features are computed, **Then** a length-of-stay feature is produced, consistent with Phase 4's length-of-stay definition (same field derivation, not a second divergent formula).
3. **Given** a cleaned claim's date fields, **When** date-derived features are computed, **Then** attributes like day-of-week, month, and year are extracted from the standardized ISO dates.
4. **Given** categorical/code columns, **When** categorical encoding is applied, **Then** every categorical feature used downstream is a numeric-encoded representation, with the encoding scheme documented and consistently applied.
5. **Given** `PRVDR_NUM`, **When** provider-frequency is computed, **Then** each claim's feature reflects how often that provider appears in the historical data (a real computed frequency, not an assumed value).
6. **Given** a claim missing an input needed for a specific feature (e.g., missing discharge date for length-of-stay), **When** that feature is computed, **Then** the feature value is left null/missing for that claim (not fabricated), consistent with Phase 2/4's no-fabrication handling of missing data.

---

### User Story 2 - Compute window-level features from currently-available signals (Priority: P1)

As the implementer of anomaly detection (Phase 7), I need window-level aggregate features (claim count, amount stats, missingness %, duplicate %, invalid-status %, volume/amount deviation vs. the Phase 4 baseline) computed per processing window, using only signals that already exist by this point in the pipeline, so windows can be compared against historical norms.

**Why this priority**: Equal priority to Story 1 — window-level features are the other half of the feature set anomaly detection needs, and they depend directly on Phase 4's baseline being available.

**Independent Test**: Can be tested by computing window-level features for the historical data and confirming volume/amount deviation values are computed relative to Phase 4's `BaselineSnapshot`, not an independently re-derived or assumed baseline.

**Acceptance Scenarios**:

1. **Given** the Phase 4 baseline and a window's actual claim count, **When** volume deviation is computed, **Then** it reflects the real difference (absolute or relative) between this window's count and the baseline's expected count for a comparable window.
2. **Given** a window's cleaned claims, **When** missingness %, duplicate %, and invalid-status % are computed for that window, **Then** they are sourced from (or consistent with) Phase 2/3's per-batch measurements, scoped to that specific window rather than the whole historical file.
3. **Given** the full set of processing windows, **When** window-level features are computed, **Then** every window (including zero-claim windows, consistent with Phase 4's `VolumeBaseline`) receives a complete feature row.

---

### User Story 3 - Reserve the window-level schema for anomaly count, populated once Phase 7 exists (Priority: P3)

As the implementer, I need the window-level feature schema to include an `anomaly_count` field from the start, populated as null/unset until Phase 7's anomaly detection produces real scores, so the schema doesn't need to change shape later and downstream consumers can rely on a stable feature contract.

**Why this priority**: This is a forward-compatibility/schema-stability concern rather than something with independent business value today, hence P3 — but it matters because Phase 8's risk dataset construction expects a stable window-feature shape to build on.

**Independent Test**: Can be tested by confirming the window-level feature schema includes `anomaly_count` (nullable) immediately after this feature ships, before Phase 7 exists, and that no downstream consumer errors on its null value.

**Acceptance Scenarios**:

1. **Given** this feature is implemented before Phase 7 exists, **When** window-level features are computed, **Then** every window's `anomaly_count` field is present but null, clearly distinguished from a real computed zero.
2. **Given** Phase 7 later populates real anomaly scores, **When** an enrichment step (owned by Phase 7 or Phase 8, not this feature) updates `anomaly_count`, **Then** it does so without requiring a schema migration on this feature's output — the field already existed as a defined, nullable slot.

### Edge Cases

- What happens when a categorical column has a value in a current batch that wasn't observed during encoding-scheme fitting (e.g., a new `CLM_DRG_CD` not seen in historical data)? The encoding MUST handle unseen categories explicitly (e.g., a documented "unknown" bucket) rather than erroring or silently producing a zero/default that looks like a real category.
- What happens to amount-ratio features when the denominator is zero or missing (e.g., `CLM_TOT_CHRG_AMT` is 0 or null)? The ratio feature MUST be null for that claim, not a divide-by-zero error or a fabricated large/default number.
- What happens when a window-level feature depends on a baseline window type that doesn't exist yet (e.g., the current window definition changed since the baseline was computed)? The system MUST detect the mismatch and report it rather than silently computing a deviation against an incompatible baseline.
- How does provider frequency behave for a provider appearing only in a very recent batch, not in the historical baseline used to compute frequency? The feature MUST reflect the actual computed frequency from whatever historical scope is configured (even if that count is low/1), not error or default to zero when the provider is legitimately rare.
- What happens to `anomaly_count` for windows computed before Phase 7 ships versus after? Any window-level feature row MUST make it unambiguous whether `anomaly_count` is "not yet available" (null) versus "computed as zero anomalies" (real zero) — these are never conflated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute claim-level amount-ratio features (e.g., payment-to-charge ratio) from real `amount`-category column values, producing a null result when the required inputs are missing or the denominator is zero — never a fabricated or divide-by-zero-masking value.
- **FR-002**: System MUST compute a claim-level length-of-stay feature using the same `CLM_ADMSN_DT`→`NCH_BENE_DSCHRG_DT` derivation established in Phase 4, excluding claims with missing/invalid dates from that feature (null, not fabricated).
- **FR-003**: System MUST compute date-derived claim-level features (at minimum day-of-week, month, year) from the standardized ISO dates produced by Phase 2.
- **FR-004**: System MUST encode categorical/code columns used as model inputs into a documented, consistently-applied numeric representation, with an explicit, non-fabricating handling path for categories not seen during encoding-scheme fitting.
- **FR-005**: System MUST compute a claim-level provider-frequency feature reflecting how often `PRVDR_NUM` appears in the configured historical scope, computed from real data.
- **FR-006**: System MUST compute window-level claim count, amount statistics, missingness %, duplicate %, and invalid-status % per processing window, using the same window definition established in Phase 4.
- **FR-007**: System MUST compute window-level volume deviation and amount deviation relative to Phase 4's `BaselineSnapshot`, and MUST detect and report a window-definition mismatch rather than silently computing against an incompatible baseline.
- **FR-008**: System MUST include an `anomaly_count` field in the window-level feature schema from initial implementation, populated as null (explicitly distinguished from a real computed zero) until a later enrichment step populates it from Phase 7's output.
- **FR-009**: System MUST produce a complete feature row for every window defined in the current run, including windows with zero claims (consistent with Phase 4's `VolumeBaseline` handling of empty windows).
- **FR-010**: System MUST NOT fabricate any feature value for missing/unavailable underlying data — every feature is either a real computed value or explicitly null, per constitution Principle II.

### Key Entities

- **ClaimFeatures**: Per-claim feature vector — amount ratios, length-of-stay, date-derived attributes, encoded categoricals, provider frequency — keyed to the claim identifier.
- **WindowFeatures**: Per-window feature vector — claim count, amount stats, missingness %, duplicate %, invalid-status %, volume deviation, amount deviation, and the deferred/nullable `anomaly_count`.
- **EncodingScheme**: The documented, versioned mapping used to encode each categorical/code column, including its "unseen category" handling rule.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of cleaned claims receive a complete `ClaimFeatures` row, with every feature either a real computed value or an explicit null (zero fabricated values, verified by a test that injects a claim with missing inputs and checks the resulting nulls).
- **SC-002**: 100% of processing windows (including zero-claim windows) receive a complete `WindowFeatures` row.
- **SC-003**: Every `WindowFeatures.volume_deviation` and `.amount_deviation` value is verifiably computed from Phase 4's `BaselineSnapshot` (recomputable by re-applying the deviation formula to the baseline and the window's own claim data).
- **SC-004**: `anomaly_count` is present in 100% of `WindowFeatures` rows and is null (not zero) in every row produced before Phase 7 exists — verified by a schema/contract test.
- **SC-005**: Categorical encoding correctly handles at least one injected "unseen category" test case without error and without silently mapping it to an existing legitimate category's code.

## Assumptions

- The specific encoding scheme (one-hot vs. frequency/target encoding) per categorical column is an implementation choice for `/speckit-plan`, guided by cardinality (e.g., low-cardinality columns like `CLM_IP_ADMSN_TYPE_CD` are natural one-hot candidates; high-cardinality columns like `CLM_DRG_CD`'s 167 values or diagnosis/procedure codes are natural frequency/target-encoding candidates) — this spec fixes the requirement (documented, consistent, handles unseen categories) not the specific algorithm.
- Per the clarification resolved for this feature: `anomaly_count` is a deferred/nullable column in the `WindowFeatures` schema from this feature's initial implementation, populated by a later enrichment step once Phase 7 (anomaly detection benchmark) produces real scores — this feature's own scope and tests cover only the features computable at this point in the build order.
- This feature does not perform feature *selection* (dropping constant/redundant/leakage-risk columns) — that is Phase 6, a separate feature that consumes this feature's full output.
