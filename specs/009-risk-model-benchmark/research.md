# Phase 0 Research: Risk Model Benchmark

## Decision: Selection ranking rule — PR-AUC floor gate, then rank by recall, calibration as tie-break

**Decision**: `model_selection.py` first excludes any model whose PR-AUC falls below a documented minimum floor relative to the label base rate (i.e., meaningfully better than a random/majority-class baseline); among remaining candidates, it ranks by recall (highest first) as the primary criterion; if models tie on recall (rounded to a documented precision, e.g., 3 decimal places), calibration metric (lower Brier score preferred) breaks the tie, then false-negative rate as a final tie-break.

**Rationale**: MVP_CONTEXT.md states the priority qualitatively ("prioritizing recall + PR-AUC") without a fixed formula, and the spec's Assumptions require the plan to pick and document a defensible rule. A PR-AUC floor gate first prevents selecting a model that merely predicts everything positive to inflate recall (which would trivially maximize recall while being useless); ranking survivors by recall directly implements "false negatives are the costly error" (Phase 9's own stated rationale).

**Alternatives considered**: A single weighted composite of recall and PR-AUC (e.g., `0.5*recall + 0.5*PR-AUC`) — rejected as arbitrary weighting no more justified than the gate-then-rank approach, and less protective against the "predict-everything-positive" degenerate case that pure recall-weighting risks; PR-AUC as the primary sort key with recall as tie-break (considered viable — noted as an equally defensible alternative ordering; gate-then-recall was chosen because MVP_CONTEXT.md's own phrasing lists "recall" first and frames false negatives, not overall precision-recall trade-off curve area, as the specific cost being minimized).

## Decision: Calibration metric is Brier score

**Decision**: Report Brier score (mean squared error between predicted probability and actual binary outcome) as the calibration metric for every model.

**Rationale**: Brier score is a standard, simple, well-understood calibration metric that doesn't require binning choices (unlike a calibration-curve/reliability-diagram statistic, which needs a bin-count decision) — keeps the metric itself simple to compute and reproduce exactly (spec SC-002).

**Alternatives considered**: Expected Calibration Error (ECE) via binned reliability diagrams (rejected as the primary reported metric — requires an arbitrary bin-count choice that would itself need documentation/justification; may still be computed as a supplementary diagnostic during implementation, but Brier score is the one guaranteed by this spec).

## Decision: Row-to-split assignment cross-checked against Phase 6, not independently derived

**Decision**: `benchmark_runner.py` joins each `RiskDatasetRow` (which already carries `window_start`/`window_end` per Phase 8's FR-007) against Phase 6's `TemporalSplit` date ranges to assign train/validation/test, and a dedicated test asserts this assignment matches what Phase 6 would produce directly on the same windows.

**Rationale**: FR-002 explicitly forbids recomputing or reshuffling the split — cross-checking against Phase 6's persisted boundaries (rather than, say, re-deriving a fresh 70/15/15 split from Phase 8's row dates independently) is the only way to guarantee Phase 6, Phase 7's benchmark, and this feature all agree on exactly the same chronological boundaries.

**Alternatives considered**: Re-deriving a fresh 70/15/15 split from Phase 8's own row date range (rejected — even though it would likely produce the same boundaries in principle, it risks silent drift from Phase 6/7's split if window definitions or data scope differ even slightly, and directly contradicts FR-002's explicit "MUST NOT recompute").

## Decision: Benchmark results are versioned by `(risk_dataset_version, split_id)` pair

**Decision**: Each `RiskBenchmarkResult` set is tagged with the Phase 8 dataset version and Phase 6 split ID it was computed against, so re-running the benchmark after new data is loaded (the continuous-ingestion phase was removed 2026-08-18) produces a new, distinguishable result set rather than overwriting the prior one.

**Rationale**: Spec FR-009 requires re-runnability with distinguishable versioning as the dataset grows over time — this is the minimal versioning key needed to satisfy that without over-engineering a full model-registry system for the MVP.

**Alternatives considered**: No versioning, always overwrite (rejected — makes it impossible to compare "how did the benchmark change as more historical data arrived," which Phase 21's future monitoring work would want).
