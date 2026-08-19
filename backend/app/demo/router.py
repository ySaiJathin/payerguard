"""Demo feature API: batches, pipeline runs, the simulator, and upload.

Everything the Simulator page needs, and nothing the dashboard needs -- the
dashboard keeps reading `/quality/results`, `/baseline`, `/anomaly/results`
and `/incidents`, which this feature writes into.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.demo import batches, pipeline, simulator, upload
from app.demo.column_profile import DemoProfileUnavailableError
from app.demo.schemas import (
    BatchManifestEntry,
    PipelineRunResult,
    SimulationStartRequest,
    SimulationStatus,
)

router = APIRouter(prefix="/demo", tags=["demo"])

MAX_UPLOAD_BYTES = 64 * 1024 * 1024


@router.get("/batches", response_model=list[BatchManifestEntry])
def list_batches() -> list[BatchManifestEntry]:
    """The three synthetic batches, generating them on first call if the
    working copy has none yet."""
    try:
        return batches.ensure_generated()
    except DemoProfileUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/batches/regenerate", response_model=list[BatchManifestEntry])
def regenerate_batches() -> list[BatchManifestEntry]:
    """Reseeds all three batches from their specs. Deterministic: the same
    specs produce the same batches."""
    try:
        return batches.generate_all(force=True)
    except DemoProfileUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/pipeline/run", response_model=PipelineRunResult)
def run_pipeline_now(
    batch_id: str, inject_anomalies: bool = False, db: Session = Depends(get_db)
) -> PipelineRunResult:
    """Runs a batch through the whole pipeline synchronously, with no
    chunked ingestion -- the direct path, used to seed the dashboard."""
    try:
        return pipeline.run_batch(db, batch_id, inject_extra=inject_anomalies, source="batch")
    except batches.UnknownBatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/pipeline/runs", response_model=list[PipelineRunResult])
def pipeline_runs(limit: int = 25) -> list[PipelineRunResult]:
    """Every pipeline run this installation has performed, newest first --
    batches, simulator runs and uploads alike."""
    return list(reversed(pipeline.read_runs()))[:limit]


@router.post("/simulation/start", response_model=SimulationStatus)
def start_simulation(request: SimulationStartRequest) -> SimulationStatus:
    batch_id = request.batch_id or simulator.next_batch_id(None)
    try:
        return simulator.start(batch_id, request.inject_anomalies)
    except batches.UnknownBatchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/simulation/runs", response_model=list[SimulationStatus])
def simulation_runs() -> list[SimulationStatus]:
    return simulator.list_runs()


@router.get("/simulation/{run_id}", response_model=SimulationStatus)
def simulation_status(run_id: str) -> SimulationStatus:
    status = simulator.get_status(run_id)
    if status is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown simulation run {run_id!r}. Run state is held in process and is lost on "
                "restart; the run's results, if it completed, are in GET /demo/pipeline/runs."
            ),
        )
    return status


@router.post("/upload", response_model=PipelineRunResult)
async def upload_claims(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> PipelineRunResult:
    """Validates an uploaded claims file against the expected schema and,
    if it matches, runs it through the identical pipeline the synthetic
    batches use. A schema mismatch is a 422 naming what is wrong."""
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File is {len(content) / 1e6:.1f} MB; the limit is {MAX_UPLOAD_BYTES / 1e6:.0f} MB.",
        )
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")

    filename = file.filename or "upload.csv"
    try:
        frame, labels = upload.validate_and_load(content, filename)
    except upload.UploadSchemaError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    stored_name = upload.persist_upload(content, filename)
    return pipeline.run_pipeline(
        db,
        frame,
        labels,
        batch_id=stored_name,
        batch_label=f"Upload: {filename}",
        source="upload",
        injection_applied=False,
    )
