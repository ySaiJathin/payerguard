"""Pydantic models for the audit trail.

See specs/016-audit-history/data-model.md for field definitions and
validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class EntityType(str, Enum):
    claim = "claim"
    incident = "incident"
    batch = "batch"


class PipelineStage(str, Enum):
    cleaning = "cleaning"
    quality = "quality"
    anomaly = "anomaly"
    risk = "risk"
    severity_scoring = "severity_scoring"
    llm_investigation = "llm_investigation"
    incident_status = "incident_status"
    human_feedback = "human_feedback"
    remediation = "remediation"
    revalidation = "revalidation"
    # `ingestion` was deliberately absent through Phase 16 (continuous
    # ingestion was removed 2026-08-18 and `app/ingestion/` had no write
    # path to instrument). Spec 017-batch-file-ingestion built a real one
    # -- `app.ingestion.batch_service` now emits this stage for every
    # accepted and rejected upload -- so it is re-added here.
    ingestion = "ingestion"


class AuditTrailEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_id: str
    entity_type: EntityType
    entity_id: str
    pipeline_stage: PipelineStage
    source_module: str
    source_record_id: str
    baseline_snapshot_id_used: str | None = None
    sequence_number: int
    occurred_at: datetime


class AuditSourceRegistryEntry(BaseModel):
    module_name: str
    record_types_contributed: list[str]
    registered: bool


class HistoryQueryResult(BaseModel):
    entity_type: str
    entity_id: str
    entries: list[AuditTrailEntry]
    page: int
    page_size: int
    total_count: int
    # False only when the entity has NO audit history at all -- never for
    # a valid-but-empty page of a non-empty history (spec FR-006, SC-006).
    found: bool
