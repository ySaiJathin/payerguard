"""Loads Phase 8's risk dataset and Phase 6's temporal split, assigns every
row to train/validation/test using Phase 6's exact boundaries (never
recomputing or reshuffling -- spec FR-002), and builds the numeric
feature matrix + label vector each model type consumes.

**Feature columns**: the 8 raw signal columns on `RiskDatasetRow`
(`claim_count`, `gx_failure_count`, `anomaly_score`, `anomaly_frequency`,
`affected_claim_pct`, `volume_deviation`, `amount_deviation`,
`historical_quality_failure_rate`) -- deliberately excluding
`investigation_risk_indicator`. That field is the exact weighted
composite Phase 8's `InvestigationRiskLabelFormula` thresholds to produce
`investigation_risk_label` (`label = 1 iff IRI >= threshold`); including
it as a model input would let any classifier trivially reproduce the
label by learning a single-feature threshold rule instead of benchmarking
real predictive signal from the underlying quality/anomaly/deviation
measurements.

**Versioning**: Phase 8 stamps no version identifier on the persisted
risk dataset, so `risk_dataset_version` here is a SHA-256 hash of the
rows' own content (each row's JSON representation, sorted by
`window_id`) -- a stable, non-invasive versioning key computed without
modifying Phase 8 (spec FR-009): identical rows always hash identically
regardless of how they were loaded, and any real content change (Phase 15
adding data, or a label recompute) changes the hash.
"""

import hashlib
import json

import pandas as pd

from app.features.selection.schemas import TemporalSplit
from app.features.selection.temporal_split import assign_split, read_temporal_split
from app.risk.benchmark.errors import InsufficientClassDiversityError, RiskModelInputUnavailableError
from app.risk.dataset.dataset_log import read_risk_dataset_rows
from app.risk.dataset.label_distribution import compute_label_distribution
from app.risk.dataset.schemas import RiskDatasetRow

FEATURE_COLUMNS = [
    "claim_count",
    "gx_failure_count",
    "anomaly_score",
    "anomaly_frequency",
    "affected_claim_pct",
    "volume_deviation",
    "amount_deviation",
    "historical_quality_failure_rate",
]
LABEL_COLUMN = "investigation_risk_label"


class BenchmarkFrame:
    """One (X, y) pair per split, plus versioning/context metadata shared
    by every model type this benchmark run fits."""

    def __init__(
        self,
        splits: dict[str, tuple[pd.DataFrame, pd.Series]],
        risk_dataset_version: str,
        split: TemporalSplit,
        label_distribution_context: dict,
    ):
        self.splits = splits
        self.risk_dataset_version = risk_dataset_version
        self.split = split
        self.label_distribution_context = label_distribution_context

    @property
    def train(self) -> tuple[pd.DataFrame, pd.Series]:
        return self.splits["train"]

    @property
    def validation(self) -> tuple[pd.DataFrame, pd.Series]:
        return self.splits["validation"]

    @property
    def test(self) -> tuple[pd.DataFrame, pd.Series]:
        return self.splits["test"]


def _rows_to_frame(rows: list[RiskDatasetRow]) -> pd.DataFrame:
    records = [
        {"window_start": r.window_start, **{c: getattr(r, c) for c in FEATURE_COLUMNS}, LABEL_COLUMN: r.investigation_risk_label}
        for r in rows
    ]
    return pd.DataFrame.from_records(records)


def _dataset_hash(rows: list[RiskDatasetRow]) -> str:
    payload = json.dumps(
        sorted((json.loads(r.model_dump_json()) for r in rows), key=lambda r: r["window_id"]),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_benchmark_frame(
    rows: list[RiskDatasetRow] | None = None, split: TemporalSplit | None = None, out_dir=None
) -> BenchmarkFrame:
    if rows is None:
        rows = read_risk_dataset_rows(out_dir)
    if not rows:
        raise RiskModelInputUnavailableError(
            "No Phase 8 risk dataset found -- run POST /risk/dataset/build first."
        )

    if split is None:
        split = read_temporal_split()
    if split is None:
        raise RiskModelInputUnavailableError("No Phase 6 temporal split found -- run POST /features/split first.")

    df = _rows_to_frame(rows)
    df["split_name"] = df["window_start"].apply(lambda d: assign_split(d, split))

    splits: dict[str, tuple[pd.DataFrame, pd.Series]] = {}
    for name in ("train", "validation", "test"):
        portion = df.loc[df["split_name"] == name]
        splits[name] = (portion[FEATURE_COLUMNS], portion[LABEL_COLUMN])

    train_labels = splits["train"][1]
    if train_labels.nunique() < 2:
        raise InsufficientClassDiversityError(
            f"Train-split rows contain only {train_labels.nunique()} distinct "
            "investigation_risk_label class(es) -- cannot fit a classifier."
        )

    risk_dataset_version = _dataset_hash(rows)
    label_distribution_context = compute_label_distribution(
        [{"investigation_risk_label": r.investigation_risk_label, "claim_count": r.claim_count} for r in rows]
    ).model_dump()

    return BenchmarkFrame(
        splits=splits,
        risk_dataset_version=risk_dataset_version,
        split=split,
        label_distribution_context=label_distribution_context,
    )
