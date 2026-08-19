"""Explicit finite state machine for `Incident.status` (spec FR-007,
FR-008; research.md).

An explicit `{from_status: {action: {possible_to_statuses}}}` table, not
a free-text status field, makes an illegal transition (double-accept,
reject-after-accept, accepting a rejected incident without going through
recalculation first) a validation error by construction rather than
something each caller has to remember to check. `resolved`/`reopened`
were reserved from Phase 12 onward (no incoming transitions defined
there) specifically so Phase 14 (014-revalidation) could add its own
transition into these statuses later without a breaking redesign of this
table's shape (FR-008) -- `revalidation_result` below is that addition.

`revalidation_result` from `accepted` maps to *two* possible destinations
(`resolved` or `reopened`) for the same reason `recalculate` does above:
the actual outcome depends on a runtime call to 014's resolution
criteria, not something this static table alone can decide --
`validate_transition` only confirms the *action* is legal here; the
calling service (`app.revalidation.revalidation_service`) picks and
records which of the legal destinations actually applies. The same
action is legal again from `reopened` -- 014's spec Edge Cases
explicitly requires supporting re-revalidation after a reviewer applies
further manual fixes to a reopened incident (each such run is its own
distinct, timestamped `RevalidationRun`, never overwriting a prior one),
and spec Assumptions describe this feature's state-machine extension as
covering transitions "into/out of" `resolved`/`reopened`, not only into
them. `resolved` remains terminal (no outgoing transitions) -- nothing
in 014's spec requires reopening an already-resolved incident.

`recalculate` from `rejected` maps to *two* possible destinations
(`ready_for_review` if the new investigation succeeds, `pending_
investigation` if it fails again) because the actual outcome depends on
a runtime call to Phase 11, not something this static table alone can
decide -- `validate_transition` only confirms the *action* is legal here;
the calling service picks and records which of the legal destinations
actually applies.

**Known MVP limitation**: `pending_investigation` has no human-triggered
action defined (matching contracts/api.md's `recalculate` endpoint, which
is scoped strictly to `rejected` incidents per its own `409` condition).
An incident whose investigation fails at creation and is never rejected
has no path back to review in this feature -- a documented limitation,
not an oversight to silently work around by expanding the contract.
"""

from app.hitl.errors import InvalidTransitionError

TRANSITIONS: dict[str, dict[str, set[str]]] = {
    "pending_investigation": {},
    "ready_for_review": {
        "accept": {"accepted"},
        "reject": {"rejected"},
    },
    "accepted": {
        "revalidation_result": {"resolved", "reopened"},
    },
    "rejected": {
        "recalculate": {"ready_for_review", "pending_investigation"},
    },
    "resolved": {},
    "reopened": {
        "revalidation_result": {"resolved", "reopened"},
    },
}


def validate_transition(current_status: str, action: str) -> set[str]:
    """Returns the set of legal destination statuses for `action` from
    `current_status`. Raises `InvalidTransitionError` if `current_status`
    is unknown or `action` isn't legal from it."""
    if current_status not in TRANSITIONS:
        raise InvalidTransitionError(f"Unknown incident status: {current_status!r}")

    legal_actions = TRANSITIONS[current_status]
    if action not in legal_actions:
        raise InvalidTransitionError(
            f"Action {action!r} is not valid from status {current_status!r} "
            f"(legal actions here: {sorted(legal_actions) or 'none'})."
        )
    return legal_actions[action]
