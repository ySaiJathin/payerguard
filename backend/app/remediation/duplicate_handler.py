"""Duplicate-flagging handler (spec FR-001, FR-006).

Matches a claim already flagged as a full-row duplicate by Phase 2's
detection (data_engineering/duplicate_detection.py) and marks it. The
mark is a fixed constant, never an invented value -- flagging a
known-duplicate row doesn't require deciding *what* value to write, only
*that* the row is flagged.
"""

from app.remediation.schemas import AffectedClaimInput, RemediationRule

DUPLICATE_FLAGGED_MARKER = "DUPLICATE_FLAGGED"


def matches(claim: AffectedClaimInput, rule: RemediationRule) -> bool:
    return claim.is_duplicate is True


# Re-verification at execution time (FR-006) re-runs the identical check
# -- the precondition here is simply "is this claim still flagged as a
# duplicate right now", so selection-time and apply-time use the same
# function.
verify_precondition = matches


def apply(claim: AffectedClaimInput, rule: RemediationRule) -> tuple[str | None, str]:
    return (None, DUPLICATE_FLAGGED_MARKER)
