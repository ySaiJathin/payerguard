# Feature Specification: LLM Investigation (Mistral)

**Feature Branch**: `011-llm-investigation`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 11 — LLM investigation (Mistral) (MVP_CONTEXT.md Section 5): structured incident → Mistral → incident summary, likely root cause, evidence, business impact, recommended fix, prevention recommendation. LLM has read-only access to structured evidence; it never executes remediation. If evidence is insufficient, it must say so explicitly (\"Insufficient evidence to determine the root cause\") rather than guess."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Investigate a structured incident and produce a structured, evidence-grounded report (Priority: P1)

As the human reviewer who will act on this investigation (Phase 12), I need Mistral to analyze a structured incident (its Quality/Anomaly/Risk/Severity/Business Impact scores and underlying evidence) and produce a summary, likely root cause, supporting evidence, business impact narrative, recommended fix, and prevention recommendation, so I have a defensible starting point for my accept/reject decision instead of raw scores alone.

**Why this priority**: This is the phase's entire purpose and the direct input to Phase 12's human-in-the-loop review — nothing else in this phase matters without it working correctly.

**Independent Test**: Can be tested by feeding a structured incident (built from Phase 10's Severity/Business Impact/Priority plus Phase 3/7/9's underlying evidence) into the investigation service and confirming the response contains all six documented sections (summary, root cause, evidence, business impact, recommended fix, prevention recommendation), each grounded in the actual evidence supplied.

**Acceptance Scenarios**:

1. **Given** a structured incident with real Quality/Anomaly/Risk scores and specific GX check failures, **When** investigation runs, **Then** the response's root-cause section references the actual failing checks/anomaly signals supplied, not generic boilerplate.
2. **Given** the same structured incident, **When** investigation runs twice, **Then** both responses reference the same underlying evidence (allowing for natural language variation, not contradictory fact claims) since the input data is unchanged.
3. **Given** the investigation response, **When** it's stored, **Then** it is linked to the specific incident and the specific evidence snapshot it was generated from, so a later reviewer can see exactly what the LLM saw.

---

### User Story 2 - Never guess when evidence is insufficient (Priority: P1)

As someone accountable for this project's no-fabrication principle extending to the LLM layer, I need Mistral to explicitly state "Insufficient evidence to determine the root cause" (or an equivalent explicit insufficiency statement) when the structured evidence doesn't support a confident root-cause determination, rather than inventing a plausible-sounding explanation.

**Why this priority**: Equal priority to Story 1 — an LLM that confidently fabricates root causes when it shouldn't would be worse than no LLM investigation at all, given this project's evidence-first narrative (MVP_CONTEXT.md Section 1).

**Independent Test**: Can be tested by constructing a deliberately sparse/ambiguous incident (minimal evidence, conflicting signals) and confirming the investigation response explicitly states insufficient evidence rather than producing a confident-sounding but unsupported root cause.

**Acceptance Scenarios**:

1. **Given** an incident with minimal or ambiguous supporting evidence, **When** investigation runs, **Then** the root-cause section explicitly states the evidence is insufficient, rather than a fabricated-sounding definitive cause.
2. **Given** an incident with strong, clear evidence (e.g., a single dominant GX CRITICAL failure with a clear pattern), **When** investigation runs, **Then** the response provides a substantive root-cause determination (the insufficiency path is not applied indiscriminately to every incident).
3. **Given** a response marked insufficient-evidence, **When** it's reviewed downstream (Phase 12), **Then** the recommended-fix section correspondingly avoids prescribing a specific fix it cannot justify (e.g., defers to "Manual Action Required" territory rather than inventing a remediation).

---

### User Story 3 - Enforce read-only, non-executing LLM access (Priority: P1)

As the person responsible for this system's safety boundary, I need the LLM investigation service to have strictly read-only access to structured evidence and zero ability to execute remediation or write to claim data, so a prompt-injection or model-error scenario cannot cause unintended data changes.

**Why this priority**: Equal priority — this is a direct implementation of constitution Principle IV ("The LLM (Mistral) proposes; it never executes") and a hard safety boundary, not a nice-to-have.

**Independent Test**: Can be tested by inspecting the investigation service's dependencies/permissions and confirming it has no code path capable of writing to `claims`, `remediations`, or any mutating table/endpoint — only read access to evidence and write access to its own investigation-result record.

**Acceptance Scenarios**:

1. **Given** the investigation service's implementation, **When** its data-access boundary is reviewed, **Then** it can only read structured evidence (Phase 3/4/7/9/10 outputs) and write its own `LLMInvestigation` result — no other write path exists.
2. **Given** a malicious or malformed incident payload attempting prompt injection (e.g., evidence text containing instructions to "delete all claims"), **When** investigation runs, **Then** no remediation or data mutation occurs — the service structurally cannot act on such instructions regardless of what the LLM outputs.
3. **Given** the investigation result, **When** consumed by Phase 12, **Then** it is treated strictly as a recommendation requiring human accept/reject — the investigation service itself never marks an incident resolved or triggers remediation.

### Edge Cases

- What happens when the Mistral API call fails (timeout, rate limit, service error)? The system MUST surface a clear, distinguishable failure state (not silently retry indefinitely, and not fabricate a fallback investigation result).
- What happens when Mistral's response doesn't conform to the expected structured format (missing a required section)? The system MUST detect this and treat it as a failed/incomplete investigation requiring re-run or human escalation, rather than silently presenting a partial result as complete.
- What happens when the same incident is investigated multiple times (e.g., after a human rejects and requests recalculation, per Phase 12)? Each investigation MUST be recorded as a distinct, timestamped result, preserving prior investigations for audit rather than overwriting them.
- What happens if the structured evidence contains a claim-amount or score value that's `unavailable` (e.g., Phase 10's Business Impact component)? The investigation prompt MUST represent this "unavailable" state accurately to the LLM (not coerce it to a fabricated number) so the LLM's business-impact narrative correctly reflects known unknowns.
- What happens to the `MISTRAL_API_KEY` and other secrets in this feature's implementation? They MUST be sourced from environment configuration (`.env`, gitignored) and never hardcoded or logged in plaintext, consistent with MVP_CONTEXT.md Section 7.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST construct a structured incident payload from Phase 3 (quality), Phase 7 (anomaly), Phase 9 (risk), and Phase 10 (Severity/Business Impact/Priority) outputs, representing every included value accurately (including any `unavailable` markers from Phase 10) before sending it to the LLM.
- **FR-002**: System MUST call Mistral with the structured incident and MUST parse the response into six documented sections: summary, likely root cause, evidence, business impact, recommended fix, and prevention recommendation.
- **FR-003**: System MUST require the LLM to explicitly state insufficient evidence (rather than a fabricated root cause) when the structured evidence doesn't support a confident determination, and MUST NOT post-process an insufficiency statement into a manufactured-sounding conclusion.
- **FR-004**: System MUST validate that the LLM response conforms to the expected structured format, treating a malformed/incomplete response as a failed investigation requiring re-run or escalation — never presented to a human reviewer as if it were complete.
- **FR-005**: System MUST grant the investigation service read-only access to structured evidence — it MUST have no code path capable of writing to `claims`, `remediations`, or any other mutating store; its only write capability is persisting its own investigation result.
- **FR-006**: System MUST persist every investigation result as a distinct, timestamped record linked to the specific incident and the specific evidence snapshot used, preserving prior investigations across re-runs (never overwriting).
- **FR-007**: System MUST surface a clear, distinguishable failure state when the Mistral API call fails (timeout, rate limit, error), without silently retrying indefinitely or fabricating a fallback result.
- **FR-008**: System MUST source `MISTRAL_API_KEY` from environment configuration only, never hardcoded or logged in plaintext.
- **FR-009**: System MUST treat every investigation result strictly as a recommendation — the investigation service itself MUST NOT mark an incident resolved, trigger remediation, or otherwise mutate incident/claim state.

