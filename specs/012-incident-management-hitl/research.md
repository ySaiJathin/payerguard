# Phase 0 Research: Incident Management & Human-in-the-Loop

## Decision: Explicit finite state machine for incident status, not a free-text status field

**Decision**: `state_machine.py` defines incident status as an enum (`pending_investigation`, `ready_for_review`, `accepted`, `rejected`, and reserved-but-not-yet-used `resolved`/`reopened` for Phase 14) with an explicit transition table (`{from_status: {action: to_status}}`), and every accept/reject/recalculate action is validated against this table before applying.

**Rationale**: FR-007/SC-003/SC-006 require invalid transitions to be explicitly rejected, not silently allowed — a free-text or loosely-typed status field makes this hard to guarantee; an explicit transition table makes illegal transitions a validation error by construction. FR-008's extensibility requirement is satisfied by reserving `resolved`/`reopened` in the enum now, even though Phase 13/14 will be the first features to actually trigger transitions into them.

**Alternatives considered**: Boolean flags (`is_accepted`, `is_rejected`) instead of a single status enum (rejected — allows contradictory states like both flags true, which a single enum with a transition table structurally prevents).

## Decision: Recalculation re-invokes Phase 11 unconditionally, and re-invokes Phase 10 scoring only if upstream evidence changed

**Decision**: `recalculation_service.py` always calls Phase 11's `POST /llm/investigate` again (a reviewer may want a fresh LLM read regardless), but only re-invokes Phase 10's scoring functions if a check against the incident's stored evidence snapshot shows the underlying Phase 3/4/7/9 data has actually changed since the snapshot was taken — and records explicitly which happened (`evidence_changed: true/false`) so the system never claims evidence changed when it didn't (spec Edge Cases).

**Rationale**: Directly satisfies the spec's edge case requirement; also avoids wastefully re-running Phase 10's arithmetic (cheap, but re-running it should still reflect reality, not be triggered by convention alone).

**Alternatives considered**: Always re-running the full Phase 10 scoring pipeline on every recalculation regardless of whether evidence changed (rejected — technically harmless since Phase 10's functions are pure/idempotent, but would make the `evidence_changed` flag meaningless/always-true, undermining the spec's explicit requirement that the system "MUST NOT claim the evidence changed if it didn't").

## Decision: `HumanFeedback` persistence has zero import-time dependency on Phase 7/9's model-fitting code

**Decision**: `reject_service.py` and its `HumanFeedback` persistence path do not import anything from `app.anomaly.benchmark` or `app.risk.benchmark`'s fitting functions — feedback is written to the `human_feedback` table and nothing else happens automatically.

**Rationale**: Mirrors Phase 11's read-only enforcement pattern (research.md decision on import-graph isolation) — the strongest guarantee that "no automatic retraining from a single event" (FR-006, SC-005) holds is that the code path to trigger retraining simply isn't reachable from feedback capture, not just that nothing currently calls it by convention.

**Alternatives considered**: A feature flag / config check gating auto-retraining (rejected as the sole mechanism — a flag can be flipped by mistake; import-graph isolation is a stronger structural guarantee, consistent with how Phase 11 handled the equivalent write-access risk).

## Decision: Minimal reviewer attribution via a passed-in identifier field, no auth system

**Decision**: Accept/reject/feedback actions accept a `reviewer_id` (or `reviewer_name`) string field in the request body, stored on the resulting `IncidentStatusTransition`/`HumanFeedback` records, without validating it against any authentication system.

**Rationale**: MVP_CONTEXT.md Section 4 doesn't define a multi-tenant/user-auth model for this MVP; the spec's Assumptions section explicitly defers a full auth system. A passed-in identifier is the minimal viable way to satisfy "timestamped and attributed to the acting reviewer" (FR-002) without inventing scope MVP_CONTEXT.md doesn't call for.

**Alternatives considered**: A hardcoded single "system reviewer" identity (rejected — would make multi-reviewer feedback history, which SC-002/FR-004 require preserving distinctly, indistinguishable between different actual reviewers); building a full auth system now (rejected — clear scope creep beyond what MVP_CONTEXT.md defines for this MVP).
