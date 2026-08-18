"""Historical baseline's external API surface.

Endpoints per specs/004-historical-baseline/contracts/api.md.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.baseline import snapshot_log
from app.baseline.schemas import BaselineSnapshot, BaselineSnapshotSummary
from app.baseline.snapshot_service import BaselineInputUnavailableError, compute_baseline_snapshot
from app.baseline.window_definition import DEFAULT_WINDOW_DEFINITION

router = APIRouter(prefix="/baseline", tags=["baseline"])


class ComputeRequest(BaseModel):
    window_definition: str = DEFAULT_WINDOW_DEFINITION


@router.post("/compute", response_model=BaselineSnapshot)
def compute(request: ComputeRequest | None = None) -> BaselineSnapshot:
    window_definition = (request or ComputeRequest()).window_definition
    try:
        snapshot = compute_baseline_snapshot(window_definition)
    except BaselineInputUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    snapshot_log.write_baseline_snapshot(snapshot)
    return snapshot


@router.get("", response_model=BaselineSnapshot)
def get_latest() -> BaselineSnapshot:
    snapshot = snapshot_log.read_latest_baseline_snapshot()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No baseline has been computed yet.")
    return snapshot


@router.get("/history", response_model=list[BaselineSnapshotSummary])
def get_history() -> list[BaselineSnapshotSummary]:
    return snapshot_log.read_baseline_history()
