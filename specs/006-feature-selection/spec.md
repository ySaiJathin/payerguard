# Feature Specification: Feature Selection

**Feature Branch**: `006-feature-selection`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 6 — Feature selection (MVP_CONTEXT.md Section 5): Stage 1 (drop constant/near-constant/duplicate/raw-ID/high-missingness/leakage columns), Stage 2 (correlation, mutual information, variance, cardinality, missingness thresholds), Stage 3 (XGBoost importance, permutation importance, RFE if needed). Feature selection is fit on training/validation data only — never on test data."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Establish the shared temporal split feature selection is fit on (Priority: P1)

As the implementer of Phases 7 and 9 (anomaly and risk model benchmarks), I need a single, shared temporal 70/15/15 train/validation/test split established once and reused consistently, so feature selection, anomaly benchmarking, and risk benchmarking all evaluate against the same chronological boundaries instead of silently drifting apart.

**Why this priority**: Every subsequent claim in this feature ("fit on training/validation only") is meaningless without a concrete, shared split to point to — and constitution Principle VII (Temporal Integrity) requires this split be chronological, never random, across the whole pipeline.

**Independent Test**: Can be tested by computing the split once and confirming the training portion contains only chronologically earlier claims than validation, which in turn is chronologically earlier than test, with zero date overlap across the three portions.

**Acceptance Scenarios**:

1. **Given** the full cleaned/featured claim set spanning 2015-04-01 to 2022-10-31, **When** the temporal split is computed, **Then** the earliest 70% (by time) becomes train, the next 15% becomes validation, and the latest 15% becomes test — never a random shuffle.
2. **Given** the split, **When** any claim's split assignment is checked, **Then** it is deterministic and reproducible (the same claim always lands in the same split on repeated runs against unmodified data).
3. **Given** this split is computed once in this feature, **When** Phase 7 (anomaly) and Phase 9 (risk) run, **Then** they reuse this exact split rather than each computing an independent one.

---

### User Story 2 - Apply Stage 1 (structural) filtering (Priority: P1)

As the implementer, I need constant, near-constant, duplicate, raw-identifier, high-missingness, and leakage-risk columns dropped from the modeling feature set before any statistical or model-based selection runs, so obviously non-informative or unsafe columns don't waste later stages' effort or introduce leakage.

**Why this priority**: Structural filtering is cheap, deterministic, and removes the columns MVP_CONTEXT.md Section 2.2 has already identified as problematic (e.g., `NCH_CLM_TYPE_CD`, `CLM_FREQ_CD` constant columns; `OT_PHYSN_UPIN` fully-null) — doing this first makes every later stage more effective, so it's foundational alongside Story 1.

**Independent Test**: Can be tested by confirming that the specific columns MVP_CONTEXT.md Section 2.2 already flags (constant columns, fully-null columns) are dropped by Stage 1, without needing to run Stage 2/3 at all.

**Acceptance Scenarios**:

1. **Given** the documented constant columns (`NCH_CLM_TYPE_CD`, `CLM_FREQ_CD`, `CLAIM_QUERY_CODE`, `CLM_MDCR_NON_PMT_RSN_CD`, `PTNT_DSCHRG_STUS_CD`), **When** Stage 1 runs, **Then** all are dropped from the modeling feature set, with the drop reason recorded per column.
2. **Given** the documented fully-null columns (`OT_PHYSN_UPIN`, `FI_NUM`, etc.), **When** Stage 1 runs, **Then** all are dropped as high-missingness, with the drop reason recorded.
3. **Given** raw identifier columns (`CLM_ID`, `BENE_ID`, `PRVDR_NUM` as raw values, not their engineered features like provider-frequency), **When** Stage 1 runs, **Then** they are dropped from the modeling feature set (they remain available as row keys/joins, just not as model inputs) since raw high-cardinality identifiers are not informative model features and risk memorization.
4. **Given** a feature that would only exist because it directly encodes the future target (e.g., anything derived from post-hoc incident/investigation outcomes), **When** Stage 1 runs, **Then** it is dropped as a leakage risk, with the specific leakage reasoning recorded.

---

### User Story 3 - Apply Stage 2 (statistical) and Stage 3 (model-based) selection, fit on train+validation only (Priority: P2)

As the implementer of the anomaly and risk benchmarks, I need the remaining features further narrowed by correlation/mutual-information/variance/cardinality/missingness thresholds (Stage 2) and then by XGBoost/permutation importance or RFE (Stage 3), with every threshold and importance ranking fit exclusively on the train+validation portion of the Story 1 split, so the final feature set generalizes and the test set stays genuinely unseen.

**Why this priority**: This stage refines what Stage 1 leaves behind into the final modeling feature set — necessary for benchmark quality but strictly sequenced after Stories 1-2, hence P2.

**Independent Test**: Can be tested by confirming that no Stage 2/3 threshold, correlation figure, or importance ranking changes when the test-split portion of the data is altered (proving the selection process never touched it).

**Acceptance Scenarios**:

1. **Given** the Stage 1 output feature set, **When** Stage 2 runs, **Then** highly correlated redundant pairs, near-zero-variance features, and features failing configured missingness/cardinality thresholds are dropped, computed only from train+validation data.
2. **Given** the Stage 2 output, **When** Stage 3 runs, **Then** an XGBoost importance ranking (and permutation importance, and RFE if the feature count still warrants it) is computed on train+validation data only, and features below a documented importance threshold are dropped.
3. **Given** the final selected feature set, **When** it is compared against a version computed with a deliberately corrupted test-split portion of the input, **Then** the selected feature set and all Stage 2/3 statistics are identical — proving test-set isolation.

### Edge Cases

