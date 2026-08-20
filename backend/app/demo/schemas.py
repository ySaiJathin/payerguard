"""Pydantic models for the demo synthetic-data / simulator feature.

These are additive to the existing phase schemas -- nothing here replaces
`app/quality/schemas.py`, `app/anomaly/schemas.py` or
`app/risk/*/schemas.py`; the demo pipeline writes its real results back
through those same schemas so the dashboard keeps reading the endpoints it
already reads.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.anomaly.schemas import InjectionType
from app.llm.schemas import LLMInvestigation

__all__ = [
    "InjectionType",
    "InjectionCluster",
    "InjectionPlan",
    "BatchSpec",
    "BatchManifestEntry",
    "SubScores",
    "WindowRiskAssessment",
    "AnomalyEvaluation",
    "PipelineRunResult",
    "SimulationStartRequest",
    "SimulationStatus",
]


class InjectionCluster(BaseModel):
    """Several injection types landing inside one contiguous date block.

    A real bad ingestion is localised and usually breaks more than one
    thing at once, and a scoring window only reaches the upper severity
    bands when several signals fire together. Spreading injections evenly
    across the batch instead produces a row of indistinguishable
    middle-of-the-road windows, which is the opposite of a demo.
    """

    name: str
    rates: dict[InjectionType, float] = Field(default_factory=dict)
    # Share of the block's rows that are actually injected. 1.0 means the
    # whole block is corrupted; lower values interleave healthy claims.
    density: float = 1.0


class InjectionPlan(BaseModel):
    """How much of each anomaly type to inject into a batch, and where.

    `rates` is the background: each type gets its own contiguous block,
    sized so the block is `background_density` injected. `clusters` are the
    co-located hotspots. A type may appear in both -- its totals add up.
    Rates are fractions of the batch's claim count and every target row is
    drawn from a disjoint pool, so a row carries at most one label.
    """

    rates: dict[InjectionType, float] = Field(default_factory=dict)
    clusters: list[InjectionCluster] = Field(default_factory=list)
    background_density: float = 0.7

    def total_rate(self) -> float:
        total = sum(self.rates.values())
        for cluster in self.clusters:
            total += sum(cluster.rates.values())
        return total


class BatchSpec(BaseModel):
    """A reproducible recipe for one synthetic batch."""

    batch_id: str
    label: str
    description: str
    claim_count: int
    start_date: str
    end_date: str
    seed: int
    # Multiplicative reshaping of the amount distribution relative to the
    # real source profile: scale moves the centre, spread widens/narrows
    # the log-normal sigma. 1.0/1.0 reproduces the source shape.
    amount_scale: float = 1.0
    amount_spread: float = 1.0
    # Extra structural degradation applied on top of the source profile's
    # own natural missingness, as percentage points.
    extra_missing_pct: float = 0.0
    duplicate_rate: float = 0.0
    injection_plan: InjectionPlan = Field(default_factory=InjectionPlan)


class BatchManifestEntry(BaseModel):
    batch_id: str
    label: str
    description: str
    file: str
    ground_truth_file: str
    rows: int
    claims: int
    injected_rows: int
    injected_counts: dict[str, int]
    date_from: str
    date_to: str
    clm_pmt_amt_sum: float
    clm_pmt_amt_median: float
    duplicate_rows: int
    missing_cell_pct: float
    generated_at: datetime
    spec: BatchSpec


class SubScores(BaseModel):
    """The distinct risk signal types fed to the XGBoost risk model.

    Every field is a 0-100 sub-score computed from real per-window
    measurements -- see `app/demo/risk_model.py` for how each is derived.
    """

    missing_data_risk: float
    null_risk: float
    duplicate_risk: float
    sla_timeliness_risk: float
    range_risk: float
    dtype_risk: float
    validity_risk: float
    uniqueness_risk: float
    freshness_risk: float
    anomaly_risk: float


class AnomalyEvaluation(BaseModel):
    model_type: str = "isolation_forest"
    train_rows: int
    eval_rows: int
    injected_eval_rows: int
    precision: float
    recall: float
    f1: float
    fpr: float
    per_injection_type: dict[str, dict[str, float]]
    threshold: float
    detection_latency_ms: float
    execution_time_s: float
    feature_columns: list[str]
    parameters: dict


class WindowRiskAssessment(BaseModel):
    window_id: str
    window_start: str
    window_end: str
    claim_count: int
    sub_scores: SubScores
    risk_score: float
    severity_band: str
    anomaly_claim_count: int
    dominant_injection_type: str | None
    affected_claim_pct: float
    affected_claims_amounts: list[float]
    anomaly_score_percentile: float
    quality_check_bands: list[str]
    deviation_pct: float


class PipelineRunResult(BaseModel):
    run_id: str
    source: str
    batch_id: str
    batch_label: str
    injection_applied: bool
    rows: int
    claims: int
    quality_run_id: str
    quality_composite_score: float
    quality_band_counts: dict[str, int]
    quality_type_band_counts: dict[str, dict[str, int]]
    anomaly: AnomalyEvaluation
    risk_model_type: str = "xgboost"
    windows: list[WindowRiskAssessment]
    incident_ids: list[str]
    incident_severity_counts: dict[str, int]
    # The exact `LLMInvestigation` objects `narrative.to_investigation()`
    # produced and logged for each incident created in this run -- the same
    # object `GET /llm/investigations/{incident_id}` would return, captured
    # at creation time rather than regenerated, so there's no second call
    # needed and no risk of a duplicate/drifted copy (investigation_id is
    # assigned once, by `to_investigation`, and never regenerated here).
    investigations: list[LLMInvestigation] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime


class SimulationStartRequest(BaseModel):
    batch_id: str | None = None
    inject_anomalies: bool = False


class SimulationStatus(BaseModel):
    run_id: str
    batch_id: str
    batch_label: str
    inject_anomalies: bool
    state: str  # queued | ingesting | analyzing | complete | failed
    chunk_index: int
    chunk_total: int
    chunk_interval_seconds: float
    claims_ingested: int
    claims_total: int
    current_window: str | None
    message: str
    started_at: datetime
    updated_at: datetime
    result: PipelineRunResult | None = None
    error: str | None = None
