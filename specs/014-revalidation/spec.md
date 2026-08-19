# Feature Specification: Revalidation

**Feature Branch**: `014-revalidation`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 14 — Revalidation (MVP_CONTEXT.md Section 5): re-run GX + anomaly + risk on affected claims after remediation; produce before/after comparison using real recomputed values; mark incident Resolved or Reopened."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recompute quality, anomaly, and risk signals on remediated claims (Priority: P1)

As a reviewer who accepted a remediation, I need Phase 3's quality checks, Phase 7's anomaly scoring, and Phase 9's risk scoring re-run on the specific claims that were remediated, using real recomputed values, so I can see whether the remediation actually fixed the underlying problem rather than just marking it "done."

**Why this priority**: This is the phase's entire purpose — without genuine recomputation, "before/after" would be meaningless, directly risking a repeat of the no-fabrication violations this project has already corrected elsewhere.

**Independent Test**: Can be tested by remediating a fixture claim with a known quality issue (e.g., a duplicate flagged and resolved), then confirming Phase 3's quality check for that specific claim is re-run and produces a genuinely different (improved) result reflecting the remediation.

**Acceptance Scenarios**:

1. **Given** a `RemediationRun` with completed `RemediationAction` records (Phase 13), **When** revalidation runs, **Then** Phase 3's relevant expectation checks are re-executed against the remediated claims' current state, producing new `ExpectationCheckResult` entries (not reusing the pre-remediation ones).
2. **Given** the same remediated claims, **When** revalidation runs, **Then** Phase 7's selected production anomaly model re-scores them, producing a new anomaly score.
3. **Given** the same remediated claims (and their window), **When** revalidation runs, **Then** Phase 9's selected production risk model re-scores the affected window, producing a new risk score.
4. **Given** all three re-scored signals, **When** Phase 10's Severity/Business Impact/Priority scoring functions are re-invoked (per their documented reusability, Phase 10 FR-011), **Then** a genuine "after" Priority score is produced from the real recomputed values.

---

### User Story 2 - Produce an honest before/after comparison (Priority: P1)

As a reviewer, I need a clear before/after comparison of Quality/Anomaly/Risk/Severity/Priority for the remediated incident, using the real pre-remediation values already stored on the incident and the real post-remediation recomputed values, so I can judge whether the remediation genuinely improved the situation.

**Why this priority**: Equal priority — a before/after comparison built from anything other than two genuine snapshots would misrepresent the remediation's effect, violating the project's evidence-first principle.

**Independent Test**: Can be tested by comparing a fixture incident's stored pre-remediation scores against the Story 1 recomputed post-remediation scores, and confirming the comparison output shows the real delta (which may be an improvement, no change, or even a regression — not assumed to always improve).

**Acceptance Scenarios**:

1. **Given** an incident's original (pre-remediation) Quality/Anomaly/Risk/Severity/Priority scores, **When** the before/after comparison is generated, **Then** it pairs each with its genuine post-remediation counterpart from Story 1, computing the real delta for each.
2. **Given** a remediation that didn't actually improve one of the signals (e.g., risk score stayed the same or got worse), **When** the comparison is generated, **Then** it reports that honestly — the comparison logic never assumes or forces an improvement narrative.
3. **Given** the comparison, **When** persisted, **Then** it remains permanently linked to the specific `RemediationRun` it evaluates, supporting the full audit trail (Phase 16).

---

### User Story 3 - Mark the incident Resolved or Reopened based on real revalidation results (Priority: P1)

As a reviewer, I need the incident automatically marked "Resolved" when revalidation shows the underlying issue is genuinely fixed, or "Reopened" when it isn't, so incidents don't sit indefinitely in an ambiguous state after remediation.

**Why this priority**: Equal priority — this is the concrete, actionable outcome of Stories 1-2; without it, revalidation would produce data but no decision.

**Independent Test**: Can be tested with two fixtures — one where recomputed Quality/Anomaly/Risk genuinely clear the relevant PASS/thresholds (expect "Resolved") and one where they don't (expect "Reopened") — confirming the status transition matches the real recomputed evidence in both cases.

**Acceptance Scenarios**:

1. **Given** post-remediation recomputed signals that clear the documented resolution criteria (e.g., no remaining CRITICAL quality checks and anomaly/risk scores back within normal bands for the affected claims), **When** revalidation completes, **Then** the incident transitions to "Resolved" via Phase 12's incident state machine (extending the reserved status from Phase 12's FR-008).
2. **Given** post-remediation recomputed signals that still show a CRITICAL quality check or an elevated risk/anomaly score, **When** revalidation completes, **Then** the incident transitions to "Reopened," making it available for further review/remediation rather than being closed prematurely.
3. **Given** an incident with any "Manual Action Required" markings still outstanding from Phase 13, **When** revalidation runs, **Then** it MUST NOT mark the incident "Resolved" while unresolved manual actions remain — at most "Reopened" or a state that reflects the incomplete remediation.

### Edge Cases

