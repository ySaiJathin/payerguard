"""Pydantic models for the remediation engine.

See specs/013-remediation-engine/data-model.md for field definitions and
validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class HandlerType(str, Enum):
    duplicate_flagging = "duplicate_flagging"
    approved_imputation = "approved_imputation"
    approved_status_mapping = "approved_status_mapping"


class ReasonCode(str, Enum):
    no_matching_rule = "no_matching_rule"
    precondition_invalidated = "precondition_invalidated"
    concurrent_incident_conflict = "concurrent_incident_conflict"


class RemediationRule(BaseModel):
    """One entry in a versioned rule table (config/*.yaml) -- the sole
    source of remediation decisions at execution time (spec FR-001,
    FR-005)."""

    rule_id: str
    handler_type: HandlerType
    precondition: dict
    to_value: str | float | None = None
    precedence_rank: int
    rule_table_version: str


class AffectedClaimInput(BaseModel):
    """Caller-supplied per-claim data for one affected claim of the
    incident being remediated. Phase 12's `Incident` has no persisted
    affected-claims list and no `claims` table exists yet (backend/app/
    models/claims.py is still a placeholder), so -- matching the
    established pattern of `EvidenceBundle` in incidents/schemas.py --
    the caller supplies the affected claims explicitly in the run
    request rather than remediation autonomously fetching them. Because
    remediation only ever iterates over the claims present here,
    FR-003's "never touch a claim outside the documented affected set"
    is structurally guaranteed by this request shape."""

    claim_id: str
    is_duplicate: bool = False
    fields: dict[str, str | float | None] = {}


class RemediationRunRequest(BaseModel):
    affected_claims: list[AffectedClaimInput]


class RemediationAction(BaseModel):
    """The record of one applied handler against one specific claim
    (spec data-model.md). Unique on (incident_id, claim_id, rule_id) --
    enforces idempotency (FR-008, SC-005)."""

    model_config = ConfigDict(from_attributes=True)

    action_id: str
    incident_id: str
    claim_id: str
    rule_id: str
    before_value: str | None
    after_value: str | None
    applied_at: datetime


class ManualActionRequired(BaseModel):
    """A record marking one specific affected-claim condition as
    unhandled -- why no handler applied (unmatched condition,
    invalidated precondition, or concurrent-incident conflict)."""

    model_config = ConfigDict(from_attributes=True)

    record_id: str
    incident_id: str
    claim_id: str
    description: str
    reason_code: ReasonCode
    flagged_at: datetime


class RemediationRun(BaseModel):
    """The aggregate result of one remediation execution against an
    accepted incident. Every affected claim appears in exactly one of
    `actions`/`manual_actions_required` for a completed run (FR-009,
    SC-003)."""

    run_id: str
    incident_id: str
    actions: list[RemediationAction]
    manual_actions_required: list[ManualActionRequired]
    started_at: datetime
    completed_at: datetime | None
