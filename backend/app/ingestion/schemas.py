"""Pydantic models for batch file ingestion.

See specs/017-batch-file-ingestion/data-model.md for field definitions
and validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class BatchStatus(str, Enum):
    rejected = "rejected"
    accepted = "accepted"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class RejectionReasonCode(str, Enum):
    wrong_delimiter = "wrong_delimiter"
    missing_columns = "missing_columns"
    unexpected_columns = "unexpected_columns"
    empty_file = "empty_file"
    below_min_rows = "below_min_rows"
    above_max_size = "above_max_size"
    unparseable = "unparseable"


class BatchUploadRejection(BaseModel):
    batch_id: str
    reason_code: RejectionReasonCode
    detail: str


class IngestedBatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: str
    filename: str
    stored_path: str | None = None
    uploaded_at: datetime
    row_count: int | None = None
    status: BatchStatus
    rejection_reason: BatchUploadRejection | None = None
    pipeline_stage_reached: str | None = None
    quality_result_id: str | None = None
    anomaly_result_id: str | None = None
    risk_result_id: str | None = None
    incident_ids: list[str] = []


class BatchListing(BaseModel):
    batches: list[IngestedBatch]
    page: int
    page_size: int
    total_count: int
