"""Error types for the revalidation engine."""


class IncompleteRemediationRunError(ValueError):
    """Raised when revalidation targets a `remediation_run_id` that either
    doesn't exist on the incident or hasn't finished (`completed_at` is
    still `None`) -- maps to `409 Conflict` (spec FR-009, SC-006).
    Revalidating a still-running/partial remediation would draw a
    premature conclusion from an incomplete before/after picture."""
