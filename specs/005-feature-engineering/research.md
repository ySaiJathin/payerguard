# Phase 0 Research: Feature Engineering

## Decision: `anomaly_count` is a deferred/nullable field, populated by a later enrichment step

**Decision**: `WindowFeatures.anomaly_count` exists in the schema from this feature's first implementation, defaults to `null`, and is populated by a small enrichment routine that Phase 7 (or Phase 8) calls after anomaly scoring exists — not by this feature re-running.

**Rationale**: This is the outcome of the clarification resolved before drafting: MVP_CONTEXT.md lists `anomaly_count` as a Phase 5 window feature, but the anomaly model doesn't exist until Phase 7. A deferred/nullable column keeps the schema stable across phases (Phase 8's risk dataset construction can rely on the column existing) while avoiding fabricating a value before the real detector exists.

**Alternatives considered**: Dropping the field from Phase 5 entirely and adding it only in Phase 8 (the other option presented to the user, not selected — would have required Phase 8 to alter/extend the `WindowFeatures` schema rather than fill in an already-defined slot); computing a placeholder anomaly count from Phase 3's quality CRITICAL flags as a stand-in (rejected — conflates data-quality anomalies with the statistical/behavioral anomalies Phase 7 is specifically benchmarked to detect, which is a different signal).

## Decision: Categorical encoding scheme chosen per column by cardinality, with a documented unseen-category bucket

**Decision**: Low-cardinality categorical columns (e.g., `CLM_IP_ADMSN_TYPE_CD` with 3 values, `PRVDR_STATE_CD` with 51) use one-hot encoding; high-cardinality columns (`CLM_DRG_CD` with 167 values, diagnosis/procedure codes with hundreds+) use frequency encoding (replace category with its historical occurrence count/rate). Every encoder reserves an explicit "unseen" bucket/sentinel value for categories not present during fitting.

**Rationale**: One-hot encoding on a 167+ or diagnosis-code-cardinality column would explode feature dimensionality without clear benefit; frequency encoding scales to high cardinality while still being a real, computed (not fabricated) signal. An explicit unseen-category bucket satisfies FR-004/SC-005's requirement to handle new categories without erroring or silently aliasing to an existing category.

**Alternatives considered**: One-hot encoding everywhere (rejected — infeasible dimensionality for diagnosis/procedure codes); target encoding using the eventual risk label (rejected for claim/window-level general features — target encoding using a label that doesn't exist until Phase 8 would introduce a temporal/leakage dependency this early in the pipeline; reserved as a possible Stage 3 feature-selection technique in Phase 6 instead, where MVP_CONTEXT.md already anticipates "XGBoost importance" style label-aware steps).

## Decision: Length-of-stay reuses Phase 4's exact derivation via a shared utility, not a re-implementation

**Decision**: `claim_level/length_of_stay.py` imports the same date-difference logic Phase 4's `length_of_stay_baseline.py` uses (factored into a small shared utility function), rather than reimplementing `(NCH_BENE_DSCHRG_DT - CLM_ADMSN_DT).days` independently.

**Rationale**: Spec Acceptance Scenario 2 for User Story 1 explicitly requires this feature's length-of-stay to be "consistent with Phase 4's length-of-stay definition (same field derivation, not a second divergent formula)" — a shared utility is the only way to structurally guarantee that consistency rather than relying on two independent implementations staying in sync by convention.

**Alternatives considered**: Independent reimplementation (rejected — direct risk of the two formulas silently diverging, e.g., different missing-date exclusion handling).

## Decision: Window-level deviation features compute against Phase 4's baseline via its stored window definition, with mismatch detection

**Decision**: `deviation_features.py` reads `BaselineSnapshot.volume_baseline.window_definition` and asserts it matches the window definition configured for this feature run before computing any deviation; a mismatch raises a clear, typed error rather than computing a misleading deviation number.

**Rationale**: FR-007 explicitly requires detecting and reporting a window-definition mismatch instead of silently comparing incompatible windows — this is a direct, cheap-to-implement guard against a subtle correctness bug (e.g., comparing a daily window's claim count against a weekly baseline would produce a meaningless deviation).

**Alternatives considered**: Silently coercing/resampling to reconcile mismatched window definitions (rejected as unnecessary complexity for the MVP — mismatch should surface as a configuration error to fix, not be silently patched over).
