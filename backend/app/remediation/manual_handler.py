"""Manual Action Required fallback (spec FR-004, FR-009).

Not a "handler" in the sense of the three deterministic remediation
handlers -- this is the explicit, traceable escalation path for any
affected-claim condition none of them can apply to (no matching rule, a
precondition that no longer holds, or a cross-incident claim conflict),
so nothing is ever silently skipped or guessed at.
"""

from datetime import datetime, timezone
from uuid import uuid4

from app.remediation.schemas import ManualActionRequired, ReasonCode


def flag_manual_action(
    incident_id: str, claim_id: str, reason_code: ReasonCode, description: str
) -> ManualActionRequired:
    return ManualActionRequired(
        record_id=str(uuid4()),
        incident_id=incident_id,
        claim_id=claim_id,
        description=description,
        reason_code=reason_code,
        flagged_at=datetime.now(timezone.utc),
    )
