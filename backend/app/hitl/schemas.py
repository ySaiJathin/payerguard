"""Pydantic models for the HITL accept/reject/recalculate workflow.

See specs/012-incident-management-hitl/data-model.md for field
definitions and validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

from app.incidents.schemas import EvidenceBundle, Incident
from app.llm.schemas import LLMInvestigation


class ReasonCategory(str, Enum):
    incorrect_root_cause = "incorrect_root_cause"
    insufficient_evidence_disagreement = "insufficient_evidence_disagreement"
    false_positive = "false_positive"
    other = "other"


class AcceptRequest(BaseModel):
    reviewer_id: str


class RejectRequest(BaseModel):
    reviewer_id: str
    reason_category: ReasonCategory
    feedback_text: str

    @field_validator("feedback_text")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        # Belt-and-suspenders: reject_service.py enforces this too (the
        # structural guarantee FR-003 actually relies on), but failing
        # fast at the schema layer gives a clearer 422 for the common case.
        if not value.strip():
            raise ValueError("feedback_text must not be empty.")
        return value


class RecalculateRequest(BaseModel):
    """Optional -- omitting `new_evidence` means "recalculate with the
    incident's existing evidence" (evidence_changed will be False);
    additive beyond quickstart.md's bare example, matching 010/011's
    router request schemas."""

    new_evidence: EvidenceBundle | None = None


class HumanFeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feedback_id: str
    incident_id: str
    investigation_id: str
    reason_category: str
    feedback_text: str
    reviewer_id: str
    submitted_at: datetime


class IncidentStatusTransitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transition_id: str
    incident_id: str
    from_status: str
    to_status: str
    action: str
    reviewer_id: str | None
    occurred_at: datetime


class RecalculateResponse(BaseModel):
    incident: Incident
    new_investigation: LLMInvestigation | None
    evidence_changed: bool
