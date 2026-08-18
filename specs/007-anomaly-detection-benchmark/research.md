# Phase 0 Research: Anomaly Detection Benchmark

## Decision: HBOS via `pyod`, other three via scikit-learn / hand-rolled IQR

**Decision**: Use `pyod.models.hbos.HBOS` for the HBOS implementation (matches the exact formula in MVP_CONTEXT.md Section 3.1: `Hj(x) = -log(Pj(x) + ε)`, `HBOS(x) = Σ Hj(x)`), `sklearn.ensemble.IsolationForest` and `sklearn.neighbors.LocalOutlierFactor` for the other two model-based candidates, and a hand-rolled IQR implementation (simple, formula is fully specified in Section 3.1 already) for the baseline.

**Rationale**: pyod is the standard, well-tested library implementing HBOS with the exact histogram-based formula this project documents; reimplementing it by hand risks subtle formula deviations. scikit-learn's Isolation Forest/LOF are the canonical implementations referenced generically by name in MVP_CONTEXT.md. IQR is simple enough (Q1/Q3/1.5×IQR bounds) that a hand-rolled implementation using pandas quantiles is more transparent than pulling in a dependency for it.

**Alternatives considered**: Hand-rolling HBOS from scratch (rejected — higher risk of formula bugs than using pyod's tested implementation, for a formula this project's own documentation already pins exactly); using scikit-learn's own HBOS-adjacent approaches (none exist natively in sklearn — pyod is the standard choice here).

## Decision: Primary ranking metric is F1 on injected anomalies, with FPR as tie-breaker, execution time as second tie-breaker

**Decision**: `model_selection.py` ranks the four `BenchmarkResult` entries primarily by F1 score (balances precision/recall, appropriate since neither over- nor under-flagging is free), with false-positive rate as the first tie-breaker (lower FPR preferred, since analysts reviewing flagged anomalies bear the cost of false positives) and execution time as the second tie-breaker (faster preferred, all else equal).

**Rationale**: MVP_CONTEXT.md doesn't fix a single formula for the anomaly track (unlike the risk model's explicit "recall + PR-AUC" framing in Phase 9), so the spec's Assumptions section requires the plan to pick and document a reasonable, defensible rule. F1 is the standard balanced metric for anomaly detection evaluation; FPR as tie-breaker reflects the operational cost of the analyst who has to review every flagged incident (MVP_CONTEXT.md Section 1's HITL narrative).

**Alternatives considered**: Recall-primary (rejected as primary — appropriate for the risk model where false negatives are explicitly called out as the costly error in Phase 9, but the anomaly-detection use case here feeds Severity/Priority scoring downstream rather than being the final investigation-worthy decision itself, so F1's balance is more appropriate); a single composite score combining all six metrics with arbitrary weights (rejected — would itself be an unjustified fabricated formula, whereas F1-then-FPR-then-latency is a standard, explainable cascade).

## Decision: Injection harness produces one combined validation copy and one combined test copy, with all 5 types represented and disjoint

**Decision**: For each of validation and test, the harness creates one working copy of that split and injects all five anomaly types into disjoint subsets of rows/cells within that copy (rather than five entirely separate copies per split), tracking each injected instance's `injection_type` and a `synthetic_instance_id`.

**Rationale**: A single combined copy per split is simpler to manage and score against (one evaluation pass per model per split, not five), while disjoint injection subsets keep the ground-truth labeling and per-injection-type metrics (spec Edge Cases: "traceable back to its injection type") unambiguous — no row is claimed by two injection types at once.

**Alternatives considered**: Five fully separate copies per split (rejected — multiplies evaluation runs five-fold for no accuracy benefit, since disjoint subsets within one copy achieve the same per-type traceability).

## Decision: `anomaly_count` enrichment scores real windows using the selected model's calibrated threshold, run as an explicit, separate step

**Decision**: `window_enrichment.py` is invoked only after `model_selection.py` has produced a `ProductionModelSelection`; it re-scores each window's real (non-injected) claims using the selected model and its validation-calibrated threshold (e.g., HBOS's 95th/99th percentile bands from Section 3.1), counting flagged claims per window.

**Rationale**: Keeps benchmark evaluation (which must touch injected/labeled data on validation/test copies) structurally separate from production enrichment (which must only ever score real, non-injected data) — reduces the risk of accidentally leaking injected instances into `anomaly_count`, which is meant to reflect genuine anomalies in the real dataset.

**Alternatives considered**: Computing `anomaly_count` as a byproduct of the benchmark's test-split evaluation pass (rejected — the test split is only 15% of the data and contains injected anomalies; `anomaly_count` needs to cover every real window across the full historical range, not just the test-split slice).
