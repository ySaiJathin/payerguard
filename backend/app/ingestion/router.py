"""POST /claims/upload and related ingestion endpoints.

Endpoints per specs/017-batch-file-ingestion/contracts/api.md.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.ingestion import batch_service, pipeline_runner, upload_validation
from app.ingestion.paths import batch_upload_path
from app.ingestion.schemas import BatchListing, IngestedBatch, RejectionReasonCode

router = APIRouter(prefix="/claims", tags=["ingestion"])

MAX_UPLOAD_BYTES = upload_validation.MAX_UPLOAD_BYTES


@router.post("/upload", response_model=IngestedBatch, status_code=201)
async def upload_claims(file: UploadFile = File(...), db: Session = Depends(get_db)) -> IngestedBatch:
    """Validates an uploaded file against the raw claims schema and, if it
    matches, runs it through the full existing pipeline (spec FR-001
    through FR-003). Every attempt -- accepted or rejected -- is tracked
    and audited (FR-004, FR-009)."""
    content = await file.read()
    filename = file.filename or "upload.csv"

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"{filename!r} is {len(content) / 1e6:.1f} MB; the limit is {MAX_UPLOAD_BYTES / 1e6:.0f} MB.",
        )

    try:
        frame, row_count = upload_validation.validate_and_load(content, filename)
    except upload_validation.UploadRejectionError as exc:
        rejected = batch_service.record_rejection(
            db, filename=filename, reason_code=RejectionReasonCode(exc.reason_code), detail=exc.detail
        )
        raise HTTPException(status_code=422, detail=rejected.model_dump(mode="json")) from exc

    # create_batch first (establishes batch_id + the FR-009 audit entry),
    # then persist the raw bytes at the path that id determines, then
    # record where they landed -- three small steps rather than guessing
    # a batch_id before it exists.
    batch = batch_service.create_batch(db, filename=filename, row_count=row_count)
    raw_path = batch_upload_path(batch.batch_id)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(raw_path, sep="|", index=False)
    batch_service.set_stored_path(db, batch.batch_id, str(raw_path))

    try:
        pipeline_runner.run(db, batch.batch_id, raw_path)
    except pipeline_runner.PipelineRunError:
        # The batch's own `status` (already set to `failed` by
        # pipeline_runner) is the honest signal -- the upload itself
        # still succeeded, so this is not surfaced as an HTTP error
        # (spec FR-007, contracts/api.md).
        pass

    result = batch_service.get_batch(db, batch.batch_id)
    return result


@router.get("/batches", response_model=BatchListing)
def list_batches(page: int = 1, page_size: int = 25, db: Session = Depends(get_db)) -> BatchListing:
    return batch_service.list_batches(db, page=page, page_size=page_size)


@router.get("/batches/{batch_id}", response_model=IngestedBatch)
def get_batch(batch_id: str, db: Session = Depends(get_db)) -> IngestedBatch:
    batch = batch_service.get_batch(db, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"Unknown batch_id: {batch_id}")
    return batch
