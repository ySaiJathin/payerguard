"""Synthetic anomaly-injection harness (spec FR-004, FR-005, FR-006).

Applied only to copies of the validation/test splits -- `inject_all` raises
if ever called with `split_name="train"`, a structural guard backing FR-005
(the training data this benchmark fits models on must stay byte-identical
to Phase 6's train portion throughout).

Per research.md's "one combined copy per split" decision, `inject_all`
applies all five injection types to disjoint row subsets of a single working
copy of the given split's matrix, rather than five separate copies -- one
evaluation pass per model per split, with every injected instance still
traceable to its exact `injection_type` via `InjectedAnomalyInstance`.
"""

from uuid import uuid4

import numpy as np
import pandas as pd

from app.anomaly.schemas import InjectedAnomalyInstance, InjectionType

AMOUNT_LIKE_SUBSTRINGS = ("amt", "amount", "pmt", "chrg", "charge", "payment")
MISSING_VALUE_COLUMN_FRACTION = 0.5
AMOUNT_SPIKE_FACTOR = 50.0
DISTRIBUTION_SHIFT_N_FEATURES = 3
DISTRIBUTION_SHIFT_N_STD = 6.0
VOLUME_DROP_MARGIN_FACTOR = 3.0

N_INJECTION_TYPES = 5


class TrainSplitInjectionError(ValueError):
    """Raised if `inject_all` is ever called with `split_name='train'`
    (spec FR-005) -- the injection harness must never touch training data."""


def _new_instance(
    injection_type: InjectionType, split: str, rows: list[str], columns: list[str]
) -> InjectedAnomalyInstance:
    return InjectedAnomalyInstance(
        synthetic_instance_id=str(uuid4()),
        injection_type=injection_type,
        split=split,
        affected_rows=[str(r) for r in rows],
        affected_columns=list(columns),
    )


def inject_missing_value_spike(
    df: pd.DataFrame, feature_columns: list[str], row_ids: list, split: str, rng: np.random.Generator
) -> tuple[pd.DataFrame, list[InjectedAnomalyInstance]]:
    """Nulls out a random subset of feature values on each targeted row."""
    df = df.copy()
    instances = []
    n_cols = max(1, int(len(feature_columns) * MISSING_VALUE_COLUMN_FRACTION))
    n_cols = min(n_cols, len(feature_columns))
    for row_id in row_ids:
        affected_cols = list(rng.choice(feature_columns, size=n_cols, replace=False))
        df.loc[row_id, affected_cols] = np.nan
        instances.append(_new_instance(InjectionType.missing_value_spike, split, [row_id], affected_cols))
    return df, instances


def inject_amount_spike(
    df: pd.DataFrame,
    feature_columns: list[str],
    row_ids: list,
    split: str,
    rng: np.random.Generator,
    factor: float = AMOUNT_SPIKE_FACTOR,
) -> tuple[pd.DataFrame, list[InjectedAnomalyInstance]]:
    """Multiplies an amount-like numeric feature by a large factor on each
    targeted row; falls back to any numeric feature if no amount-like
    column name is present in the selected feature set."""
    df = df.copy()
    amount_cols = [c for c in feature_columns if any(s in c.lower() for s in AMOUNT_LIKE_SUBSTRINGS)]
    candidate_cols = amount_cols or feature_columns
    instances = []
    for row_id in row_ids:
        col = str(rng.choice(candidate_cols))
        current = df.loc[row_id, col]
        base = 1.0 if pd.isna(current) or current == 0 else float(current)
        df.loc[row_id, col] = base * factor
        instances.append(_new_instance(InjectionType.amount_spike, split, [row_id], [col]))
    return df, instances


def inject_duplicate_spike(
    df: pd.DataFrame, feature_columns: list[str], row_ids: list, split: str, rng: np.random.Generator
) -> tuple[pd.DataFrame, list[InjectedAnomalyInstance]]:
    """Appends a near-duplicate row (new synthetic row id, copied feature
    values) for each targeted row -- the duplicate is the labeled anomaly,
    the original stays normal."""
    df = df.copy()
    instances = []
    new_rows = []
    for row_id in row_ids:
        duplicate = df.loc[row_id].copy()
        synthetic_id = f"SYN-DUP-{uuid4()}"
        duplicate.name = synthetic_id
        new_rows.append(duplicate)
        instances.append(_new_instance(InjectionType.duplicate_spike, split, [synthetic_id], feature_columns))
    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)])
    return df, instances