- What happens if revalidation is triggered before remediation has actually completed (e.g., a `RemediationRun` still has pending handlers)? The system MUST refuse or clearly flag this rather than revalidating against a partially-remediated state and drawing a premature conclusion.
- What happens if a remediated claim's revalidated quality/anomaly/risk results are worse than before remediation? Per Story 2, this MUST be reported honestly, and per Story 3, the incident MUST be marked "Reopened," not "Resolved" — remediation is never assumed successful by default.
- What happens if Phase 7/9's production models have been re-benchmarked (a new model selected) between the original incident creation and this revalidation? Revalidation MUST use whichever model is currently the production selection at revalidation time, and MUST record which model version was used, so a later reviewer understands why "before" and "after" might have used different underlying models.
- What happens if revalidation is run multiple times on the same remediated incident (e.g., re-checking after additional manual fixes)? Each revalidation MUST be recorded as its own distinct, timestamped comparison — not overwriting prior revalidation history.
- What happens to claims affected by the incident that received a "Manual Action Required" marking in Phase 13 (never actually remediated)? Revalidation MUST still recompute their current signals (they may have changed for unrelated reasons) but MUST clearly distinguish "still has an outstanding manual action" from "was remediated and revalidated."

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST re-execute Phase 3's relevant expectation checks against the current state of every claim affected by a completed `RemediationRun`, producing new `ExpectationCheckResult` entries.
- **FR-002**: System MUST re-score the affected claims using Phase 7's current production anomaly model, producing a new anomaly score.
- **FR-003**: System MUST re-score the affected window using Phase 9's current production risk model, producing a new risk score.
- **FR-004**: System MUST re-invoke Phase 10's Severity/Business Impact/Priority scoring functions using the recomputed values from FR-001-FR-003, producing genuine post-remediation Severity/Business Impact/Priority scores.
- **FR-005**: System MUST generate a before/after comparison pairing the incident's original pre-remediation scores with the FR-001-FR-004 post-remediation scores, computing real deltas without assuming improvement.
- **FR-006**: System MUST persist the before/after comparison, permanently linked to the specific `RemediationRun` it evaluates.
- **FR-007**: System MUST mark the incident "Resolved" only when the recomputed signals clear documented resolution criteria AND no outstanding "Manual Action Required" markings remain from the associated `RemediationRun`.
- **FR-008**: System MUST mark the incident "Reopened" when recomputed signals do not clear resolution criteria, or when outstanding manual actions remain.
- **FR-009**: System MUST refuse to run revalidation against an incomplete/pending `RemediationRun`, with a clear error.
- **FR-010**: System MUST record which specific version of the Phase 7/9 production models was used for each revalidation, since the production selection may have changed since the incident's original scoring.
- **FR-011**: System MUST preserve full revalidation history — each revalidation run is a distinct, timestamped record, never overwriting a prior one.
- **FR-012**: System MUST NOT fabricate or assume any revalidation outcome — every recomputed value and every Resolved/Reopened determination is derived from real, current computation (constitution Principle II).

### Key Entities

- **RevalidationRun**: One execution of Stories 1-3 against a specific `RemediationRun` — recomputed Quality/Anomaly/Risk/Severity/Business Impact/Priority, model versions used, timestamp.
- **BeforeAfterComparison**: The paired pre/post values and computed deltas for each signal, linked to a `RevalidationRun`.
- **ResolutionDetermination**: The Resolved/Reopened outcome, the specific criteria evaluated, and whether outstanding manual actions blocked "Resolved."

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of `RevalidationRun` records contain genuinely recomputed (not reused/copied) Quality/Anomaly/Risk values for their affected claims — verified by a test asserting the recomputation functions were actually invoked, not skipped.
- **SC-002**: 100% of `BeforeAfterComparison` records show the real delta, including test cases where the delta is negative/unfavorable (verified by a fixture where remediation doesn't improve the signals).
- **SC-003**: Zero incidents are marked "Resolved" while any linked `ManualActionRequired` record (from the associated `RemediationRun`) remains outstanding.
- **SC-004**: Every `RevalidationRun` records the specific Phase 7/9 model versions used (FR-010), enabling a later audit to explain any before/after discrepancy caused by a model change rather than the remediation itself.
- **SC-005**: Re-running revalidation on the same incident produces a new, distinct `RevalidationRun` record each time — prior records remain queryable and unmodified.
- **SC-006**: 100% of revalidation attempts against an incomplete `RemediationRun` are refused with a clear error.

## Assumptions

- "Documented resolution criteria" (FR-007) is a configurable rule (e.g., no remaining CRITICAL quality checks for the affected claims, anomaly score back within the Section 3.1 NORMAL band, risk score below the configured investigation-worthy threshold) — this spec requires such criteria to exist and be applied consistently, not a single fixed numeric formula, mirroring how other phases (6, 7, 9) leave exact thresholds to the plan/implementation while fixing the requirement that they be documented.
- This feature extends Phase 12's incident status enum with "Resolved"/"Reopened" (already reserved per Phase 12's FR-008) rather than introducing a separate status model — the `hitl` module's state machine (Phase 12) is updated by this feature to include the transition rules into/out of these two states.
- This feature is triggered after Phase 13's remediation completes (either automatically, or via an explicit reviewer action) — the exact trigger mechanism (automatic vs. manual "revalidate" button) is an implementation/UX choice for later phases (Phase 17 frontend), not fixed here; this spec only requires the capability to exist and be callable.