- What happens if Stage 1 would drop every feature in a column category (hypothetically)? The selection process MUST report this explicitly as a configuration/data issue rather than silently proceeding with zero features from that category.
- What happens when two features are perfectly correlated but both are otherwise informative? Stage 2 MUST document which one was kept and why (e.g., simpler/more interpretable, or the one with lower missingness) rather than an arbitrary unrecorded choice.
- What happens to `WindowFeatures.anomaly_count` (deferred/nullable per Phase 5) during selection — is a feature that's currently all-null incorrectly dropped as "high-missingness"? Feature selection MUST recognize the deferred/nullable field as a special case (excluded from Stage 1/2's missingness-based dropping logic, or explicitly deferred from selection consideration until Phase 7 populates it) rather than permanently discarding it for being 100% null today.
- What happens if Stage 3's XGBoost importance step itself needs a target label, but no label exists yet at this point in the build order (the risk label is Phase 8, after this phase)? Stage 3 MUST use a task-appropriate proxy suitable for unsupervised/pre-label feature ranking (e.g., importance against a provisional signal such as the Phase 3 quality-score or Phase 4 deviation magnitude) OR MUST be explicitly re-run once the Phase 8 label exists, and the specification of which applies MUST be recorded, not left ambiguous in the implementation.
- What happens if the temporal split (Story 1) produces a validation or test portion too small to compute stable statistics (e.g., very few claims in the tail)? The system MUST report the resulting sample sizes and flag if a portion is too small for reliable Stage 2/3 statistics, rather than silently producing unstable thresholds.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compute a single, shared temporal 70/15/15 train/validation/test split of the featured claim data, ordered strictly by claim date, with zero random shuffling, and MUST persist this split for reuse by Phase 7 and Phase 9.
- **FR-002**: System MUST make the temporal split deterministic and reproducible across repeated runs on unmodified data.
- **FR-003**: System MUST drop constant and near-constant columns (Stage 1), recording the specific reason and the columns affected.
- **FR-004**: System MUST drop columns identified as duplicates of other columns (Stage 1), raw high-cardinality identifier columns not intended as model inputs (Stage 1), and columns with missingness above a documented threshold not already handled by Phase 5's feature-level null semantics (Stage 1).
- **FR-005**: System MUST drop columns identified as leakage risks (features that would encode information not genuinely available at prediction time, e.g., post-hoc outcome-derived fields), recording the specific leakage reasoning per dropped column.
- **FR-006**: System MUST compute Stage 2 statistics (correlation, mutual information, variance, cardinality, missingness thresholds) exclusively on the train+validation portion of the Story 1 split, never touching the test portion.
- **FR-007**: System MUST compute Stage 3 model-based importance (XGBoost feature importance, permutation importance, and RFE if the post-Stage-2 feature count still warrants it) exclusively on the train+validation portion.
- **FR-008**: System MUST exclude the deferred/nullable `anomaly_count` window feature (per Phase 5) from missingness-based dropping logic in Stage 1/2, since its current all-null state is a known, temporary characteristic, not a genuine data-quality signal.
- **FR-009**: System MUST persist the final selected feature set, along with every drop decision (feature name, stage, specific reason) across all three stages, as an auditable record.
- **FR-010**: System MUST verify and be able to demonstrate that Stage 2/3 statistics and the final selected feature set are unaffected by the contents of the test-split portion (constitution Principle VII, no leakage).
- **FR-011**: System MUST NOT silently proceed if a column category would lose all its features — this condition MUST be reported explicitly.

### Key Entities

- **TemporalSplit**: The shared train/validation/test assignment per claim/window, with split boundaries (date ranges) and counts per portion.
- **FeatureDropDecision**: One record per dropped feature — feature name, stage (1/2/3), specific reason, and the statistic (if any) that triggered the drop.
- **SelectedFeatureSet**: The final list of features surviving all three stages, versioned and referencing the `TemporalSplit` and drop-decision records it was derived from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The `TemporalSplit` has zero date overlap between train/validation/test portions, and re-running split computation on unmodified data reproduces an identical assignment 100% of the time.
- **SC-002**: 100% of the columns MVP_CONTEXT.md Section 2.2 already identifies as constant or fully-null are present in Stage 1's drop list with the correct reason recorded.
- **SC-003**: Zero Stage 2/3 statistics or the final `SelectedFeatureSet` change when the test-split portion's data is deliberately corrupted in a test fixture — proving structural test-set isolation, not just documented intent.
- **SC-004**: Every dropped feature across all three stages has a `FeatureDropDecision` record with a specific, non-generic reason — zero features dropped without a recorded rationale.
- **SC-005**: `anomaly_count` is never present in any Stage 1/2 missingness-based drop list before Phase 7 exists (verified by a dedicated test), confirming FR-008's exemption holds.

## Assumptions

- The shared `TemporalSplit` established here (FR-001) is the same split Phase 7's anomaly benchmark and Phase 9's risk benchmark reuse — this feature is the natural place to establish it once, given it must exist before Stage 2/3 selection can run, and Section 3.2/Phase 9 both require the identical discipline (chronological, no shuffling).
- Stage 3's need for a target label ahead of Phase 8's official risk label is resolved by using a provisional, already-available signal (Phase 3's quality score and/or Phase 4's deviation-magnitude features) as the ranking target for this phase's feature-importance step; the plan should record explicitly that Stage 3's importance ranking is provisional and MAY be re-validated once Phase 8's real investigation-risk label exists, without treating that re-validation as this feature's own obligation.
- Exact numeric thresholds for Stage 1 (near-constant %, high-missingness %) and Stage 2 (correlation cutoff, variance cutoff) are configurable implementation parameters, not fixed by this spec; this spec fixes the requirement that they be documented and applied consistently, not their specific values.
