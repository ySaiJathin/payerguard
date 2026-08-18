"""Pydantic models for the quality validation layer feature.

See specs/003-quality-validation-layer/data-model.md for field definitions
and validation rules.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.data_engineering.schemas import ColumnCategory

__all__ = [
    "ColumnCategory",
    "ExpectationType",
    "Band",
    "ExpectationCheckResult",
    "QualityScoreResult",
    "CompletenessCalibrationEntry",
]


class ExpectationType(str, Enum):
    COMPLETENESS = "completeness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    DTYPE = "dtype"
    RANGE = "range"
    CODE_SET = "code_set"
    FRESHNESS = "freshness"
    MISSING_RATE = "missing_rate"
    DUPLICATE_RATE = "duplicate_rate"


class Band(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ExpectationCheckResult(BaseModel):
    check_id: str
    suite_name: str
    column_name: str | None = None
    expectation_type: ExpectationType
    computed_rate_or_count: float
    band: Band
    threshold_used: dict = Field(default_factory=dict)
    run_id: str
    evaluated_at: datetime


class QualityScoreResult(BaseModel):
    run_id: str
    batch_source: str
    composite_score: float = Field(ge=0, le=100)
    weights_used: dict[str, float]
    contributing_check_ids: list[str]
    generated_at: datetime


class CompletenessCalibrationEntry(BaseModel):
    column_name: str
    expected_max_missing_pct: float = Field(ge=0, le=100)
    source_note: str
