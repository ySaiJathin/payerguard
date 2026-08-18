"""Orchestrates one investigation attempt: build prompt -> call Mistral ->
validate response -> persist result (spec FR-002 through FR-007, FR-009).

**Read-only boundary (spec FR-005, FR-009; research.md)**: this module,
and everything it imports, has zero import-time dependency on `app.
incidents` or `app.remediation`'s write-capable functions -- it only
imports its own `llm` module's persistence and pure evidence/response
helpers. This is a structural guarantee enforced by
`tests/llm/test_write_access_boundary.py`'s static import-graph check,
not just a comment: even a successfully prompt-injected Mistral response
telling this service to "delete all claims" has no write-capable code
path here to call, no matter what the response text says.
"""

from datetime import datetime, timezone
from uuid import uuid4

from app.llm import investigation_log, mistral_client, payload_builder, prompt_templates, response_parser
from app.llm.errors import MalformedResponseError, MistralAPIError
from app.llm.schemas import FailureType, InvestigationFailure, LLMInvestigation, StructuredIncidentPayload


def investigate(
    incident_id: str,
    payload: StructuredIncidentPayload,
    mistral_client_override=None,
    model_version: str = mistral_client.DEFAULT_MODEL,
) -> LLMInvestigation:
    evidence_snapshot_id = payload_builder.compute_evidence_snapshot_id(payload)
    prompt = prompt_templates.build_investigation_prompt(payload)

    try:
        draft = mistral_client.call_mistral(prompt, client=mistral_client_override, model=model_version)
        validated_draft, insufficient_evidence = response_parser.validate_and_tag(draft)
    except (MistralAPIError, MalformedResponseError) as exc:
        failure_type = FailureType.malformed_response if isinstance(exc, MalformedResponseError) else FailureType.api_error
        failure = InvestigationFailure(
            failure_id=str(uuid4()),
            incident_id=incident_id,
            failure_type=failure_type,
            error_detail=str(exc),
            occurred_at=datetime.now(timezone.utc),
        )
        investigation_log.append_failure(failure)
        raise

    investigation = LLMInvestigation(
        investigation_id=str(uuid4()),
        incident_id=incident_id,
        evidence_snapshot_id=evidence_snapshot_id,
        summary=validated_draft.summary,
        likely_root_cause=validated_draft.likely_root_cause,
        insufficient_evidence=insufficient_evidence,
        evidence=validated_draft.evidence,
        business_impact_narrative=validated_draft.business_impact_narrative,
        recommended_fix=validated_draft.recommended_fix,
        prevention_recommendation=validated_draft.prevention_recommendation,
        model_version=model_version,
        generated_at=datetime.now(timezone.utc),
    )
    investigation_log.append_investigation(investigation)
    return investigation
