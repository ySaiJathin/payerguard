# Phase 0 Research: Remediation Engine

## Decision: Rule tables as versioned YAML config, loaded at service start, not database rows

**Decision**: The three rule tables live as YAML files under `backend/app/remediation/config/`, each with a `version` field, loaded once at service startup (or on-demand with an explicit reload endpoint for admin use) rather than as mutable database rows editable at runtime.

**Rationale**: FR-001 requires "versioned, reviewable configuration" — a file under version control is directly reviewable via normal code-review/PR process (matching this project's spec-driven-development workflow), which is a stronger "reviewed before use" guarantee than a database row an admin could edit without any review trail. This keeps rule-table changes subject to the same git history/audit trail as the rest of the codebase.

**Alternatives considered**: Database-backed rule tables with an admin UI (rejected for MVP — adds an editing surface and its own audit-trail requirements that MVP_CONTEXT.md doesn't call for; the Edge Cases note explicitly places "who approves changes to them" outside this feature's scope, and file-based config with git review is the simplest mechanism consistent with that).

## Decision: Precedence order — duplicate flagging first, then status mapping, then imputation

**Decision**: When multiple handlers could plausibly apply to the same affected-claim condition, `precedence.py` applies duplicate-flagging first (a duplicate row is the most unambiguous, lowest-risk correction), then approved status mapping (a known code-level correction), then approved imputation last (imputation is the most invasive of the three, since it fills in a value rather than correcting/flagging an existing one).

**Rationale**: This ordering reflects increasing "invasiveness"/risk of the action — flagging is non-destructive and easily reversible, status mapping changes a single categorical field to a known-correct value, imputation fills a genuine gap and is the handler most likely to be wrong if applied under an ambiguous condition. Applying the least invasive fix first, and only reaching for imputation when nothing less invasive applies, is a defensible, explainable default.

**Alternatives considered**: Alphabetical/arbitrary ordering (rejected — spec explicitly requires a *documented, non-arbitrary* precedence, and an invasiveness-based ordering is directly justifiable, unlike an alphabetical one); configurable precedence per rule table (considered as a future refinement — the fixed three-tier ordering above is simpler and sufficient for the MVP's three fixed handler types).

## Decision: Idempotency via a `RemediationAction` existence check keyed on `(incident_id, claim_id, rule_id)`

**Decision**: Before applying any handler, `remediation_service.py` checks whether a `RemediationAction` already exists for the exact `(incident_id, claim_id, rule_id)` triple; if so, it skips re-applying that specific action (but still re-verifies/records any other affected claims/conditions on the same incident that haven't yet been handled).

**Rationale**: This is the simplest correct idempotency key — re-running remediation on a partially-completed incident (e.g., after a crash mid-run) resumes rather than restarts, and never double-applies a specific already-completed action (spec FR-008, SC-005).

**Alternatives considered**: A single incident-level "already remediated" flag that skips the entire run if any action was ever taken (rejected — too coarse; would prevent completing remaining unhandled claims after a partial failure, contradicting the spirit of resumability).

## Decision: Cross-incident claim conflict detected via an active-remediation lock per claim

**Decision**: Before applying any handler to a claim, `remediation_service.py` checks whether that claim already has an in-progress or very-recently-applied `RemediationAction` from a *different* incident; if so, it raises a documented conflict (`ManualActionRequired` with reason `"concurrent_incident_conflict"`) rather than proceeding.

**Rationale**: Directly satisfies FR-010 and the spec's Edge Cases requirement that a claim affected by multiple incidents not have remediation silently overwritten/interfered with — an explicit conflict marking keeps a human in the loop for the ambiguous case rather than guessing which incident's remediation should "win."

**Alternatives considered**: Allowing both incidents' remediation to apply in sequence with last-write-wins (rejected — could silently undo or conflict with the first incident's correction, exactly what the spec warns against); a global lock blocking all remediation until the conflict is manually resolved (rejected as overly broad — only the specific contested claim needs to pause, not every incident in the system).
