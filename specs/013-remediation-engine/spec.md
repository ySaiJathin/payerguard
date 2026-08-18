# Feature Specification: Remediation Engine

**Feature Branch**: `013-remediation-engine`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 13 — Remediation engine (MVP_CONTEXT.md Section 5): deterministic handlers only: duplicate flagging, approved imputation, approved status mapping. Anything unhandled → \"Manual Action Required.\" No LLM-invented fixes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Apply only pre-approved, deterministic remediation actions (Priority: P1)

As the person accountable for this system never taking an unvetted automated action on real claims data, I need the remediation engine to execute only from a fixed set of pre-approved, deterministic handlers (duplicate flagging, approved imputation, approved status mapping) once an incident is accepted, so every automated change is traceable to a specific, reviewed rule — never an LLM-improvised fix.

**Why this priority**: This is the direct implementation of constitution Principle V ("The remediation engine only performs actions with a pre-approved, deterministic mapping... the system never invents a fix") — the phase's entire reason for existing.

**Independent Test**: Can be tested by accepting an incident whose affected claims match a known duplicate-row condition (from Phase 2's duplicate detection) and confirming the remediation engine applies exactly the duplicate-flagging handler, with no other action taken and no LLM call made during execution.

**Acceptance Scenarios**:

1. **Given** an accepted incident whose affected claims include a Phase 2-flagged duplicate row, **When** remediation runs, **Then** the duplicate-flagging handler is applied (the duplicate is marked, per its pre-approved mapping) and the specific handler used is recorded.
2. **Given** an accepted incident whose affected claims include a missing value matching an approved-imputation rule (e.g., a documented, narrow imputation policy), **When** remediation runs, **Then** the approved-imputation handler is applied exactly as documented, and the imputed value plus the rule that produced it are recorded.
3. **Given** an accepted incident whose affected claims include a status-code needing an approved mapping (e.g., a known equivalent/corrected code), **When** remediation runs, **Then** the approved-status-mapping handler is applied per its documented mapping table, and the change is recorded.
4. **Given** remediation executes, **When** its implementation is inspected, **Then** it has zero code path that calls the LLM (Phase 11) to invent or suggest a fix at execution time — Phase 11's role ends at investigation/recommendation, never remediation execution.

---

### User Story 2 - Escalate anything unhandled as "Manual Action Required" (Priority: P1)

As a reviewer, I need any affected-claim condition that doesn't match one of the pre-approved handlers to be explicitly marked "Manual Action Required," so I know exactly which parts of an accepted incident still need my direct attention rather than being silently skipped or guessed at.

**Why this priority**: Equal priority — this is the other half of constitution Principle V's guarantee; without it, unhandled conditions would either error out unhelpfully or (worse) risk being silently ignored.

**Independent Test**: Can be tested by accepting an incident whose affected claims include a condition with no matching approved handler, and confirming the remediation output explicitly marks it "Manual Action Required" with the specific unhandled condition described.

**Acceptance Scenarios**:

1. **Given** an accepted incident with an affected-claim condition that matches no pre-approved handler, **When** remediation runs, **Then** that specific condition is marked "Manual Action Required" with a description of what wasn't handled and why.
2. **Given** an incident with a mix of handleable and unhandleable conditions, **When** remediation runs, **Then** the handleable conditions are remediated per their approved handlers while the unhandleable ones are separately marked "Manual Action Required" — the presence of unhandled conditions does not block remediation of the handled ones.
3. **Given** a "Manual Action Required" marking, **When** reviewed later, **Then** it remains visible in the incident's remediation record even after any handled conditions are resolved, so partial-automation cases are never mistaken for fully-resolved ones.

---

### User Story 3 - Remediate only accepted incidents, and only affected claims (Priority: P1)

As the person responsible for this system's safety boundary, I need the remediation engine to act only on incidents with an explicit "accepted" status (per Phase 12's HITL gate) and only on the specific claims identified as affected by that incident, so no remediation ever touches claim data without the required human authorization or acts beyond its documented scope.

**Why this priority**: Equal priority — directly implements constitution Principle IV's requirement that "No remediation touches claim data without an explicit human accept decision," scoped precisely by Principle V's "affected claims only" framing throughout MVP_CONTEXT.md.

**Independent Test**: Can be tested by attempting to trigger remediation on a non-accepted incident (pending, rejected) and confirming it's refused, and by confirming remediation on an accepted incident only modifies the claims listed as affected by that specific incident, not the full dataset.

**Acceptance Scenarios**:

1. **Given** an incident in any status other than "accepted," **When** remediation is attempted, **Then** the system refuses with a clear error — remediation never executes against a non-accepted incident.
2. **Given** an accepted incident with a specific list of affected claims, **When** remediation runs, **Then** only those specific claims are modified — no claim outside the incident's documented affected set is touched.
3. **Given** remediation completes, **When** the result is reviewed, **Then** every applied handler and every "Manual Action Required" marking references the specific claim(s) it applies to, supporting Phase 14's before/after revalidation.

### Edge Cases

