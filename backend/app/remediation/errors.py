"""Error types for the remediation engine."""


class NotAcceptedIncidentError(ValueError):
    """Raised when remediation is attempted against an incident whose
    status isn't "accepted" (spec FR-002, SC-002) -- maps to `409
    Conflict`. Remediation is structurally refused for every other
    status (pending_investigation, ready_for_review, rejected, ...);
    Phase 12's HITL accept is the sole authorization mechanism this
    engine checks before acting on an incident."""
