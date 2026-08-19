"""Approved-imputation handler (spec FR-001, FR-006).

Matches a claim whose named column is currently missing (`None`), and
fills it with the rule's pre-approved `to_value` -- a documented,
narrow sentinel/default, never a fabricated clinical guess (constitution
Principle II).
"""

from app.remediation.schemas import AffectedClaimInput, RemediationRule


def matches(claim: AffectedClaimInput, rule: RemediationRule) -> bool:
    column = rule.precondition["column"]
    return claim.fields.get(column) is None


# Re-verification at execution time (FR-006) re-runs the identical check
# -- if the claim's field has since been populated (e.g. a race with
# re-ingestion), this returns False and the caller falls back to Manual
# Action Required instead of overwriting a now-present value.
verify_precondition = matches


def apply(claim: AffectedClaimInput, rule: RemediationRule) -> tuple[None, str]:
    return (None, rule.to_value)