- What happens if an approved handler's preconditions aren't actually met when remediation runs (e.g., the duplicate-flagging handler is selected but the row is no longer flagged as a duplicate by the time remediation executes, due to a race with re-ingestion)? The handler MUST re-verify its precondition at execution time and fall back to "Manual Action Required" if the condition no longer holds, rather than blindly applying a stale action.
- What happens if two different approved handlers could both plausibly apply to the same affected claim (e.g., both a status-mapping and an imputation rule)? The handler-selection logic MUST apply a documented precedence order, not an arbitrary/undocumented choice.
- What happens if remediation is triggered twice on the same accepted incident (e.g., a retry after a partial failure)? It MUST be idempotent — re-applying already-completed handlers MUST NOT double-apply a change (e.g., double-flagging a duplicate) or error unexpectedly.
- What happens to the approved-imputation and approved-status-mapping rule tables themselves — who approves changes to them? This feature MUST treat these tables as versioned, reviewable configuration (not inline magic values scattered through code), even though the approval workflow for changing them is outside this feature's scope.
- What happens if a claim is affected by multiple incidents simultaneously? Remediation for one incident MUST NOT silently interfere with or overwrite pending remediation state from another incident on the same claim — this MUST be handled explicitly (e.g., sequenced, or flagged as a conflict).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement exactly three deterministic remediation handlers: duplicate flagging, approved imputation, and approved status mapping — each driven by a versioned, reviewable configuration table, not inline magic values.
- **FR-002**: System MUST execute remediation only for incidents with status "accepted" (per Phase 12's HITL gate) — MUST refuse with a clear error for any other status.
- **FR-003**: System MUST scope remediation strictly to the specific claims identified as affected by the incident being remediated — MUST NOT modify any claim outside that documented set.
- **FR-004**: System MUST mark any affected-claim condition matching no approved handler as "Manual Action Required," with a description of the specific unhandled condition, without blocking remediation of other, handleable conditions on the same incident.
- **FR-005**: System MUST NOT call the LLM (Phase 11) or any other model to invent, select, or suggest a remediation action at execution time — handler selection is driven solely by the pre-approved, deterministic configuration tables.
- **FR-006**: System MUST re-verify each handler's precondition at execution time immediately before applying it, falling back to "Manual Action Required" if the precondition no longer holds.
- **FR-007**: System MUST apply a documented precedence order when more than one approved handler could plausibly apply to the same affected-claim condition.
- **FR-008**: System MUST be idempotent — re-running remediation on an incident where some handlers already completed MUST NOT double-apply those changes.
- **FR-009**: System MUST record, for every affected claim, either the specific handler applied (with its resulting change) or the "Manual Action Required" marking — every affected claim has an explicit, traceable remediation outcome.
- **FR-010**: System MUST detect and explicitly flag (not silently proceed on) the case where a claim is affected by more than one incident with pending/concurrent remediation.

### Key Entities

- **RemediationRule**: One entry in a versioned configuration table (duplicate-flagging criteria, an approved imputation rule, or an approved status-mapping rule), including its precondition and precedence rank.
- **RemediationAction**: The record of one applied handler against one specific claim — rule used, before/after value, incident reference, timestamp.
- **ManualActionRequired**: A record marking one specific affected-claim condition as unhandled — description, incident reference, affected claim, timestamp.
- **RemediationRun**: The aggregate result of one remediation execution against an accepted incident — the set of `RemediationAction` and `ManualActionRequired` records it produced.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of `RemediationAction` records reference one of the three documented handler types and its specific `RemediationRule` — zero ad hoc/undocumented actions.
- **SC-002**: 100% of remediation attempts against a non-"accepted" incident are refused with a clear error — zero successful remediation executions against pending/rejected incidents.
- **SC-003**: 100% of affected claims in a `RemediationRun` receive either a `RemediationAction` or a `ManualActionRequired` record — zero affected claims with no traceable outcome.
- **SC-004**: A code/dependency audit confirms zero import-time dependency from the remediation execution path to Phase 11's LLM client.
- **SC-005**: Re-running remediation on an incident with already-applied handlers produces zero duplicate `RemediationAction` records (idempotency verified by a dedicated test).
- **SC-006**: A precondition-invalidation test (handler selected, then precondition artificially invalidated before execution) results in a `ManualActionRequired` record, not an incorrectly-applied action.

## Assumptions

- The exact contents of the approved-imputation and approved-status-mapping rule tables (which specific values/mappings are pre-approved) are configuration data to be defined during implementation/plan, informed by Phase 2's cleaning-rules precedent (e.g., a status-mapping table might correct a known-equivalent `PTNT_DSCHRG_STUS_CD` variant) — this spec fixes the requirement that such tables exist, are versioned/reviewable, and are the sole source of remediation decisions, not their specific entries.
- "Approval" of a `RemediationRule` is a configuration-management concern (who edits the table, under what review) outside this feature's own scope, per the Edge Cases note — this feature's obligation is to treat the table as the sole authority at execution time, not to build an approval workflow for the table itself.
- This feature does not perform revalidation (re-running GX/anomaly/risk after remediation) — that is Phase 14, a separate feature that consumes this feature's `RemediationRun` output to know what changed.
