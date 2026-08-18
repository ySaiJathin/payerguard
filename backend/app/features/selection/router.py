"""Feature selection's external API surface.

Endpoints per specs/006-feature-selection/contracts/api.md, mounted on the
same `/features` prefix as Phase 5's `features_router`.
"""

from fastapi import APIRouter, HTTPException

from app.features.selection.drop_decision_log import read_drop_decisions, read_selected_feature_set
from app.features.selection.schemas import FeatureDropDecision, SelectedFeatureSet, TemporalSplit
from app.features.selection.selection_service import FeaturesInputUnavailableError, run_selection
from app.features.selection.stage1_structural import AllFeaturesDroppedError
from app.features.selection.temporal_split import (
    TemporalSplitInputUnavailableError,
    compute_and_persist_temporal_split,
    read_temporal_split,
)

router = APIRouter(prefix="/features", tags=["feature-selection"])


@router.post("/split", response_model=TemporalSplit)
def compute_split() -> TemporalSplit:
    existing = read_temporal_split()
    if existing is not None:
        return existing
    try:
        return compute_and_persist_temporal_split()
    except TemporalSplitInputUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/split", response_model=TemporalSplit)
def get_split() -> TemporalSplit:
    split = read_temporal_split()
    if split is None:
        raise HTTPException(status_code=404, detail="No TemporalSplit computed yet -- call POST /features/split first.")
    return split


@router.post("/select", response_model=SelectedFeatureSet)
def select() -> SelectedFeatureSet:
    try:
        return run_selection()
    except (FeaturesInputUnavailableError, AllFeaturesDroppedError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/selected", response_model=SelectedFeatureSet)
def get_selected() -> SelectedFeatureSet:
    feature_set = read_selected_feature_set()
    if feature_set is None:
        raise HTTPException(status_code=404, detail="No SelectedFeatureSet computed yet -- call POST /features/select first.")
    return feature_set


@router.get("/drop-decisions", response_model=list[FeatureDropDecision])
def get_drop_decisions(stage: int | None = None) -> list[FeatureDropDecision]:
    return read_drop_decisions(stage=stage)
