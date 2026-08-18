"""Validates the content rules of an `InvestigationDraft` beyond what
Mistral's structured-output mode already guarantees (JSON shape), and
tags the insufficiency signal (spec FR-002, FR-003, FR-004; research.md).
"""

from app.llm.errors import MalformedResponseError
from app.llm.prompt_templates import INSUFFICIENCY_PHRASE
from app.llm.schemas import InvestigationDraft

_REQUIRED_FIELDS = (
    "summary",
    "likely_root_cause",
    "evidence",
    "business_impact_narrative",
    "recommended_fix",
    "prevention_recommendation",
)


def validate_and_tag(draft: InvestigationDraft) -> tuple[InvestigationDraft, bool]:
    empty_fields = [name for name in _REQUIRED_FIELDS if not getattr(draft, name).strip()]
    if empty_fields:
        raise MalformedResponseError(
            f"Mistral response is missing required section(s): {empty_fields} (spec FR-004)."
        )

    insufficient_evidence = INSUFFICIENCY_PHRASE.lower() in draft.likely_root_cause.lower()
    return draft, insufficient_evidence
