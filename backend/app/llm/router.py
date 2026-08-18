"""LLM investigation API endpoints.

Endpoints per specs/011-llm-investigation/contracts/api.md.
"""

from fastapi import APIRouter, HTTPException

from app.llm import investigation_log, investigation_service
from app.llm.errors import IncidentNotFoundError, MalformedResponseError, MistralAPIError
from app.llm.schemas import InvestigateRequest, InvestigationHistoryResponse, LLMInvestigation

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/investigate", response_model=LLMInvestigation)
def investigate(request: InvestigateRequest) -> LLMInvestigation:
    if request.structured_payload is None:
        # Phase 12's Incident store doesn't exist yet -- there is nothing
        # to resolve incident_id against (contracts/api.md's own Notes).
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown incident_id {request.incident_id!r} -- Phase 12's incident store isn't "
                "implemented yet. Supply structured_payload directly for pre-Phase-12 use."
            ),
        )

    try:
        return investigation_service.investigate(request.incident_id, request.structured_payload)
    except MistralAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except MalformedResponseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/investigations/{incident_id}", response_model=InvestigationHistoryResponse)
def get_investigations(incident_id: str) -> InvestigationHistoryResponse:
    investigations, failures = investigation_log.read_investigation_history(incident_id)
    return InvestigationHistoryResponse(investigations=investigations, failures=failures)
