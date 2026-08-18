"""Pydantic models for feature selection.

See specs/006-feature-selection/data-model.md for field definitions and
validation rules.
"""

from datetime import date, datetime

from pydantic import BaseModel


class DateRange(BaseModel):
    start: date
    end: date


class TemporalSplit(BaseModel):
    split_id: str
    train_date_range: DateRange
    validation_date_range: DateRange
    test_date_range: DateRange
    train_count: int
    validation_count: int
    test_count: int
    computed_at: datetime
    sample_size_warning: str | None = None


class FeatureDropDecision(BaseModel):
    feature_name: str
    stage: int
    reason: str
    statistic_value: float | None = None
    stage_computed_on: str


class SelectedFeatureSet(BaseModel):
    version_id: str
    features: list[str]
    split_id: str
    target_used_for_stage3: str
    stage1_drop_count: int
    stage2_drop_count: int
    stage3_drop_count: int
    generated_at: datetime
