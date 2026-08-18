"""Assembles the `StructuredIncidentPayload` sent to Mistral (spec FR-001)
from already-resolved Phase 3/7/9/10 evidence values -- a pure function,
mirroring Phase 10's "take already-resolved inputs, never fetch your own
dependencies" pattern (research.md), since Phase 12's Incident store
doesn't exist yet to fetch evidence from.

Every `BusinessImpactResult` component with `status == "unavailable"` is
represented to the LLM as an explicit string (`"unavailable - {reason}"`),
never coerced to `0` or silently dropped from the payload (spec FR-001,
Edge Cases, data-model.md's validation rule) -- an LLM shown a bare `0`
for a genuinely-unmeasurable component would have no way to distinguish
it from a real measured zero, and could narrate a false "no impact"
finding.
"""

import hashlib
import json

from app.risk.scoring.schemas import BusinessImpactResult, SeverityResult
from app.llm.schemas import StructuredIncidentPayload


def _severity_business_impact_dict(
    severity_result: SeverityResult, business_impact_result: BusinessImpactResult
) -> dict:
    business_impact_components = {}
    for component in business_impact_result.components:
        if component.status == "computed":
            business_impact_components[component.name] = component.value
        else:
            business_impact_components[component.name] = f"unavailable - {component.reason}"

    return {
        "severity": severity_result.severity,
        "quality_failure_severity": severity_result.quality_failure_severity,
        "anomaly_magnitude_score": severity_result.anomaly_magnitude_score,
        "materiality_score": severity_result.materiality_score,
        "business_impact": business_impact_result.business_impact,
        "business_impact_components": business_impact_components,
        "has_unavailable_business_impact_components": business_impact_result.has_unavailable_components,
    }


def build_payload(
    incident_context: dict,
    quality_check_results: list[dict],
    anomaly_evidence: dict,
    risk_evidence: dict,
    severity_result: SeverityResult,
    business_impact_result: BusinessImpactResult,
    affected_claims_sample: list[dict] | None = None,
) -> StructuredIncidentPayload:
    return StructuredIncidentPayload(
        incident_context=incident_context,
        quality_evidence={"check_results": quality_check_results},
        anomaly_evidence=anomaly_evidence,
        risk_evidence=risk_evidence,
        severity_business_impact=_severity_business_impact_dict(severity_result, business_impact_result),
        affected_claims_sample=affected_claims_sample or [],
    )


def compute_evidence_snapshot_id(payload: StructuredIncidentPayload) -> str:
    """A deterministic hash of the payload's own content -- identical
    evidence always yields the same snapshot id, so a later reviewer can
    confirm two investigations were (or weren't) run against the same
    evidence, without this feature owning a separate versioning scheme
    (mirrors Phase 9's `risk_dataset_version` hashing pattern)."""
    payload_json = payload.model_dump_json()
    canonical = json.dumps(json.loads(payload_json), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
