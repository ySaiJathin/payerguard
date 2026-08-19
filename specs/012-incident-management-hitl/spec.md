# Feature Specification: Incident Management & Human-in-the-Loop

**Feature Branch**: `012-incident-management-hitl`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 12 — Incident management & HITL (MVP_CONTEXT.md Section 5): incident CRUD, accept/reject endpoints, feedback capture on reject, recalculation loop. Human feedback is stored for future retraining but never triggers automatic retraining from a single event."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create incidents from high-priority findings and manage them (Priority: P1)

As a reviewer using PayerGuard, I need incidents created from the pipeline's findings (Phase 10's Priority score, Phase 11's LLM investigation) and manageable through standard CRUD operations, so I have a durable, queryable record of every finding that warranted attention.

**Why this priority**: Incidents are the central object every downstream HITL/remediation/audit phase operates on — nothing else in Phases 12-16 works without this.

**Independent Test**: Can be tested by triggering incident creation for a window/finding with real Phase 10 Priority and Phase 11 investigation data, and confirming a queryable `Incident` record exists with all of that data attached.

**Acceptance Scenarios**:

1. **Given** a window/finding with a computed Priority score and a completed LLM investigation, **When** an incident is created, **Then** the resulting `Incident` record carries the real Quality/Anomaly/Risk/Severity/Business Impact/Priority scores and a reference to the `LLMInvestigation` record.
2. **Given** existing incidents, **When** listed/read, **Then** the API returns real persisted data (status, scores, investigation, timestamps) — never placeholder/demo data.
3. **Given** an incident's underlying evidence changes (e.g., after Phase 14 revalidation), **When** the incident is updated, **Then** the update is reflected without losing the incident's history (prior states remain auditable, not overwritten silently).

---

### User Story 2 - Accept or reject an LLM investigation's recommendation (Priority: P1)

As a reviewer, I need explicit accept/reject actions on an incident's LLM investigation, so remediation (Phase 13) only proceeds after my explicit human judgment, per this project's human-in-the-loop principle.

**Why this priority**: Equal priority — this is the direct implementation of constitution Principle IV ("No remediation touches claim data without an explicit human accept decision").

**Independent Test**: Can be tested by calling accept on an incident and confirming its status transitions to a state that authorizes Phase 13's remediation engine to proceed, and by calling reject and confirming remediation is never authorized without a subsequent accept.

**Acceptance Scenarios**:

1. **Given** an incident with a completed `LLMInvestigation`, **When** a reviewer accepts it, **Then** the incident transitions to an "accepted" status that Phase 13's remediation engine is authorized to act on, and the acceptance is timestamped and attributed to the acting reviewer.
2. **Given** an incident, **When** a reviewer rejects it, **Then** the incident transitions to a "rejected" status, remediation is never triggered from this rejection, and the system requires feedback capture (Story 3) as part of the reject action.
3. **Given** an incident already accepted, **When** a duplicate accept or a reject is attempted, **Then** the system handles the conflicting state transition explicitly (e.g., rejects the invalid transition with a clear error) rather than silently allowing an inconsistent state.

---

### User Story 3 - Capture feedback on reject and support recalculation (Priority: P1)

As a reviewer who rejects an LLM investigation, I need to provide feedback explaining why, and I need the system to support recalculating the incident's evidence/investigation afterward, so my judgment is captured for future retraining and I get a chance to re-review with updated information rather than the incident being a dead end.

**Why this priority**: Equal priority — MVP_CONTEXT.md explicitly requires "Reject decisions must capture feedback and trigger recalculation, not be silently dropped" (constitution Principle IV) — this is not optional.

**Independent Test**: Can be tested by rejecting an incident with feedback text, confirming the feedback is persisted and linked to the incident and the specific investigation it responds to, then triggering recalculation and confirming a new investigation cycle (Phase 11 re-invocation) becomes available for re-review.

**Acceptance Scenarios**:

