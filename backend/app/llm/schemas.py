"""Pydantic models for LLM investigation.

See specs/011-llm-investigation/data-model.md for field definitions and
validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class StructuredIncidentPayload(BaseModel):
    incident_context: dict
    quality_evidence: dict
    anomaly_evidence: dict
    risk_evidence: dict
    severity_business_impact: dict
    affected_claims_sample: list[dict] = []


class InvestigationDraft(BaseModel):
    """The six-section shape handed to Mistral's structured-output mode
    (`chat.parse(response_format=InvestigationDraft, ...)`) -- Mistral
    itself enforces this JSON shape; `response_parser.py` enforces the
    content rules (non-empty, insufficiency detection) a JSON schema
    alone can't express (research.md)."""

    summary: str
    likely_root_cause: str
    evidence: str
    business_impact_narrative: str
    recommended_fix: str
    prevention_recommendation: str


class LLMInvestigation(BaseModel):
    investigation_id: str
    incident_id: str
    evidence_snapshot_id: str
    summary: str
    likely_root_cause: str
    insufficient_evidence: bool
    evidence: str
    business_impact_narrative: str
    recommended_fix: str
    prevention_recommendation: str
    model_version: str
    generated_at: datetime


class FailureType(str, Enum):
    api_error = "api_error"
    timeout = "timeout"
    malformed_response = "malformed_response"


class InvestigationFailure(BaseModel):
    failure_id: str
    incident_id: str
    failure_type: FailureType
    error_detail: str
    occurred_at: datetime


class InvestigateRequest(BaseModel):
    """Request body for `POST /llm/investigate` (contracts/api.md).
    `structured_payload` is an additive, optional field beyond
    quickstart.md's bare `{"incident_id": ...}` example -- Phase 12's
    Incident store doesn't exist yet, so there is nothing to resolve
    `incident_id` against unless the caller supplies the payload directly
    (contracts/api.md's own Notes section anticipates exactly this)."""

    incident_id: str
    structured_payload: StructuredIncidentPayload | None = None


class InvestigationHistoryResponse(BaseModel):
    investigations: list[LLMInvestigation]
    failures: list[InvestigationFailure]
