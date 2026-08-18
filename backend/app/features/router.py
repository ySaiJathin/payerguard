"""Feature engineering's external API surface.

Endpoints per specs/005-feature-engineering/contracts/api.md.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.baseline.window_definition import DEFAULT_WINDOW_DEFINITION
from app.features import features_log
from app.features.features_service import FeaturesInputUnavailableError, compute_features
from app.features.schemas import ClaimFeatures, FeaturesComputeResult, WindowFeatures
from app.features.window_level.deviation_features import WindowDefinitionMismatchError

router = APIRouter(prefix="/features", tags=["features"])


class ComputeRequest(BaseModel):
    window_definition: str = DEFAULT_WINDOW_DEFINITION


class AnomalyCountUpdate(BaseModel):
    anomaly_count: int


@router.post("/compute", response_model=FeaturesComputeResult)
def compute(request: ComputeRequest | None = None) -> FeaturesComputeResult:
    window_definition = (request or ComputeRequest()).window_definition
    try:
        claim_features, window_features = compute_features(window_definition)
    except (FeaturesInputUnavailableError, WindowDefinitionMismatchError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    features_log.write_claim_features(claim_features)
    features_log.write_window_features(window_features)

    return FeaturesComputeResult(
        claims_processed=len(claim_features),
        windows_processed=len(window_features),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/claims", response_model=list[ClaimFeatures] | ClaimFeatures)
def get_claims(claim_id: str | None = None):
    rows = features_log.read_claim_features()
    if claim_id is None:
        return rows
    for row in rows:
        if row.claim_id == claim_id:
            return row
    raise HTTPException(status_code=404, detail=f"No ClaimFeatures found for claim_id={claim_id!r}")


@router.get("/windows", response_model=list[WindowFeatures])
def get_windows() -> list[WindowFeatures]:
    return features_log.read_window_features()


@router.patch("/windows/{window_id}/anomaly-count", response_model=WindowFeatures)
def update_anomaly_count(window_id: str, request: AnomalyCountUpdate) -> WindowFeatures:
    try:
        return features_log.update_window_anomaly_count(window_id, request.anomaly_count)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
