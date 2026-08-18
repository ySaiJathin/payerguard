# Phase 0 Research: Risk Dataset Construction

## Decision: The investigation-risk label formula

**Decision**: Define a continuous **Investigation Risk Indicator (IRI)** per window:

```
IRI = w_q × norm(quality_failure_rate) + w_a × norm(anomaly_frequency) + w_d × norm(max(|volume_deviation|, |amount_deviation|))
```

where `norm(x)` min-max normalizes each signal to [0, 1] using statistics computed **only on Phase 6's train-split windows** (never validation/test, to avoid leakage into the label itself), and default weights `w_q = 0.4, w_a = 0.4, w_d = 0.2` (quality and anomaly weighted equally as the two most direct "something is wrong here" signals; deviation weighted lower since it's a softer, more ambiguous signal — mirrors the illustrative-and-configurable weighting style MVP_CONTEXT.md Section 3.3 already uses for Severity).

`investigation_risk_label = 1` if `IRI` is at or above the 75th percentile of `IRI` computed over train-split windows (the top quartile of historical risk indicator is treated as investigation-worthy); `0` otherwise. Zero-claim windows always receive `investigation_risk_label = 0` (nothing to investigate) regardless of `IRI`, satisfying spec FR-006.

**Rationale**: This directly satisfies constitution Principle II's explicit callout that this specific judgment call ("the SLA-breach label in Phase 8") "requires a judgment call, that judgment must be written down and justified, not silently assumed." Using a normalized weighted composite (not a single dominant signal) reflects that all three named inputs (quality-failure rate, anomaly frequency, deviation) matter per MVP_CONTEXT.md Section 8's changelog entry describing the label as "built from quality-failure rate + anomaly frequency + volume/amount deviation." A percentile threshold calibrated on train-split data only avoids baking test-split information into the label definition itself, consistent with constitution Principle VII.

**Alternatives considered**: A fixed absolute threshold (e.g., "quality_failure_rate > 5%") on a single signal (rejected — MVP_CONTEXT.md explicitly frames this as a combination of three signals, not one); an unsupervised clustering approach to find "risk" clusters (rejected as unnecessary complexity for the MVP and harder to document/justify in the same explicit, formulaic way FR-003 requires); a fixed percentage target (e.g., "top 10% always investigation-worthy") instead of quartile (rejected — 75th percentile/quartile is a more standard, easily-explained convention, and the exact cutoff remains configurable per the spec's Assumptions).

## Decision: Row assembly reads persisted upstream outputs via direct file/API reference, never recomputation

**Decision**: `row_assembly.py` reads Phase 3's `quality_results.json`, Phase 4's `baseline_snapshot.json`, Phase 5's `window_features.csv` (post Phase 7 enrichment), and Phase 7's `anomaly_benchmark_results.json` directly — joining on `window_id` — rather than recomputing any statistic.

**Rationale**: FR-002 explicitly requires this to avoid divergence between this feature's numbers and the upstream phases' own numbers; this is the same "read, don't recompute" pattern already established in Phase 4 (reading Phase 3's quality results) and Phase 6 (reading Phase 5's features).

**Alternatives considered**: Recomputing GX failure count or anomaly frequency independently within this feature (rejected — duplicated logic, drift risk, directly against FR-002).

## Decision: `investigation_risk_label_formula.md` is a generated, versioned Markdown artifact, not just inline code comments

**Decision**: Every run of this feature (re)generates `data/risk/investigation_risk_label_formula.md`, stating the exact weights, normalization statistics (train-split min/max per signal), percentile threshold, and a paragraph explicitly citing MVP_CONTEXT.md Section 2.4's rejection of a timing-based label.

**Rationale**: FR-003/FR-004 and SC-003 require the derivation to be "persisted as a reviewable artifact, not only embedded in code" and to "explicitly reference" Section 2.4 — a generated Markdown file satisfies both "reviewable by a human" and "reproducible/versioned alongside the data it was computed from."

**Alternatives considered**: A docstring/code comment only (rejected — not independently reviewable without reading source code, and spec FR-003 explicitly rules this out: "not only embedded in code").
