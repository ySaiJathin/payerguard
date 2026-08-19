"""Approved status-mapping handler (spec FR-001, FR-006).

Matches a claim whose named column currently holds the rule's
`from_value`, and maps it to the rule's `to_value` -- both values come
solely from the versioned rule table (config/status_mapping_rules.yaml),
never invented ad hoc.
"""

from app.remediation.schemas import AffectedClaimInput, RemediationRule


def matches(claim: AffectedClaimInput, rule: RemediationRule) -> bool:
    column = rule.precondition["column"]
    from_value = rule.precondition["from_value"]
    return claim.fields.get(column) == from_value


# Re-verification at execution time (FR-006) re-runs the identical check
# -- if the claim's field has since changed away from `from_value` (e.g.
# a race with re-ingestion), this returns False and the caller falls
# back to Manual Action Required instead of applying a stale mapping.
verify_precondition = matches


def apply(claim: AffectedClaimInput, rule: RemediationRule) -> tuple[str, str]:
    return (rule.precondition["from_value"], rule.to_value)
