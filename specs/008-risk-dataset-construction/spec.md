# Feature Specification: Risk Dataset Construction

**Feature Branch**: `008-risk-dataset-construction`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 8 — Risk dataset construction (MVP_CONTEXT.md Section 5): build incident/window-grain rows (GX failure count, anomaly score, affected-claim %, volume deviation, amount deviation, historical quality-failure rate, anomaly frequency, claim count). Define and document the investigation-risk label derivation explicitly, per Section 2.4: this dataset has no genuine SLA/processing-turnaround field, so the target is built from quality-failure rate + anomaly frequency + volume/amount deviation rather than a fabricated timing-based label."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Assemble window-grain rows from every upstream signal (Priority: P1)

As the implementer of Phase 9 (risk model benchmark), I need one row per processing window carrying every real, already-computed upstream signal — GX failure count, anomaly score, affected-claim %, volume deviation, amount deviation, historical quality-failure rate, anomaly frequency, claim count — so the risk model has a complete, real feature set to train against.

**Why this priority**: Without this assembled dataset, Phase 9 has nothing to train on — this is the direct, non-optional prerequisite.

**Independent Test**: Can be tested by confirming each window-grain row's fields are traceable back to a specific upstream feature/phase output (Phase 3's quality results, Phase 5/7's window features including the now-populated `anomaly_count`, Phase 4's baseline deviations) rather than being independently computed or assumed.

**Acceptance Scenarios**:

1. **Given** Phase 3's persisted quality-check results, **When** a window-grain row is assembled, **Then** its GX failure count reflects the real count of CRITICAL (and, per configuration, WARNING) checks for that window's claims.
2. **Given** Phase 7's enriched `WindowFeatures.anomaly_count`, **When** a window-grain row is assembled, **Then** its anomaly score/frequency fields are derived from that real, non-null value.
3. **Given** Phase 5's `WindowFeatures` volume/amount deviation fields, **When** a window-grain row is assembled, **Then** those exact values are carried through, not recomputed independently.
4. **Given** a window with zero claims (a legitimate historical gap, per Phase 4's zero-claim window handling), **When** a window-grain row is assembled for it, **Then** the row reflects genuine zero/undefined values for claim-dependent fields rather than being silently skipped or defaulted to a non-zero placeholder.

---

### User Story 2 - Derive and document the investigation-risk label explicitly (Priority: P1)

As the person responsible for defending this project's no-fabrication principle under scrutiny, I need the investigation-risk label's derivation from quality-failure rate, anomaly frequency, and volume/amount deviation written down explicitly — formula, thresholds, and reasoning — rather than an unexplained binary flag, so anyone reviewing the risk model later understands exactly what "investigation-worthy" means and why.

**Why this priority**: Equal priority to Story 1 — MVP_CONTEXT.md Section 2.4 and constitution Principle II both single this out as requiring explicit, written justification precisely because the original SLA-breach approach was rejected for being unsupported by the data; getting this wrong (or leaving it implicit) repeats the mistake this project already corrected once.

**Independent Test**: Can be tested by confirming a documented artifact (not just code) states the exact formula/thresholds combining the three input signals into the label, and that the label for any given window-grain row is reproducible by re-applying that documented formula to the row's own input fields.

**Acceptance Scenarios**:

1. **Given** a window-grain row's quality-failure rate, anomaly frequency, and volume/amount deviation, **When** the investigation-risk label is computed, **Then** it follows a single, documented formula/threshold — not a per-row ad hoc judgment.
2. **Given** the documented formula, **When** it is re-applied by hand to a row's own stored input fields, **Then** it reproduces that row's stored label exactly.
3. **Given** the label derivation document, **When** reviewed, **Then** it explicitly states why this combination was chosen (i.e., because no genuine SLA/processing-turnaround field exists, per MVP_CONTEXT.md Section 2.4) rather than assuming the reader already knows.

---

### User Story 3 - Preserve temporal ordering for the eventual train/val/test split (Priority: P2)

As the implementer of Phase 9, I need the risk dataset's rows to carry their window's chronological position explicitly, so Phase 9's mandated temporal 70/15/15 split can be applied without re-deriving chronology from scratch.

**Why this priority**: A direct enabler for Phase 9, but Phase 9 could theoretically re-derive ordering from window IDs alone — carrying it explicitly is a convenience/robustness improvement, hence P2 rather than P1.

**Independent Test**: Can be tested by confirming every window-grain row carries a date/ordering field consistent with Phase 4/5's window definition, and that sorting the dataset by this field reproduces the correct chronological window sequence.

**Acceptance Scenarios**:

1. **Given** the assembled risk dataset, **When** rows are sorted by their chronological field, **Then** the order matches the true chronological order of the underlying windows (2015-04-01 through 2022-10-31 span).
2. **Given** Phase 6's `TemporalSplit` (train/validation/test date boundaries), **When** the risk dataset's rows are matched against those boundaries, **Then** each row can be unambiguously assigned to train/validation/test without recomputing the split.

### Edge Cases

- What happens if Phase 7's `anomaly_count` enrichment hasn't been run yet when this feature executes? The risk dataset construction MUST fail fast with a clear error (missing prerequisite) rather than assembling rows with a fabricated or silently-zeroed anomaly signal.
- What happens to the investigation-risk label for a window with zero claims? The label derivation MUST explicitly define the behavior for this case (e.g., not investigation-worthy by definition, since there's nothing to investigate) rather than leaving it undefined or erroring.
- What happens if the three input signals (quality-failure rate, anomaly frequency, deviation) disagree strongly (e.g., high anomaly frequency but perfect quality)? The documented formula MUST still produce a deterministic label — the point of documenting the formula explicitly is that this kind of disagreement is resolved by the formula, not by ad hoc judgment at row-assembly time.
- What happens when this feature is re-run after Phase 15 adds new historical batches? The risk dataset MUST be regenerable from the (now larger) upstream data without manual intervention, and previously-labeled historical rows MUST remain reproducible (same formula applied to the same historical inputs yields the same label).
- What happens if the label derivation formula's chosen thresholds produce a heavily imbalanced label distribution (e.g., 99% not-investigation-worthy)? This MUST be surfaced as a reportable characteristic of the dataset (informing Phase 9's evaluation-metric choice, which already prioritizes recall + PR-AUC specifically because of class imbalance concerns) rather than silently rebalanced or hidden.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST assemble one row per processing window (matching Phase 4/5's window definition) containing: GX failure count (from Phase 3), anomaly score/frequency (from Phase 7's enriched `anomaly_count`), affected-claim % (claims flagged by any quality/anomaly check ÷ total claims in window), volume deviation and amount deviation (from Phase 5's `WindowFeatures`), historical quality-failure rate (from Phase 4's `DataHealthBaseline`), and claim count.
- **FR-002**: System MUST source every field in FR-001 from its corresponding upstream phase's persisted output — never recompute a value independently in a way that could diverge from the upstream source of truth.
- **FR-003**: System MUST derive the investigation-risk label using a single, explicitly documented formula/threshold combining quality-failure rate, anomaly frequency, and volume/amount deviation — the formula and its rationale MUST be persisted as a reviewable artifact, not only embedded in code.
- **FR-004**: The documented label-derivation formula MUST explicitly state why it does not use a timing/SLA-based approach, referencing the data limitation established in MVP_CONTEXT.md Section 2.4.
- **FR-005**: System MUST make the investigation-risk label reproducible: re-applying the documented formula to a row's own stored input fields MUST reproduce that row's stored label exactly, for every row.
- **FR-006**: System MUST explicitly define and apply the label derivation for zero-claim windows (e.g., defaulting to not-investigation-worthy, documented as part of the formula, not a special-cased exception left unexplained).
- **FR-007**: System MUST carry a chronological ordering field on every row, consistent with Phase 6's `TemporalSplit` date boundaries, so rows can be unambiguously assigned to train/validation/test without re-deriving chronology.
- **FR-008**: System MUST fail fast with a clear error if Phase 7's `anomaly_count` enrichment has not been completed, rather than assembling rows with a fabricated or assumed anomaly signal.
- **FR-009**: System MUST report the resulting label distribution (count/percentage investigation-worthy vs. not) as part of this feature's output, so downstream consumers (Phase 9) are aware of any class imbalance.
- **FR-010**: System MUST support regenerating the risk dataset from updated upstream data (Phase 15 continuous ingestion) without code changes, and MUST reproduce identical historical labels when re-run against unmodified historical inputs.

### Key Entities

- **RiskDatasetRow**: One window-grain row — all FR-001 fields, the chronological ordering field, and the derived `investigation_risk_label`.
- **InvestigationRiskLabelFormula**: The documented, versioned formula/threshold definition combining quality-failure rate, anomaly frequency, and volume/amount deviation into the label, plus its written rationale referencing Section 2.4.
- **LabelDistributionReport**: The count/percentage breakdown of the label across the assembled dataset.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of `RiskDatasetRow` fields are traceable to a specific upstream phase's persisted output (verified by a provenance test asserting no field is computed independently within this feature).
- **SC-002**: 100% of `RiskDatasetRow.investigation_risk_label` values are exactly reproduced when the documented `InvestigationRiskLabelFormula` is re-applied to that row's own stored inputs.
- **SC-003**: The `InvestigationRiskLabelFormula` artifact explicitly references MVP_CONTEXT.md Section 2.4's rejection of a timing-based label, satisfying constitution Principle II's requirement that this specific judgment call be "written down and justified."
- **SC-004**: Zero-claim windows produce a well-defined, documented label (not an error, not an undefined/null label) for 100% of such windows present in the historical data.
- **SC-005**: The `LabelDistributionReport` is present and accurate for every dataset-construction run, computed from the actual assembled rows.
- **SC-006**: Re-running this feature against unmodified upstream data reproduces byte-identical `RiskDatasetRow` records, including labels.

## Assumptions

- The investigation-risk label is binary (investigation-worthy / not) for the MVP, consistent with Phase 9's classifier framing (Logistic Regression / Random Forest / XGBoost, evaluated on precision/recall/F1/ROC-AUC/PR-AUC — standard binary-classification metrics); an ordinal/multi-level risk label is not required by MVP_CONTEXT.md and is out of scope unless a future phase asks for it.
- The exact formula combining the three input signals (weights, threshold) is defined and documented by this feature (per FR-003) rather than fixed in this spec, since MVP_CONTEXT.md itself only specifies the three input signals and the reasoning constraint (no timing-based label), not a precise formula — this mirrors how Section 3.3 defines Severity's formula with configurable weights rather than fixed values.
- "Affected-claim %" (FR-001) means the share of a window's claims flagged by at least one Phase 3 quality check (WARNING or CRITICAL) or Phase 7 anomaly detection — this combines the two upstream flagging sources into one interpretable percentage, consistent with how Phase 8's description groups "GX failure count, anomaly score... affected-claim %" together as related signals.