1. **Given** a reviewer rejects an incident, **When** the reject action is submitted, **Then** feedback text (and a structured reason category, if provided) is required and persisted, linked to the specific incident and `LLMInvestigation` being rejected.
2. **Given** a rejected incident with feedback, **When** recalculation is triggered, **Then** the system re-invokes Phase 11's investigation (and, if the underlying evidence changed, the relevant upstream scoring) producing a new `LLMInvestigation` for the same incident, available for the reviewer to accept/reject again.
3. **Given** human feedback has been captured, **When** inspected, **Then** it is stored in a form suitable for future retraining use (e.g., linked to the specific incident's features/label) but the system does NOT automatically trigger model retraining from this single feedback event — retraining remains a separate, deliberate, gated process (Phase 21).

### Edge Cases

- What happens when an incident is created for a window that already has an open (not yet accepted/rejected) incident? The system MUST handle this explicitly — either preventing duplicate open incidents for the same window/finding or explicitly supporting multiple concurrent incidents with clear identification, rather than silently creating ambiguous duplicates.
- What happens if recalculation is requested but the underlying evidence (Phase 3/7/9/10 outputs) hasn't actually changed since the rejected investigation? The system MUST still support re-invoking Phase 11 (a reviewer may want a fresh LLM read even on unchanged evidence) but MUST NOT claim the evidence changed if it didn't.
- What happens to an incident if Phase 11's investigation fails (an `InvestigationFailure`, per Phase 11's spec) during initial creation or recalculation? The incident MUST reflect this failure state clearly (e.g., "investigation pending/failed") rather than presenting an incomplete investigation as ready for review.
- What happens to feedback if a reviewer rejects an incident multiple times across multiple recalculation cycles? Every reject/feedback event MUST be preserved as its own record (a full history), not overwritten by the latest one.
- What happens to an accepted incident once Phase 13/14 (remediation/revalidation) complete? This feature's incident status model MUST accommodate downstream status transitions (e.g., "resolved," "reopened" per Phase 14) without requiring a redesign — the status field is extensible, not a fixed two-state accept/reject flag.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support creating an `Incident` record from a window/finding's Phase 10 scores and Phase 11 investigation, and MUST support reading, listing (with filtering by status/priority), and updating incidents.
- **FR-002**: System MUST implement an explicit accept action that transitions an incident to an "accepted" status, timestamped and attributed to the acting reviewer, and that is the sole authorization mechanism Phase 13's remediation engine checks before acting.
- **FR-003**: System MUST implement an explicit reject action that transitions an incident to a "rejected" status and requires feedback (free text, plus a structured reason category) as part of the same action — the system MUST NOT allow a reject without feedback.
- **FR-004**: System MUST persist every feedback record linked to the specific incident and `LLMInvestigation` it responds to, preserving full history across multiple reject cycles (never overwritten).
- **FR-005**: System MUST support a recalculation action on a rejected incident that re-invokes Phase 11's investigation (and, if applicable, re-invokes affected upstream scoring), producing a new `LLMInvestigation` available for review, without discarding the prior rejected investigation or its feedback.
- **FR-006**: System MUST NOT trigger automatic model retraining (Phase 7/9's production models) from any single feedback event — feedback is stored for future, separately-gated retraining (Phase 21) only.
- **FR-007**: System MUST reject invalid state transitions explicitly (e.g., accepting an already-accepted incident, or accepting a rejected incident without a new investigation cycle) with a clear error, rather than silently allowing an inconsistent state.
- **FR-008**: System MUST design the incident status field to be extensible to downstream statuses introduced by Phase 13/14 (e.g., "resolved," "reopened") without requiring a breaking redesign of this feature's data model.
- **FR-009**: System MUST reflect a failed investigation (Phase 11's `InvestigationFailure`) in the incident's state clearly, distinguishing "investigation failed/pending" from "ready for review."
- **FR-010**: System MUST NOT fabricate any incident field — every score, timestamp, and status transition is either a real computed/user-supplied value or an explicit pending/failed state (constitution Principle II).

### Key Entities

- **Incident**: The central record — window/finding reference, Quality/Anomaly/Risk/Severity/Business Impact/Priority scores (from Phase 10), current status (extensible enum), linked `LLMInvestigation`(s), created/updated timestamps.
- **HumanFeedback**: One reviewer's feedback on a reject action — free text, structured reason category, linked `incident_id` and `LLMInvestigation` id, reviewer attribution, timestamp.
- **IncidentStatusTransition**: An audit record of every status change (who, when, from/to status), supporting the full accept/reject/recalculate history.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of created incidents carry real Phase 10 scores and a linked `LLMInvestigation` reference — zero placeholder/demo values.
- **SC-002**: 100% of reject actions require and persist feedback — zero reject records exist without linked `HumanFeedback`.
- **SC-003**: Zero instances of remediation being authorized from a rejected incident without an intervening accept — verified by a state-machine test covering all valid/invalid transitions.
- **SC-004**: 100% of recalculation actions produce a new, distinct `LLMInvestigation` record while the prior rejected investigation and its feedback remain queryable and unmodified.
- **SC-005**: Zero automatic retraining triggers fire from feedback capture — verified by a test asserting `HumanFeedback` persistence has no code path invoking Phase 7/9's model-fitting functions.
- **SC-006**: 100% of invalid state-transition attempts (e.g., double-accept) are rejected with a clear, distinguishable error rather than silently succeeding or corrupting state.

## Assumptions

- "Reviewer attribution" for accept/reject/feedback actions assumes a minimal identity concept (a reviewer identifier/name) exists for the MVP — this spec does not require a full authentication/authorization system (out of scope per MVP_CONTEXT.md, which has no multi-tenant/external-user access model defined); the plan phase may use a simple configured reviewer identity or a passed-in identifier field until real auth exists.
- Incident status values beyond "accepted"/"rejected" (e.g., "resolved," "reopened" from Phase 14) are anticipated but not fully defined by this feature — FR-008 requires the field be extensible, and Phase 14's own spec will define those additional values precisely when it's built.
- This feature owns incident lifecycle and HITL actions; it does not itself perform remediation (Phase 13) or revalidation (Phase 14) — it only authorizes/gates them via incident status.
