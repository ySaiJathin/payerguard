"""Pydantic models for the feature engineering feature.

See specs/005-feature-engineering/data-model.md for field definitions and
validation rules. `WindowFeatures.anomaly_count` stays `None` until a
Phase 7/8 enrichment step populates it -- never a fabricated zero (spec
FR-008, SC-004).
"""

from datetime import date, datetime

from pydantic import BaseModel


class ClaimFeatures(BaseModel):
    claim_id: str
    payment_to_charge_ratio: float | None = None
    length_of_stay_days: int | None = None
    admission_day_of_week: int | None = None
    admission_month: int | None = None
    admission_year: int | None = None
    encoded_categoricals: dict[str, float | None] = {}
    provider_frequency: float | None = None


class AmountStats(BaseModel):
    mean: float
    median: float
    std: float


class WindowFeatures(BaseModel):
    window_id: str
    start: date
    end: date
    claim_count: int
    amount_stats: dict[str, AmountStats] = {}
    missing_pct: float
    duplicate_pct: float
    invalid_status_pct: float
    volume_deviation: float
    amount_deviation: dict[str, float] = {}
    anomaly_count: int | None = None


class EncodingScheme(BaseModel):
    column_name: str
    strategy: str
    fitted_categories: list[str]
    unseen_category_policy: str = "map_to_unknown_bucket"
    frequency_map: dict[str, float] = {}


class FeaturesComputeResult(BaseModel):
    claims_processed: int
    windows_processed: int
    generated_at: datetime
