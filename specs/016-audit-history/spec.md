# Feature Specification: Audit & History

**Feature Branch**: `016-audit-history`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Phase 17 — Audit & history (MVP_CONTEXT.md Section 5): full audit log across every pipeline stage; /history and /baseline read endpoints."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See a complete audit trail across every pipeline stage for any claim or incident (Priority: P1)

As a reviewer or auditor, I need a single, complete audit log spanning every pipeline stage (deterministic check, model score, LLM output, human decision, remediation, revalidation) for any given claim or incident, so I can answer "what happened to this claim/incident and why" without manually cross-referencing a dozen different modules' individual stores.

**Why this priority**: This is the phase's entire purpose and the direct fulfillment of MVP_CONTEXT.md Section 1's closing promise ("Maintains full audit history of every decision") and constitution Principle V's "every step... is written to the audit log."

**Independent Test**: Can be tested by running a claim through the full pipeline (clean → quality → anomaly → risk → incident → LLM investigation → accept → remediate → revalidate) against fixtures, then querying this feature's audit log for that claim/incident and confirming every one of those stages appears as a distinct, correctly-ordered entry.

**Acceptance Scenarios**:

1. **Given** a claim that passed through Phase 2 cleaning with a recorded correction, **When** the audit log is queried for that claim, **Then** the correction (original/cleaned value, quality issue) appears as an audit entry, sourced from Phase 2's own `QualityIssueRecord` — not re-derived independently.
2. **Given** an incident that went through investigation, accept, remediation, and revalidation, **When** the audit log is queried for that incident, **Then** every one of those stages appears as a distinct, chronologically-ordered entry, each referencing the specific upstream record (Phase 11's `LLMInvestigation` id, Phase 12's `IncidentStatusTransition` id, Phase 13's `RemediationAction` ids, Phase 14's `RevalidationRun` id).
3. **Given** the audit log, **When** inspected for any entry, **Then** every entry is sourced from (references, not duplicates) the owning phase's own persisted record — this feature aggregates and indexes, it never becomes a second, independently-writable source of truth for facts other modules already own.

---

### User Story 2 - Expose `/history` and `/baseline` read endpoints (Priority: P1)

As a reviewer or downstream consumer, I need dedicated `/history` and `/baseline` read endpoints, so I have a stable, documented way to retrieve audit history and baseline information without needing to know which internal module owns each underlying record.

**Why this priority**: Equal priority — MVP_CONTEXT.md explicitly names these two endpoints as this phase's deliverable; they're the concrete, user-facing surface of Story 1's aggregated audit capability plus a stable read path to Phase 4's baseline data.

**Independent Test**: Can be tested by calling `/history` for a known claim/incident and `/baseline` for the current baseline, confirming both return real, correctly-sourced data matching what Story 1's underlying aggregation produces and what Phase 4 actually computed.

**Acceptance Scenarios**:

