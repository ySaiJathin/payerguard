# Feature Specification: Risk Model Benchmark

**Feature Branch**: `009-risk-model-benchmark`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 9 — Risk model benchmark (MVP_CONTEXT.md Section 5): Logistic Regression (baseline) vs Random Forest vs XGBoost. Temporal 70/15/15 train/val/test split (no random shuffling — this is time-dependent data spanning 2015–2022). Evaluate accuracy/precision/recall/F1/ROC-AUC/PR-AUC/calibration/false-negative rate, prioritizing recall + PR-AUC. Select production model empirically."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Benchmark three classifiers on the real risk dataset under strict temporal discipline (Priority: P1)

As the implementer responsible for the risk-scoring half of PayerGuard's evidence-first story, I need Logistic Regression, Random Forest, and XGBoost each trained on Phase 8's risk dataset using Phase 6's exact temporal 70/15/15 split, so the eventual production risk model is backed by a real, leakage-free benchmark — never a random shuffle across this time-dependent 2015-2022 data.

**Why this priority**: This is the phase's entire purpose, and directly implements constitution Principle I for the risk track.

**Independent Test**: Can be tested by confirming all three models are fit using only Phase 8's rows falling in Phase 6's train-split date range, tuned only on validation-range rows, and scored on test-range rows exactly once.

**Acceptance Scenarios**:

1. **Given** Phase 8's `RiskDatasetRow` set and Phase 6's `TemporalSplit`, **When** the benchmark runs, **Then** Logistic Regression, Random Forest, and XGBoost are each fit on train-range rows only, with hyperparameter tuning performed on validation-range rows only.
2. **Given** all three models are tuned, **When** final evaluation runs, **Then** each is scored on test-range rows exactly once, producing accuracy/precision/recall/F1/ROC-AUC/PR-AUC/calibration/false-negative-rate metrics.
3. **Given** the temporal split is reused from Phase 6 (not recomputed here), **When** row-to-split assignment is checked, **Then** it matches Phase 6's `TemporalSplit` boundaries exactly — no re-shuffling introduced at this stage.

---

### User Story 2 - Select the production risk model empirically, prioritizing recall and PR-AUC (Priority: P1)

As the implementer, I need the production risk model selected based on real validation/test performance, prioritizing recall and PR-AUC over raw accuracy (since false negatives — missed investigation-worthy incidents — are the costly error), so the selection reflects the actual cost structure of this problem rather than a generic accuracy-maximizing choice.

**Why this priority**: Equal priority to Story 1 — the benchmark is only useful if its selection criteria match the problem's real cost asymmetry; MVP_CONTEXT.md explicitly calls this out ("false negatives are the costly error").

**Independent Test**: Can be tested by confirming the selected model is the one with the best recall+PR-AUC-weighted ranking among the three, even when a different model has higher raw accuracy.

**Acceptance Scenarios**:

