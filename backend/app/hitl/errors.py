"""Error types for the HITL accept/reject/recalculate state machine."""


class InvalidTransitionError(ValueError):
    """Raised when an action isn't a legal move from an incident's current
    status (spec FR-007, SC-003, SC-006) -- maps to `409 Conflict`."""


class MissingFeedbackError(ValueError):
    """Raised when a reject action is attempted without non-empty
    `feedback_text` (spec FR-003, SC-002) -- maps to `422 Unprocessable
    Entity`. A reject is structurally impossible without feedback."""