### Key Entities

- **StructuredIncidentPayload**: The evidence bundle assembled for the LLM — quality/anomaly/risk/severity/business-impact values (including `unavailable` markers), affected-claim references, and window/incident context.
- **LLMInvestigation**: One persisted investigation result — `summary`, `likely_root_cause` (or an explicit insufficiency statement), `evidence`, `business_impact_narrative`, `recommended_fix`, `prevention_recommendation`, linked `incident_id`, `evidence_snapshot_id`, `generated_at`, and `model_version`.
- **InvestigationFailure**: A recorded failed-investigation attempt (API error or malformed-response case), distinct from a successful `LLMInvestigation`, so failures are auditable rather than silently dropped.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of successful `LLMInvestigation` records contain all six documented sections, non-empty.
- **SC-002**: For a fixture incident with deliberately sparse/ambiguous evidence, the investigation response explicitly states insufficient evidence in 100% of test runs (not probabilistically sometimes fabricating a cause).
- **SC-003**: A code/dependency audit confirms the investigation service has zero write access to `claims`/`remediations`/incident-mutating endpoints — only to its own `LLMInvestigation` record.
- **SC-004**: 100% of Mistral API failures produce a distinguishable `InvestigationFailure` record rather than a silently degraded or fabricated `LLMInvestigation`.
- **SC-005**: Re-investigating the same incident twice produces two distinct, timestamped `LLMInvestigation` records, with the first preserved unmodified.
- **SC-006**: Zero instances of `MISTRAL_API_KEY` appearing in source code, committed files, or logs (verified by a secret-scan check in the test suite).

## Assumptions

- The exact prompt template/structure sent to Mistral is an implementation detail for `/speckit-plan`; this spec fixes the required output structure (six sections) and behavioral guarantees (insufficiency handling, read-only access), not the prompt wording itself.
- "Evidence snapshot" (FR-006) means the specific Phase 3/4/7/9/10 output values used to build the `StructuredIncidentPayload` at investigation time are captured/referenced alongside the result, so a later reviewer can reconstruct exactly what the LLM was shown even if upstream data changes afterward.
- This feature does not decide when an investigation is triggered (that's Phase 12's incident-creation/recalculation flow calling into this feature) — it defines the investigation capability itself.