1. **Given** three `BenchmarkResult` entries with different accuracy-vs-recall/PR-AUC trade-offs, **When** production selection runs, **Then** the model with the best recall+PR-AUC-prioritized ranking is selected, even if it isn't the highest-accuracy model.
2. **Given** the risk dataset's label distribution (from Phase 8, potentially imbalanced), **When** models are evaluated, **Then** PR-AUC (which is more informative than ROC-AUC under class imbalance) is reported and weighted into selection per MVP_CONTEXT.md's explicit framing.
3. **Given** the benchmark results, **When** a production model is selected, **Then** XGBoost is chosen only if it actually wins on the documented criteria — not by default assumption (mirroring Phase 7's HBOS caveat, applied here to XGBoost per MVP_CONTEXT.md Section 6).

---

### User Story 3 - Evaluate calibration, not just discrimination (Priority: P2)

As the implementer of Phase 10 (Severity/Business Impact/Priority scoring), I need the selected risk model's predicted probabilities to be evaluated for calibration (not just ranking ability), so downstream scoring that treats the Risk Score as a genuine 0-100 probability-like value is trustworthy.

**Why this priority**: Downstream phases (10+) consume the Risk Score as a probability, not just a ranking — calibration matters for that specific downstream use, but discrimination metrics (Story 1-2) are the primary benchmark axis, hence P2.

**Independent Test**: Can be tested by confirming a calibration metric (e.g., Brier score or a calibration-curve-derived statistic) is computed and reported per model on the test split.

**Acceptance Scenarios**:

1. **Given** the selected model's test-split predictions, **When** calibration is evaluated, **Then** a documented calibration metric is reported alongside the discrimination metrics.
2. **Given** a poorly-calibrated but well-discriminating model, **When** results are reported, **Then** the calibration gap is visible in the output (not hidden), informing whether Phase 10's Risk Score consumption needs a calibration adjustment step.

### Edge Cases

- What happens if Phase 8's label distribution is heavily imbalanced (as Phase 8's own edge cases anticipate)? The benchmark MUST report class balance alongside results and MUST use metrics/evaluation approaches appropriate to imbalance (PR-AUC, not relying on accuracy alone) — this is exactly why MVP_CONTEXT.md prioritizes recall + PR-AUC here.
- What happens if two models tie on the recall+PR-AUC-prioritized ranking? The selection MUST apply a documented, non-arbitrary tie-breaking rule (e.g., prefer better calibration, then lower false-negative rate).
- What happens if the validation-range data is too small to reliably tune hyperparameters (given the modest total window count from Phase 4/5's window definition)? This MUST be surfaced as a reportable data-scale limitation rather than silently proceeding with an unstable tuning result.
- What happens when this benchmark is re-run after new historical data is loaded (the continuous-ingestion phase was removed 2026-08-18) (extending Phase 8's dataset)? The benchmark MUST be re-runnable against the updated dataset and Phase 6's correspondingly-recomputed split, without requiring code changes, and previous results MUST remain distinguishable (versioned) from new results.
- What happens if none of the three models exceeds a reasonable minimum bar (e.g., barely better than a majority-class baseline) given how few windows currently exist in the historical data? This MUST be reported honestly, and production selection MUST proceed with whichever model is genuinely best (or flag that the dataset scale is currently insufficient for a confident production choice) rather than overstating confidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement three classifiers — Logistic Regression, Random Forest, and XGBoost — each trained on Phase 8's `RiskDatasetRow` set.
- **FR-002**: System MUST assign each `RiskDatasetRow` to train/validation/test using Phase 6's existing `TemporalSplit` date boundaries — MUST NOT recompute or randomly reshuffle the split.
- **FR-003**: System MUST fit every model exclusively on train-range rows, tune hyperparameters exclusively on validation-range rows, and evaluate on test-range rows exactly once per benchmark run.
- **FR-004**: System MUST compute accuracy, precision, recall, F1, ROC-AUC, PR-AUC, a calibration metric, and false-negative rate per model on the test split.
- **FR-005**: System MUST select the production model using a documented ranking rule that prioritizes recall and PR-AUC over raw accuracy, per MVP_CONTEXT.md's explicit framing.
- **FR-006**: System MUST select whichever model actually wins on the documented criteria — MUST NOT default to XGBoost without the benchmark confirming it (constitution Principle I).
- **FR-007**: System MUST apply a documented, non-arbitrary tie-breaking rule when models tie on the primary selection criteria.
- **FR-008**: System MUST report the risk dataset's label distribution (class balance) alongside benchmark results.
- **FR-009**: System MUST support re-running the benchmark against an updated (larger) risk dataset as new data is loaded (the continuous-ingestion phase was removed 2026-08-18), without code changes, with results versioned so prior and new benchmark runs remain distinguishable.
- **FR-010**: System MUST NOT fabricate or assume any benchmark metric or selection outcome — every value is computed from the actual train/validation/test data and actual model runs (constitution Principle II).

### Key Entities

- **RiskModelCandidate**: One of the three benchmarked classifiers, its fitted parameters, tuned hyperparameters, and the split it was fit/tuned on.
- **RiskBenchmarkResult**: Per-model, per-metric evaluation outcome (accuracy/precision/recall/F1/ROC-AUC/PR-AUC/calibration/FNR) on the test split, plus the label distribution context.
- **ProductionRiskModelSelection**: The final selected model, the documented ranking rule and rationale (including tie-breaking if applied), and a reference to the full `RiskBenchmarkResult` set.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three models' fitting/tuning data is verifiably confined to train/validation only — a leakage test using a corrupted test-split fixture produces identical fitted models and hyperparameters.
- **SC-002**: Every `RiskBenchmarkResult` metric is exactly reproducible by re-scoring the same selected model against the same test-split data.
- **SC-003**: `ProductionRiskModelSelection.selected_model` is verifiably the top performer under the documented recall+PR-AUC-prioritized ranking rule among the three `RiskBenchmarkResult` entries.
- **SC-004**: The label distribution (from Phase 8) is reported alongside every benchmark run's results.
- **SC-005**: A calibration metric is present in 100% of `RiskBenchmarkResult` entries.
- **SC-006**: Row-to-split assignment in this feature matches Phase 6's `TemporalSplit` boundaries with zero discrepancy (verified by a cross-check test).

## Assumptions

- The exact recall+PR-AUC-prioritized ranking formula (e.g., a weighted combination, or a lexicographic rule like "PR-AUC above a floor, then rank by recall") is a documented implementation choice for `/speckit-plan`, since MVP_CONTEXT.md states the priority qualitatively ("prioritizing recall + PR-AUC") without fixing exact weights — mirrors how Phase 7's anomaly-model ranking rule was left to the plan phase with the same reasoning.
- This feature does not compute the final 0-100 Risk Score used in Phase 10's Priority formula — it selects and evaluates the production model; Phase 10 (or a `risk.scoring` component within the same `risk` module) is responsible for applying the selected model to produce the 0-100 score for incidents.
- Given the current dataset's modest window count (tens of windows, not thousands), the benchmark's statistical power is limited; this is reported honestly per the Edge Cases requirement rather than treated as disqualifying — the benchmark discipline (temporal split, leakage prevention, documented selection) is what this feature guarantees, not a minimum sample-size guarantee, which is a data-scale characteristic outside this feature's control.
