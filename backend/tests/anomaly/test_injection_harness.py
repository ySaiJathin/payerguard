import numpy as np
import pandas as pd
import pytest

from app.anomaly.injection_harness import TrainSplitInjectionError, inject_all
from app.anomaly.schemas import InjectionType

N_ROWS = 40
FEATURE_COLUMNS = ["amount_col", "feature_b", "feature_c", "feature_d"]


def _matrix(n_rows: int = N_ROWS) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "amount_col": rng.normal(100, 10, n_rows),
            "feature_b": rng.normal(0, 1, n_rows),
            "feature_c": rng.normal(5, 2, n_rows),
            "feature_d": rng.normal(-3, 1, n_rows),
        },
        index=[f"C{i}" for i in range(n_rows)],
    )


def test_all_five_injection_types_produce_at_least_one_instance():
    matrix = _matrix()
    rng = np.random.default_rng(42)

    injected_df, ground_truth, instances = inject_all(matrix, FEATURE_COLUMNS, "validation", rng)

    types_present = {i.injection_type for i in instances}
    assert types_present == set(InjectionType)
    for injection_type in InjectionType:
        assert sum(1 for i in instances if i.injection_type == injection_type) >= 1

    assert (ground_truth == "anomaly").sum() >= len(InjectionType)
    assert set(ground_truth.index) == set(injected_df.index)


def test_injected_row_sets_are_pairwise_disjoint():
    matrix = _matrix()
    rng = np.random.default_rng(7)

    _injected_df, _ground_truth, instances = inject_all(matrix, FEATURE_COLUMNS, "test", rng)

    seen: set[str] = set()
    for instance in instances:
        rows = set(instance.affected_rows)
        assert not (rows & seen), f"row(s) {rows & seen} claimed by more than one injection instance"
        seen |= rows


def test_inject_all_rejects_train_split():
    matrix = _matrix()
    rng = np.random.default_rng(1)

    with pytest.raises(TrainSplitInjectionError):
        inject_all(matrix, FEATURE_COLUMNS, "train", rng)


def test_duplicate_spike_appends_rows_rather_than_mutating_originals():
    matrix = _matrix()
    rng = np.random.default_rng(3)

    injected_df, _ground_truth, instances = inject_all(matrix, FEATURE_COLUMNS, "validation", rng)

    duplicate_instances = [i for i in instances if i.injection_type == InjectionType.duplicate_spike]
    assert len(injected_df) == len(matrix) + len(duplicate_instances)
    for instance in duplicate_instances:
        assert instance.affected_rows[0] not in matrix.index
        assert instance.affected_rows[0] in injected_df.index
