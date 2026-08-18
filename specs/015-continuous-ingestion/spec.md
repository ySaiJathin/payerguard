# Feature Specification: Continuous Ingestion

**Feature Branch**: `015-continuous-ingestion`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 15 — Continuous ingestion (not live streaming) (MVP_CONTEXT.md Section 5): support repeated manual uploads / a watched-folder pattern that processes new batches through the same windowing and pipeline logic used for the historical baseline comparison — explicitly not a live claims-stream ingestion API/socket."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload a new batch and run it through the full pipeline (Priority: P1)

As an operator of PayerGuard, I need to upload a new batch of claims (structured the same as `inpatient.csv`) at any time after the initial historical load, and have it processed through the same cleaning → quality → baseline-comparison → feature → anomaly → risk pipeline already built in Phases 1-10, so new data is evaluated with the same rigor as the original historical file, without needing a live streaming service.

**Why this priority**: This is the phase's entire purpose — repeated batch ingestion is what "continuous" means here, and it's the direct prerequisite for everything else in this phase.

**Independent Test**: Can be tested by uploading a second, smaller batch (same schema as `inpatient.csv`) after the historical pipeline has already run, and confirming it flows through cleaning/quality/features/anomaly/risk using the existing Phase 2-9 logic (not duplicated pipeline code), producing new incidents where warranted.

**Acceptance Scenarios**:

1. **Given** a new batch file matching the expected schema (pipe-delimited, same 197-column structure validated in Phase 1/2), **When** it's uploaded, **Then** it is validated, cleaned, quality-checked, feature-engineered, and scored using the exact same service functions Phases 2-9 already implement — not a separate reimplementation.
2. **Given** the new batch is processed, **When** its windows are compared against the historical baseline, **Then** Phase 4's existing `BaselineSnapshot` (or a version appropriately extended, per Phase 4's FR-008 recomputation support) is used as the comparison reference.
3. **Given** the new batch produces a high-Priority finding, **When** processing completes, **Then** a real incident is created via Phase 12's existing incident-creation flow — the same downstream HITL/remediation/revalidation phases apply unchanged.

---

### User Story 2 - Support a watched-folder pattern for repeated batches (Priority: P2)

As an operator who wants to avoid manually triggering an upload every time, I need PayerGuard to support watching a designated folder and automatically picking up new batch files dropped into it, processing each one through the same pipeline as a manual upload, so repeated ingestion can be semi-automated without building a live streaming system.

**Why this priority**: This is a convenience layer over Story 1's core capability — Story 1 alone (manual upload) already satisfies "repeated ingestion," so the watched-folder pattern is an enhancement, not a hard prerequisite, hence P2.

**Independent Test**: Can be tested by placing a new valid batch file into the watched folder and confirming it's picked up and processed within a bounded, documented polling interval, without any API call being made by the operator.

**Acceptance Scenarios**:

1. **Given** a valid batch file is placed into the configured watched folder, **When** the watch process runs its next poll cycle, **Then** the file is picked up and processed through the identical pipeline used for a manual upload (Story 1) — no separate code path.
2. **Given** a file already processed from the watched folder, **When** the watch process polls again, **Then** it is not reprocessed (no duplicate ingestion of the same file).
3. **Given** the watched-folder mechanism, **When** inspected, **Then** it is explicitly documented and implemented as polling/file-detection — never a live socket or streaming connection, per MVP_CONTEXT.md's explicit "not live streaming" constraint.

---

### User Story 3 - Handle malformed or duplicate batch uploads safely (Priority: P2)

As an operator, I need malformed batch files (wrong schema, corrupted, empty) and accidentally-duplicated batch files to be rejected or flagged clearly, so a bad upload doesn't corrupt the pipeline's state or silently double-count claims.

**Why this priority**: An important safety net, but logically follows from Story 1 existing at all — a system with no ingestion has nothing to malform, hence P2.

**Independent Test**: Can be tested by uploading a file with the wrong column count and confirming it's rejected with a clear error (reusing Phase 1/2's existing schema validation), and by uploading the exact same valid file twice and confirming the second upload is detected and handled explicitly (not silently reprocessed as new data).

**Acceptance Scenarios**:

1. **Given** a batch file with an incorrect column count or unreadable format, **When** uploaded, **Then** it is rejected with a clear error before entering the pipeline, reusing Phase 1's existing schema-validation logic.
2. **Given** a batch file that is byte-identical to a previously-processed batch, **When** uploaded again, **Then** the system detects the duplicate batch and handles it explicitly (e.g., rejects with a "already processed" message, or reprocesses only on an explicit force flag) — never silently double-counting the same claims into the historical baseline or window features.
3. **Given** an empty batch file, **When** uploaded, **Then** it is rejected with a clear error rather than silently producing a zero-claim batch that pollutes downstream statistics.

### Edge Cases