1. **Given** a claim or incident identifier, **When** `/history` is called, **Then** it returns the complete, chronologically-ordered audit trail for that identifier, aggregating across every pipeline stage per Story 1.
2. **Given** no specific baseline version requested, **When** `/baseline` is called, **Then** it returns Phase 4's current `BaselineSnapshot` (the same data `GET /baseline` in Phase 4 already exposes) — this feature's `/baseline` endpoint is either a direct pass-through/alias to Phase 4's existing endpoint or a documented equivalent, never a second independently-computed baseline.
3. **Given** a specific baseline snapshot identifier, **When** `/baseline` is called with it, **Then** it returns that specific historical snapshot (using Phase 4's existing `GET /baseline/history` provenance), supporting audit questions like "what baseline was in effect when this incident was scored."

---

### User Story 3 - Guarantee audit completeness — no pipeline stage can silently skip logging (Priority: P2)

As the person accountable for this project's audit-trail promise, I need assurance that every pipeline stage that produces a decision, score, or action actually contributes to the audit log — not just that the log looks complete for the specific fixtures already tested — so a newly-added or modified pipeline stage can't silently bypass auditing.

**Why this priority**: This is a completeness/regression-prevention guarantee layered on top of Stories 1-2's core capability — important for long-term trustworthiness, but the aggregation/endpoint capability (Stories 1-2) delivers the primary user value first, hence P2.

**Independent Test**: Can be tested by enumerating every module identified in MVP_CONTEXT.md Section 3's "Backend architecture" list as producing a decision/score/action, and confirming each one has a corresponding audit-log source integration in this feature — with a test that fails if a new pipeline-stage module is added without a corresponding audit source being registered.

**Acceptance Scenarios**:

1. **Given** the full list of pipeline-stage modules from MVP_CONTEXT.md Section 3 (`data_engineering`, `quality`, `baseline`, `features`, `anomaly`, `risk`, `llm`, `incidents`, `hitl`, `remediation`, `revalidation`, `ingestion`), **When** this feature's audit-source registry is inspected, **Then** every module that produces a decision/score/action (i.e., all except pure feature-computation modules with no decision output) has a registered audit source.
2. **Given** a hypothetical new pipeline stage added without registering an audit source, **When** the completeness test runs, **Then** it fails explicitly, flagging the gap — rather than the audit log silently missing that stage's entries forever.

### Edge Cases

- What happens when a claim/incident's audit trail spans a baseline recomputation (Phase 4/15) that changed the baseline mid-lifecycle? The audit trail MUST show which baseline snapshot was in effect at each stage that used one, not just "the current baseline," so history remains accurate even as the baseline evolves.
- What happens when an audit query is made for a claim/incident identifier that doesn't exist or has no recorded activity? The system MUST return a clear "no history found" response, not an empty-but-ambiguous 200 OK that could be mistaken for "confirmed zero activity."
- What happens if two pipeline stages' timestamps are extremely close together (e.g., automated recalculation firing multiple sub-steps within the same second)? The audit trail MUST preserve a stable, deterministic ordering (e.g., a monotonic sequence number in addition to timestamp) so history is never ambiguous about which event happened first.
- What happens to audit history when a claim is affected by remediation from one incident and separately referenced by a different, unrelated incident? The audit trail for each incident MUST correctly scope to its own relevant stages without conflating the two incidents' histories.
- What happens if this feature's aggregation query becomes slow as pipeline history grows (many batches via Phase 15 over time)? The system MUST support paginated/filtered history queries (e.g., by date range or stage) rather than requiring every query to return an unbounded full history.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST aggregate audit-relevant records from every pipeline-stage module (Phase 2's `QualityIssueRecord`, Phase 3's `ExpectationCheckResult`, Phase 7's anomaly scores, Phase 9's risk scores, Phase 10's Severity/Business Impact/Priority results, Phase 11's `LLMInvestigation`, Phase 12's `IncidentStatusTransition`/`HumanFeedback`, Phase 13's `RemediationAction`/`ManualActionRequired`, Phase 14's `RevalidationRun`/`BeforeAfterComparison`/`ResolutionDetermination`, Phase 15's `IngestedBatch`) into one queryable audit trail, by reference to each owning module's own persisted record — never by independently re-deriving or duplicating the underlying fact.
- **FR-002**: System MUST expose a `GET /history` endpoint that returns the complete, chronologically-ordered audit trail for a given claim or incident identifier.
- **FR-003**: System MUST expose a `GET /baseline` endpoint that returns Phase 4's current baseline (or, given a specific snapshot identifier, that specific historical baseline snapshot via Phase 4's existing provenance) — as a pass-through/alias to Phase 4's own data, never a second independently-computed baseline.
- **FR-004**: System MUST preserve a stable, deterministic ordering for audit entries (a monotonic sequence in addition to timestamp) so near-simultaneous events are never ambiguously ordered.
- **FR-005**: System MUST record which specific baseline snapshot was in effect for any audit entry that depended on baseline comparison, so history remains accurate as baselines evolve (Phase 4/15).
- **FR-006**: System MUST return a clear, distinguishable "no history found" response for a claim/incident identifier with no recorded activity, distinct from a confirmed-empty result.
- **FR-007**: System MUST support paginated and/or filtered history queries (by date range and/or pipeline stage) rather than only unbounded full-history retrieval.
- **FR-008**: System MUST maintain an audit-source registry enumerating every pipeline-stage module expected to contribute audit entries, and MUST provide a completeness check that fails explicitly if a module producing decisions/scores/actions has no registered audit source.
- **FR-009**: System MUST NOT allow direct external writes to the aggregated audit trail — every entry originates only from its owning module's own persistence, never from a caller-supplied audit record via this feature's own API.

### Key Entities

- **AuditTrailEntry**: One normalized, aggregated record — `entity_type` (claim/incident/batch), `entity_id`, `pipeline_stage`, `source_module`, `source_record_id` (reference, not copy), `sequence_number`, `occurred_at`, `baseline_snapshot_id_used` (if applicable).
- **AuditSourceRegistryEntry**: One registered pipeline-stage module and the specific record type(s) it contributes to the audit trail.
- **HistoryQueryResult**: The paginated/filtered response to a `/history` query — matching `AuditTrailEntry` records plus pagination metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a fixture claim/incident run through the full pipeline, 100% of the stages it actually passed through appear as distinct `AuditTrailEntry` records in correct chronological order.
- **SC-002**: 100% of `AuditTrailEntry` records reference their owning module's actual persisted record (verified by a provenance test) — zero independently-duplicated facts.
- **SC-003**: `GET /baseline` returns data identical to Phase 4's own `GET /baseline` for the same snapshot — verified by a direct comparison test.
- **SC-004**: 100% of near-simultaneous audit entries (a fixture with two events in the same millisecond) retain a stable, deterministic order across repeated queries.
- **SC-005**: The audit-source completeness check (FR-008) fails when a test deliberately registers a new mock pipeline-stage module without an audit source, proving the guarantee is enforced, not just documented.
- **SC-006**: A history query with no matching activity returns a distinguishable "no history found" response, and a paginated query with a date-range filter returns only entries within that range, verified by dedicated tests.

## Assumptions

- This feature is purely a read/aggregation layer over every prior phase's own persisted audit-relevant records — it introduces no new write path for pipeline facts, consistent with constitution Principle VI's modular ownership (each module owns its own data; this feature only indexes/aggregates for read access).
- "Every pipeline stage" (FR-001) excludes purely internal computation modules with no decision/score/action output of their own (e.g., Phase 1's profiling, Phase 5's feature engineering, Phase 6's feature selection) — these feed into stages that do produce audited decisions (quality, anomaly, risk, incidents, etc.) rather than being separately audited themselves, consistent with FR-008's "modules producing decisions/scores/actions" framing.
- This feature completes the MVP's Phase 1-17 build order (Phases 18-22 are explicitly deferred per MVP_CONTEXT.md Section 5) — it does not depend on or anticipate frontend (Phase 18), CI/CD (Phase 20), cloud deployment (Phase 21), or monitoring (Phase 22) capabilities.
