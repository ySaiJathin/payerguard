# Feature Specification: Batch File Ingestion

**Feature Branch**: `017-batch-file-ingestion`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Batch file ingestion for PayerGuard. Scope: manual upload and repeated/batch upload of the same inpatient.csv-shaped CMS Medicare Inpatient RIF file (pipe-delimited, sep=\"|\", same 197-column schema profiled in Phase 1). Each upload is processed as a discrete batch through the existing pipeline (data engineering -> quality -> baseline -> features -> anomaly -> risk -> incidents). Explicitly NOT a live streaming API, NOT a socket-based claims feed, and NOT a claims simulator/random-claim generator. Track each upload as a batch (batch id, filename, upload timestamp, row count, status), support uploading the same file multiple times without conflict, and expose a way to list past batches."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload the real claims file and get it fully processed (Priority: P1)

As an operator, I need to upload the raw CMS Medicare Inpatient claims file (the same `inpatient.csv` shape this whole project is built on: pipe-delimited, 197 columns) and have it run through the entire existing pipeline — cleaning, quality validation, baseline comparison, feature engineering, anomaly detection, risk scoring, and incident creation — so that a real extract produces real, computed results without any manual, phase-by-phase intervention.

**Why this priority**: This is the missing front door. Every downstream phase (1 through 16) is fully built and tested, but there is currently no way to hand the system a real file and have it drive that pipeline end to end — `backend/app/ingestion/router.py` is still an unimplemented placeholder. Without this, the rest of the built system is unreachable from outside a test fixture.

**Independent Test**: Can be fully tested by uploading a real (or realistically-shaped) `inpatient.csv` extract and confirming a quality score, anomaly score, risk score, and any resulting incidents are produced and readable through the pipeline's existing read endpoints — the same artifacts every other phase already exposes.

**Acceptance Scenarios**:

1. **Given** a pipe-delimited file matching the 197-column raw claims schema, **When** it is uploaded, **Then** the system accepts it, processes it through every existing pipeline stage in order, and the resulting quality/baseline/anomaly/risk/incident data is retrievable through the pipeline's existing endpoints.
2. **Given** a file that is schema-conformant but contains claims data with real quality issues (missing values, duplicates, invalid values), **When** it is processed, **Then** those issues are handled exactly as Phase 2's existing cleaning behavior already handles them (corrected value, original value, and issue type preserved) — this feature does not introduce a second, different cleaning path.
3. **Given** a successfully processed upload, **When** its outcome is inspected, **Then** every number shown (quality score, anomaly score, risk score) is a real value computed by the existing benchmarked models and formulas, never a placeholder or estimate.

---

### User Story 2 - Upload the same or a new file again later as a separate batch (Priority: P1)

As an operator, I need to be able to upload a file — whether it's the exact same file again or a new extract covering a different date range — at any later time, and have it tracked as its own independent batch, so that repeated or periodic uploads (the normal way this system receives new data) never collide with or overwrite a previous upload's results.

**Why this priority**: Equal priority to Story 1 — "manual + repeated batch upload" is the explicit, named scope of this feature (MVP_CONTEXT.md Section 4 and Section 5 Phase 17), not a one-time-only capability. Without this, the system could ingest data exactly once and never again, which does not match "batch ingestion."

**Independent Test**: Can be fully tested by uploading the same file three times in a row (and a different file once more), and confirming four distinct, independently-retrievable batch records exist, each with its own results, none of which were overwritten by a later upload.

**Acceptance Scenarios**:

1. **Given** a file that was already uploaded and processed once, **When** the identical file is uploaded again, **Then** the system accepts it as a new, independent batch rather than rejecting it as a duplicate or silently reusing the prior batch's results.
2. **Given** two uploads submitted close together in time, **When** both are processed, **Then** each is tracked and resolved as its own batch with its own identity — neither upload's tracked record is lost or merged into the other's.

---

### User Story 3 - See what has been ingested and when (Priority: P2)

As an operator or reviewer, I need to list every batch that has been uploaded, with its filename, upload time, row count, and processing status, so I can confirm what data the system has actually ingested without having to separately track upload activity myself.

**Why this priority**: Builds on Stories 1-2's ingestion capability — valuable for operational visibility and for the audit trail, but the system is still functionally usable (an upload can be made and its results read) without a dedicated listing view, so this is one priority tier below the core ingest capability.

**Independent Test**: Can be fully tested by performing several uploads (some that succeed, at least one that is rejected for being non-conformant) and confirming the batch list accurately reflects filename, upload timestamp, row count, and the correct status for each, including the rejected one.

**Acceptance Scenarios**:

1. **Given** several prior uploads with a mix of outcomes, **When** the batch list is requested, **Then** it returns every batch with its filename, upload timestamp, row count, and current processing status, ordered so the most recent activity is easy to find.
2. **Given** a batch whose upload was rejected for not matching the expected schema, **When** the batch list is requested, **Then** that rejected attempt still appears with a status that clearly distinguishes it from a successfully-processed batch, rather than being silently dropped from history.

### Edge Cases

- What happens when an uploaded file uses the wrong delimiter, is missing required columns, or carries columns outside the expected 197-column raw schema? The system MUST reject it before any pipeline stage runs, with a specific, actionable reason (which columns are missing/unexpected), never a partial or silent ingestion.
- What happens when an uploaded file is empty, unreadable, or below a workable row count for the downstream models to fit on? The system MUST reject it with a clear reason rather than letting the failure surface deep inside a later pipeline stage.
- What happens when a file passes schema validation but fails partway through a later pipeline stage (e.g., a cleaning or quality step throws an unexpected error)? The batch's tracked status MUST honestly reflect that partial failure — never reported as "completed" when it did not actually finish, per this project's no-fabrication principle.
- What happens when an uploaded file is very large? The system MUST enforce a defined upper size/row limit and reject files beyond it with a clear reason, rather than accepting a file that could exhaust processing resources.
- What happens when two uploads are submitted at nearly the same time? Each MUST still resolve to its own distinct, correctly-tracked batch — concurrent uploads must not corrupt or interleave each other's tracked state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a manually-uploaded file shaped like the project's raw claims extract (pipe-delimited, `sep="|"`, the 197-column schema profiled in Phase 1 — see MVP_CONTEXT.md Section 2.2/2.3), not the already-cleaned schema.
- **FR-002**: System MUST validate an uploaded file's structure and column set against the expected raw schema *before* running any pipeline stage, and MUST reject a non-conformant file with a specific, actionable reason (naming which columns are missing or unexpected, or why the file could not be parsed).
- **FR-003**: On acceptance, system MUST process the uploaded file as a discrete batch through the existing pipeline stages in order — Phase 2 cleaning, Phase 3 quality validation, Phase 4 baseline comparison, Phase 5/6 feature engineering and selection, Phase 7 anomaly detection, Phase 8/9 risk scoring, Phase 10 severity/business-impact/priority, and Phase 12 incident creation — by reusing each phase's existing service logic, never by re-implementing or duplicating any phase's computation.
- **FR-004**: System MUST persist a tracked record for every upload attempt — accepted or rejected — capturing at minimum a batch identifier, the source filename, the upload timestamp, the row count (where determinable), and a processing status.
- **FR-005**: System MUST allow the same file (by content or filename) to be uploaded more than once, and MUST allow multiple sequential uploads over time, with each upload tracked as its own independent batch that never overwrites or is merged with a prior batch's tracked record or results.
- **FR-006**: System MUST expose a way to list previously uploaded batches, including each batch's filename, upload timestamp, row count, and current processing status, ordered with the most recent activity easy to find.
- **FR-007**: System MUST report a batch's processing status honestly at every stage (e.g., accepted / processing / completed / failed) — a batch MUST NOT be reported as completed unless every pipeline stage it went through actually finished successfully.
- **FR-008**: System MUST NOT provide a live streaming or socket-based ingestion path, and MUST NOT provide a client-facing random/synthetic-claim generator as part of this feature — scope is limited to manual and repeated-batch file upload, consistent with the removal of the continuous-ingestion spec (MVP_CONTEXT.md Section 4, Section 5 Phase 15 retired).
- **FR-009**: System MUST append an audit entry for every accepted and every rejected upload, and for the pipeline-stage activity a successful batch triggers, so this feature is covered by the existing audit-trail completeness guarantee (Phase 16) rather than being an unaudited gap.
- **FR-010**: System MUST enforce a defined maximum file size and a minimum workable row count, rejecting files outside those bounds with a clear reason rather than allowing an oversized or unworkably small file to enter the pipeline.

### Key Entities

- **IngestedBatch**: One tracked upload attempt — batch identifier, source filename, upload timestamp, row count, processing status (e.g., accepted / processing / completed / failed / rejected), and a reference to the pipeline-stage results it produced (if it reached that point). Distinct per upload even when the source file's content or name repeats.
- **BatchUploadRejection**: The specific, human-readable reason a given upload attempt was rejected before processing (e.g., wrong delimiter, missing/unexpected columns, empty file, below minimum row count, above maximum size).
- **BatchListing**: The queryable, ordered view over all `IngestedBatch` records exposed to an operator or reviewer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can upload a real, raw-schema claims extract and, in a single action, obtain a real quality score, anomaly score, risk score, and any resulting incidents — with no manual, phase-by-phase step required in between.
- **SC-002**: 100% of malformed or non-conformant uploads (wrong delimiter, wrong column set, empty file, below minimum rows, above maximum size) are rejected with a specific, human-readable reason, and zero pipeline stages run against a rejected file.
- **SC-003**: The same file can be uploaded five times in immediate succession and produces five independently-listable batch records with independent results, with zero collisions or overwrites, verified by a dedicated test.
- **SC-004**: For a batch deliberately made to fail partway through a pipeline stage in a test, its tracked status accurately reports the failure rather than "completed" — verified by a test that inspects status after an induced failure.
- **SC-005**: 100% of accepted and rejected uploads produce a corresponding audit-trail entry, verified against Phase 16's existing audit-source completeness check.

## Assumptions

- This feature ingests the **raw**, pre-cleaning claims schema (197 columns, pipe-delimited, per MVP_CONTEXT.md Section 2.2/2.3) — this is a different capability from `app/demo`'s existing `POST /demo/upload` endpoint, which accepts a file already matching the *cleaned/synthetic* column schema for demo and simulation purposes only. This feature does not modify, replace, or duplicate the demo module; it is the production front door the demo module's docstrings explicitly note does not yet exist for real data.
- "Repeated/batch" means a human or script can call the same upload capability again at any later time with a new or repeated extract — it does not mean the system watches a folder or maintains any persistent connection. Continuous/live ingestion was explicitly ruled out of scope when spec `015-continuous-ingestion` was removed (MVP_CONTEXT.md Section 4, Section 8 changelog item 10).
- Processing an accepted upload happens synchronously within the same request that accepts it, consistent with the pattern already established by `app/demo`'s existing upload path — no background job queue exists yet in this codebase, and introducing one is not required to meet this feature's scope.
- File size and minimum row-count limits are set to reasonable, documented defaults for this dataset's realistic scale (tens of thousands of rows) rather than being user-configurable in this pass.
- This feature completes MVP_CONTEXT.md Section 5's Phase 17. It does not depend on or extend Phase 18 (frontend), Phase 19 (Dockerization), Phase 20 (CI/CD), Phase 21 (AWS deployment), or Phase 22 (monitoring/retraining) — those remain separately scoped and deferred.
