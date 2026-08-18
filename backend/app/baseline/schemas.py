"""Pydantic models for the historical baseline feature.

See specs/004-historical-baseline/data-model.md for field definitions and
validation rules. No field anywhere in this module may be named or
semantically equivalent to "processing time", "SLA", or "turnaround"
(spec FR-006, SC-005) -- length-of-stay is the duration signal instead.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

__all__ = [
    "Percentiles",
    "VolumeWindow",
    "VolumeBaseline",
    "AmountBaseline",
    "DataHealthBaseline",
    "LengthOfStayBaseline",
    "SourceDateRange",
    "BaselineSnapshot",
    "BaselineSnapshotSummary",
]


class Percentiles(BaseModel):
    p25: float
    p50: float
    p75: float
    p95: float
    p99: float


class VolumeWindow(BaseModel):
    window_id: str
    start: date
    end: date
    claim_count: int = Field(ge=0)


class VolumeBaseline(BaseModel):
    window_definition: str
    windows: list[VolumeWindow]


class AmountBaseline(BaseModel):
    column_name: str
    mean: float
    median: float
    std: float
    min: float
    max: float
    percentiles: Percentiles


class DataHealthBaseline(BaseModel):
    historical_missing_rate_by_column: dict[str, float]
    historical_duplicate_rate: float
    categorical_distributions: dict[str, dict[str, int]]


class LengthOfStayBaseline(BaseModel):
    mean: float
    median: float
    percentiles: Percentiles
    claims_included: int = Field(ge=0)
    claims_excluded_missing_dates: int = Field(ge=0)


class SourceDateRange(BaseModel):
    min_date: date
    max_date: date


class BaselineSnapshot(BaseModel):
    snapshot_id: str
    source_file: str
    source_row_count: int = Field(ge=0)
    source_date_range: SourceDateRange
    volume_baseline: VolumeBaseline
    amount_baselines: list[AmountBaseline]
    data_health_baseline: DataHealthBaseline
    length_of_stay_baseline: LengthOfStayBaseline
    computed_at: datetime


class BaselineSnapshotSummary(BaseModel):
    """Provenance-only projection of BaselineSnapshot for GET /baseline/history."""

    snapshot_id: str
    source_file: str
    source_row_count: int = Field(ge=0)
    computed_at: datetime
