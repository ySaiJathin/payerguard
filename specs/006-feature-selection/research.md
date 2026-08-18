# Phase 0 Research: Feature Selection

## Decision: This feature establishes the shared TemporalSplit, reused (not recomputed) by Phase 7 and Phase 9

**Decision**: `temporal_split.py` computes and persists the 70/15/15 chronological split once; Phase 7's anomaly benchmark and Phase 9's risk benchmark read `data/features/temporal_split.json` rather than each computing their own.

**Rationale**: Both MVP_CONTEXT.md Section 3.2 (anomaly leakage discipline) and Phase 9 (risk model's "Temporal 70/15/15... no random shuffling") require the identical discipline. A single shared split guarantees Phase 7 and Phase 9 evaluate against the exact same chronological boundaries, which matters for comparing results across the two benchmark tracks and for Phase 8's risk-dataset construction (which sits between them and needs a consistent notion of "which window is train vs. test").

**Alternatives considered**: Each phase computing its own independent split (rejected — risks subtle drift, e.g., off-by-one boundary differences, that would make Phase 7 and Phase 9 evaluate on technically different data even though both claim "70/15/15 temporal split").

## Decision: Stage 3's importance ranking uses a provisional target, explicitly flagged as provisional

**Decision**: Stage 3's XGBoost/permutation-importance step ranks candidate features against a provisional numeric target — the Phase 4 window-level amount/volume deviation magnitude (a real, already-computed signal indicating "how unusual is this window") — with the resulting `SelectedFeatureSet` explicitly tagged `target_used: "provisional_deviation_magnitude"` so anyone consuming it later knows it wasn't ranked against the real investigation-risk label.

**Rationale**: Phase 8 (which defines the real investigation-risk label) comes after this phase in the build order, but MVP_CONTEXT.md explicitly requires Stage 3 model-based importance as part of Phase 6. Using an already-real, already-computed signal (not a fabricated placeholder) keeps this consistent with Principle II, while flagging it as provisional keeps expectations honest — nothing here claims this is the final risk-label-informed importance ranking.

**Alternatives considered**: Skipping Stage 3 until after Phase 8 (rejected — contradicts the explicit phase ordering and task breakdown in MVP_CONTEXT.md Section 5, which places Stage 3 inside Phase 6, before Phase 8); using Phase 3's quality score as the target instead (considered viable alternative — quality score is also real and available; deviation magnitude was chosen because it's more directly related to the "unusual/investigation-worthy" concept Phase 8's label will eventually formalize, but either is defensible and the `target_used` tag makes the actual choice auditable regardless).

## Decision: `anomaly_count` is structurally exempted from missingness-based dropping, not just documented

**Decision**: Stage 1/2's missingness-threshold check explicitly skips any column tagged `deferred: true` in Phase 5's `WindowFeatures` schema (currently only `anomaly_count`), rather than relying on a hardcoded column-name exception list.

**Rationale**: A schema-level `deferred` tag (set once, in Phase 5) is more robust than a selection-stage exception list that would need updating every time a new deferred field is introduced — reduces the chance of a future deferred field being silently dropped as "high missingness" before it's ever populated.

**Alternatives considered**: A hardcoded exception list naming `anomaly_count` directly in the selection stage (rejected — works today but is fragile against schema evolution; the `deferred` tag approach generalizes for free).

## Decision: Correlation/redundancy tie-breaking prefers lower missingness, then simpler derivation

**Decision**: When Stage 2 finds two highly correlated features, it keeps the one with lower missingness; if missingness is equal, it keeps the one with the simpler derivation (fewer upstream dependencies, e.g., a direct column over a multi-step derived ratio).

**Rationale**: Directly satisfies the spec's edge case requiring a documented, non-arbitrary tie-breaking rule (spec Edge Cases, "Stage 2 MUST document which one was kept and why").

**Alternatives considered**: Keeping the feature with higher Stage 3 importance as the sole tie-breaker (rejected as the primary rule — Stage 3 runs after Stage 2 in the pipeline order, so it isn't available yet at Stage 2 decision time; missingness and derivation simplicity are both known before Stage 3 runs).
