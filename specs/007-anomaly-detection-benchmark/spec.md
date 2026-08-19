# Feature Specification: Anomaly Detection Benchmark

**Feature Branch**: `007-anomaly-detection-benchmark`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 7 — Anomaly detection benchmark (MVP_CONTEXT.md Section 5): implement IQR baseline, HBOS, Isolation Forest, LOF using the train/validate/test discipline in Section 3.2. Build an anomaly-injection harness (missing-value spike, amount spike, duplicate spike, volume drop, distribution shift) applied only to validation/test copies. Evaluate precision/recall/F1/FPR/detection latency/execution time. Select production model empirically (expected HBOS, but only if the benchmark confirms it)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Benchmark all four anomaly detectors under identical, leakage-free conditions (Priority: P1)

As the implementer responsible for defending PayerGuard's "empirically-driven, evidence-first" narrative (MVP_CONTEXT.md Section 1), I need IQR, HBOS, Isolation Forest, and LOF each trained on the same training split, tuned on the same validation split, and evaluated exactly once on the same untouched test split, so the eventual production choice is backed by a real, reproducible benchmark rather than an assumption.

**Why this priority**: This is the phase's entire purpose — without a real, fair, leakage-free comparison, "we benchmarked and selected empirically" would be a false claim, directly violating constitution Principle I.

**Independent Test**: Can be tested by running the benchmark and confirming all four models were fit using only Phase 6's `TemporalSplit` train portion, calibrated only on the validation portion, and scored on the test portion exactly once (no repeated test-set peeking).

**Acceptance Scenarios**:

1. **Given** Phase 6's shared `TemporalSplit` and `SelectedFeatureSet`, **When** the benchmark runs, **Then** IQR, HBOS, Isolation Forest, and LOF are each fit on the train portion only, with any threshold calibration (e.g., HBOS's 95th/99th percentile bands) performed on the validation portion only.
2. **Given** all four models are calibrated, **When** final evaluation runs, **Then** each model is scored on the test portion exactly once, producing precision/recall/F1/FPR/detection-latency/execution-time metrics per model.
3. **Given** the benchmark results, **When** a production model is selected, **Then** the selection is the model with the best validated performance on the documented metrics — HBOS only if it actually wins, per constitution Principle I ("If a benchmark contradicts the expected outcome... the benchmark result governs").

---

### User Story 2 - Inject synthetic anomalies into validation/test copies only, never training data (Priority: P1)

As the implementer, I need a synthetic anomaly-injection harness (missing-value spike, amount spike, duplicate spike, volume drop, distribution shift) applied only to copies of the validation and test data, because this dataset has no ground-truth anomaly labels — without injected anomalies, precision/recall/F1 cannot be computed at all.

**Why this priority**: Equal priority to Story 1 — without labeled anomalies to evaluate against, none of Story 1's precision/recall/F1 metrics are computable, making this a direct, non-optional prerequisite.

**Independent Test**: Can be tested by confirming the training data used to fit each model is byte-identical to the un-injected training split, while validation/test copies used for evaluation contain the injected anomalies with their ground-truth labels attached.

**Acceptance Scenarios**:

1. **Given** the validation and test splits, **When** the injection harness runs, **Then** each of the five injection types (missing-value spike, amount spike, duplicate spike, volume drop, distribution shift) is applied to separate copies (or a combined copy with disjoint injected instances), each labeled with ground truth (injected = anomaly, original = normal).
2. **Given** the training split, **When** the injection harness runs, **Then** the training data is never modified or copied through the injection harness — it remains exactly Phase 6's train portion.
3. **Given** an injected amount-spike instance, **When** a model scores it, **Then** the model's prediction is compared against the known ground-truth label (anomaly) to compute precision/recall/F1/FPR, per injection type and in aggregate.

---

### User Story 3 - Populate the deferred `anomaly_count` window feature (Priority: P2)

As the implementer of Phase 8 (risk dataset construction), I need the selected production anomaly model's real scores populated into Phase 5's deferred `WindowFeatures.anomaly_count` field, so the window-level feature set becomes complete and Phase 8 can build the risk dataset from real, non-null anomaly signals.

**Why this priority**: This closes the loop opened by Phase 5's deferred-field design decision; it depends on Stories 1-2 completing (a production model must be selected first), hence P2.

**Independent Test**: Can be tested by confirming `WindowFeatures.anomaly_count` transitions from null to a real computed integer for every window, using the selected production model's scores against real (non-injected) claim data.

**Acceptance Scenarios**:

1. **Given** a selected production anomaly model, **When** it is applied to the real (non-synthetic) claims in each window, **Then** the count of claims flagged anomalous (per the model's calibrated threshold) is written to that window's `anomaly_count` via Phase 5's dedicated enrichment endpoint.
2. **Given** this enrichment step runs, **When** `WindowFeatures` is queried afterward, **Then** zero windows retain a null `anomaly_count` (assuming the model ran against all windows) — nulls only remain for windows genuinely not yet processed.

### Edge Cases

- What happens if two or more models tie on the primary selection metrics? The selection process MUST apply a documented tie-breaking rule (e.g., prefer lower execution time, or prefer the simpler/more interpretable model) rather than an arbitrary unrecorded pick.
- What happens if none of the four models beats the IQR baseline? The benchmark MUST still report this honestly and the production selection MUST reflect it (potentially selecting the IQR baseline itself) rather than defaulting to HBOS by assumption.
- What happens when an injected anomaly instance coincides by chance with a real, naturally-unusual claim? The injection harness MUST track injected instances by explicit synthetic ID/flag so ground truth is unambiguous, independent of whether the underlying claim was already statistically unusual.
- What happens to detection-latency/execution-time measurement if run on different hardware across runs? These metrics MUST be reported with their measurement context (hardware/environment note) so comparisons across runs aren't misinterpreted as apples-to-apples across different environments.
- What happens if `WindowFeatures.anomaly_count` enrichment (Story 3) is run more than once? Re-running it MUST be idempotent — the same selected model against unmodified window data produces the same `anomaly_count` values, not an accumulating count.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement four anomaly detection approaches: IQR baseline, HBOS, Isolation Forest, and LOF, each operating on Phase 6's `SelectedFeatureSet`.
- **FR-002**: System MUST fit every model exclusively on Phase 6's `TemporalSplit` train portion, and MUST calibrate any thresholds (e.g., HBOS percentile bands per MVP_CONTEXT.md Section 3.1) exclusively on the validation portion.
- **FR-003**: System MUST evaluate every model on the test portion exactly once per benchmark run, computing precision, recall, F1, false-positive rate, detection latency, and execution time per model.
- **FR-004**: System MUST implement an anomaly-injection harness supporting missing-value spike, amount spike, duplicate spike, volume drop, and distribution-shift injection types, each producing ground-truth-labeled synthetic anomalies.
- **FR-005**: System MUST apply the injection harness only to copies of the validation and test splits — training data MUST remain byte-identical to Phase 6's unmodified train portion throughout the benchmark.
- **FR-006**: System MUST track injected anomaly instances with an explicit synthetic flag/ID distinguishing them from naturally-occurring data, independent of whether the underlying value happens to also be statistically unusual.
- **FR-007**: System MUST select the production anomaly model based on documented, real benchmark results — the selection MUST reflect whichever model actually wins on the documented metrics, even if that contradicts the expectation that HBOS wins (constitution Principle I).
- **FR-008**: System MUST apply a documented, non-arbitrary tie-breaking rule when models tie on primary selection metrics.
- **FR-009**: System MUST record the measurement context (hardware/environment) alongside detection-latency and execution-time metrics.
- **FR-010**: System MUST apply the selected production model to real (non-injected) claim data per window and populate Phase 5's deferred `WindowFeatures.anomaly_count` field via its dedicated enrichment endpoint.
- **FR-011**: The `anomaly_count` enrichment step (FR-010) MUST be idempotent — re-running it against unmodified window data and an unchanged selected model produces identical counts.
- **FR-012**: System MUST NOT fabricate or assume any benchmark metric, threshold, or selection outcome — every reported number is computed from the actual train/validation/test data and the actual model runs (constitution Principle II).

### Key Entities

- **AnomalyModelCandidate**: One of the four benchmarked approaches (IQR, HBOS, Isolation Forest, LOF), its fitted parameters/thresholds, and the split it was fit/calibrated on.
- **InjectedAnomalyInstance**: A synthetic anomaly injected into a validation/test copy — injection type, affected row(s)/column(s), ground-truth label, synthetic-instance flag.
- **BenchmarkResult**: Per-model, per-metric evaluation outcome (precision/recall/F1/FPR/latency/execution time) on the test split, plus the measurement context.
- **ProductionModelSelection**: The final selected model, the documented selection rationale (including tie-breaking if applied), and a reference to the full `BenchmarkResult` set it was derived from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four models' fitting/calibration data is verifiably confined to train/validation only — a leakage test using a corrupted test-split fixture produces identical fitted models and thresholds (mirroring Phase 6's SC-003 pattern, applied to model fitting this time).
- **SC-002**: 100% of the five injection types produce at least one ground-truth-labeled synthetic anomaly instance in the evaluation data, each traceable back to its injection type.
- **SC-003**: Every `BenchmarkResult` metric is exactly reproducible by re-scoring the same selected model against the same test-split-with-injections data.
- **SC-004**: `ProductionModelSelection.selected_model` is verifiably the best performer on the documented primary metric(s) among the four `BenchmarkResult` entries — no selection contradicts its own recorded benchmark numbers.
- **SC-005**: 100% of windows in `WindowFeatures` have a non-null `anomaly_count` after the Story 3 enrichment step runs against complete window data.
- **SC-006**: Re-running the `anomaly_count` enrichment step twice against unmodified data produces identical counts both times (idempotency).

## Assumptions

- "Primary selection metric(s)" for choosing among the four models follows MVP_CONTEXT.md's own framing for the anomaly track (precision/recall/F1/FPR/latency/execution time, evaluated holistically) — this spec does not fix a single weighted formula for ranking models, since MVP_CONTEXT.md doesn't specify one for anomaly detection (unlike the risk model's explicit "prioritize recall + PR-AUC" in Phase 9); the plan phase should document whatever reasonable, defensible ranking rule it applies (e.g., F1 as primary with FPR as a tie-breaker), and record it as part of `ProductionModelSelection`.
- The injection harness's exact spike magnitudes/rates (e.g., what constitutes a "volume drop") are tunable implementation parameters; this spec requires the five injection types to exist and produce labeled ground truth, not specific magnitude values.
- This feature both benchmarks anomaly models and performs the one-time `anomaly_count` enrichment described in Phase 5's deferred-field design; ongoing anomaly scoring as new batches arrive (the continuous-ingestion phase was removed 2026-08-18) re-triggers this same scoring-and-enrichment logic rather than requiring separate new logic.