- What happens to Phase 4's baseline when a new batch is ingested — does it get recomputed immediately, or only on request? This feature MUST make the recomputation trigger/policy explicit (e.g., new batches are processed against the existing baseline for scoring, and baseline recomputation to *include* the new batch as "historical" is a separate, explicit action) rather than leaving it ambiguous whether "historical" silently includes not-yet-reviewed new data.
- What happens if a new batch's date range overlaps with the existing historical data's date range (e.g., a correction/resupply of a previously-ingested period)? This MUST be detected and handled explicitly (flagged for review) rather than silently creating duplicate or conflicting window data for the same period.
- What happens if the watched-folder process is down/not running when a file is dropped? The file MUST be picked up on the next time the watch process starts/polls (no data loss), and this MUST be testable/verifiable, not just assumed.
- What happens to Phase 6's `TemporalSplit` and `SelectedFeatureSet` when new data extends the historical range? Per Phase 6's own FR-001 (support reuse) and this phase's Story 1 (reuse existing baseline logic), new-batch scoring uses the *existing* split/feature set for scoring; recomputing the split/feature selection to formally extend train/val/test boundaries is a separate, explicit re-run of Phase 6 — not an automatic side effect of ingesting one new batch.
- What happens to very large batch uploads (much larger than typical)? The system MUST handle them without unbounded memory growth or an unhandled failure — this is one of the explicit categories Phase 16's testing plan calls out ("large files").

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a new batch file upload (same schema/format as `inpatient.csv`) via an explicit endpoint, and MUST process it through the exact same cleaning (Phase 2), quality (Phase 3), feature engineering (Phase 5), anomaly scoring (Phase 7), and risk scoring (Phase 9) service functions already implemented — no duplicated/parallel pipeline implementation.
- **FR-002**: System MUST validate a new batch's schema using Phase 1/2's existing schema-validation logic before processing, rejecting malformed files with a clear error.
- **FR-003**: System MUST reject empty batch files with a clear error rather than producing a zero-claim batch that enters downstream statistics.
- **FR-004**: System MUST detect byte-identical duplicate batch uploads and handle them explicitly (reject by default, reprocess only via an explicit override), never silently double-processing the same data.
- **FR-005**: System MUST support a watched-folder mode that polls a configured directory at a documented interval and processes newly-detected valid files through the identical pipeline path used by manual upload (FR-001) — implemented via polling/file-detection only, never a live socket/streaming connection.
- **FR-006**: System MUST track which files have already been processed (by the watched-folder mode) so a restart of the watch process does not reprocess already-handled files, and so a file present before the watcher started is still picked up on its first poll.
- **FR-007**: System MUST detect and explicitly flag a new batch whose date range overlaps with already-ingested historical data, rather than silently creating conflicting window/claim data for the same period.
- **FR-008**: System MUST score new batches against the existing Phase 4 baseline and Phase 6 temporal split/feature set by default — recomputing/extending the baseline or the split to formally incorporate the new batch as "historical" MUST be a separate, explicit action, not an automatic side effect of ingestion.
- **FR-009**: System MUST create real incidents (via Phase 12's existing flow) when a newly-ingested batch produces high-Priority findings, using the same Phase 10 scoring logic unchanged.
- **FR-010**: System MUST handle large batch uploads without unbounded memory growth (e.g., streaming/chunked file reads where the underlying processing allows it) and without an unhandled crash.
- **FR-011**: System MUST NOT implement or expose any live socket/streaming ingestion endpoint — all ingestion is file-based (manual upload or watched-folder), per MVP_CONTEXT.md's explicit scope constraint.

### Key Entities

- **IngestedBatch**: One uploaded/detected batch file — filename, content hash (for duplicate detection), row count, date range, ingestion method (manual/watched-folder), processing status, timestamps.
- **BatchProcessingResult**: The outcome of running an `IngestedBatch` through the pipeline — links to the Phase 2-9 outputs produced for this specific batch, and any incidents created.
- **DateRangeOverlapFlag**: A record marking a batch whose date range overlaps existing historical data, pending explicit review.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of successfully ingested batches are processed using Phase 2-9's existing service functions — verified by a code-reuse audit (no duplicated pipeline logic introduced by this feature).
- **SC-002**: 100% of malformed or empty batch uploads are rejected before entering the pipeline, with a clear, distinguishable error.
- **SC-003**: 100% of byte-identical duplicate batch uploads are detected and handled per the documented policy (rejected by default) — zero silent double-processing.
- **SC-004**: A file dropped into the watched folder is processed within the documented polling interval, verified by an end-to-end test that starts the watcher, drops a file, and confirms processing completes.
- **SC-005**: Zero live socket/streaming endpoints exist in this feature's implementation — verified by an API-surface audit.
- **SC-006**: A large-batch fixture (significantly larger than `inpatient.csv`) is processed successfully without memory-growth failure, verified by a dedicated large-file test (feeding into Phase 16's testing suite).

## Assumptions

- The watched-folder polling interval is a configurable parameter (this spec requires it be documented and bounded, not a specific value); a reasonable default (e.g., 60 seconds) is an implementation choice for `/speckit-plan`.
- "Same schema/format as inpatient.csv" assumes new batches follow the identical CMS Inpatient RIF-like 197-column pipe-delimited structure — ingesting a genuinely different schema (e.g., outpatient claims) is out of scope, consistent with MVP_CONTEXT.md Section 4's single-dataset-type scope statement.
- This feature does not itself decide *when* to formally extend Phase 4's baseline or Phase 6's temporal split to include new batches as historical data — it only guarantees new batches can be scored against the existing ones and that extension remains an available, explicit, separate action (already supported by Phase 4 FR-008 and Phase 6's re-runnable design).