def inject_volume_drop(
    df: pd.DataFrame,
    feature_columns: list[str],
    row_ids: list,
    split: str,
    rng: np.random.Generator,
    train_bounds: dict[str, tuple[float, float]] | None = None,
) -> tuple[pd.DataFrame, list[InjectedAnomalyInstance]]:
    """Drives a targeted row's feature values to an extreme outlier of the
    train distribution -- a per-row proxy for what is naturally a
    window-level phenomenon (a claim characteristic of an abrupt local
    volume collapse), per research.md/plan.md."""
    df = df.copy()
    bounds = train_bounds or {}
    instances = []
    for row_id in row_ids:
        for col in feature_columns:
            lo, hi = bounds.get(col, (df[col].min(), df[col].max()))
            lo = 0.0 if pd.isna(lo) else float(lo)
            hi = 0.0 if pd.isna(hi) else float(hi)
            span = max(abs(hi - lo), 1.0)
            extreme = lo - VOLUME_DROP_MARGIN_FACTOR * span if rng.random() < 0.5 else hi + VOLUME_DROP_MARGIN_FACTOR * span
            df.loc[row_id, col] = extreme
        instances.append(_new_instance(InjectionType.volume_drop, split, [row_id], feature_columns))
    return df, instances


def inject_distribution_shift(
    df: pd.DataFrame,
    feature_columns: list[str],
    row_ids: list,
    split: str,
    rng: np.random.Generator,
    train_std: dict[str, float] | None = None,
    n_features: int = DISTRIBUTION_SHIFT_N_FEATURES,
    n_std: float = DISTRIBUTION_SHIFT_N_STD,
) -> tuple[pd.DataFrame, list[InjectedAnomalyInstance]]:
    """Shifts several numeric features by several train-standard-deviations
    in a consistent direction on each targeted row."""
    df = df.copy()
    std_map = train_std or {}
    n_features = min(n_features, len(feature_columns))
    shift_cols = list(rng.choice(feature_columns, size=n_features, replace=False))
    direction = 1.0 if rng.random() < 0.5 else -1.0
    instances = []
    for row_id in row_ids:
        for col in shift_cols:
            std = std_map.get(col) or df[col].std() or 1.0
            if pd.isna(std) or std == 0:
                std = 1.0
            current = df.loc[row_id, col]
            base = 0.0 if pd.isna(current) else float(current)
            df.loc[row_id, col] = base + direction * n_std * std
        instances.append(_new_instance(InjectionType.distribution_shift, split, [row_id], shift_cols))
    return df, instances


def inject_all(
    matrix: pd.DataFrame,
    feature_columns: list[str],
    split_name: str,
    rng: np.random.Generator,
    train_bounds: dict[str, tuple[float, float]] | None = None,
    train_std: dict[str, float] | None = None,
) -> tuple[pd.DataFrame, pd.Series, list[InjectedAnomalyInstance]]:
    """Applies all 5 injectors to disjoint row subsets of one copy of
    `matrix` (only ever a validation/test slice -- FR-004, FR-005, FR-006).

    Returns `(injected_df, ground_truth_labels, instances)` where
    `ground_truth_labels` is a Series indexed like `injected_df` with values
    `"normal"`/`"anomaly"`.
    """
    if split_name == "train":
        raise TrainSplitInjectionError(
            "inject_all must never be called with split_name='train' (spec FR-005) -- "
            "the injection harness only ever runs on validation/test copies."
        )

    row_ids = np.array(list(matrix.index), dtype=object)
    rng.shuffle(row_ids)
    chunks = [list(chunk) for chunk in np.array_split(row_ids, N_INJECTION_TYPES)]

    working = matrix.copy()
    all_instances: list[InjectedAnomalyInstance] = []

    working, instances = inject_missing_value_spike(working, feature_columns, chunks[0], split_name, rng)
    all_instances += instances
    working, instances = inject_amount_spike(working, feature_columns, chunks[1], split_name, rng)
    all_instances += instances
    working, instances = inject_duplicate_spike(working, feature_columns, chunks[2], split_name, rng)
    all_instances += instances
    working, instances = inject_volume_drop(working, feature_columns, chunks[3], split_name, rng, train_bounds)
    all_instances += instances
    working, instances = inject_distribution_shift(working, feature_columns, chunks[4], split_name, rng, train_std)
    all_instances += instances

    anomaly_rows: set[str] = set()
    for instance in all_instances:
        anomaly_rows.update(instance.affected_rows)

    ground_truth = pd.Series("normal", index=working.index, name="ground_truth_label")
    present_anomaly_rows = [r for r in anomaly_rows if r in ground_truth.index]
    ground_truth.loc[present_anomaly_rows] = "anomaly"

    return working, ground_truth, all_instances
