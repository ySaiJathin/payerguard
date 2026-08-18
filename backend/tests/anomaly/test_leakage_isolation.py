import pickle

import numpy as np
import pandas as pd

from app.anomaly.benchmark import run_benchmark
from app.anomaly.schemas import ModelType
from app.features.selection.temporal_split import compute_temporal_split

N_DAYS = 300
FEATURE_COLUMNS = ["amount_col", "feature_b", "feature_c", "feature_d"]


def _matrix() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=N_DAYS, freq="D")
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "CLM_FROM_DT": dates,
            "amount_col": rng.normal(100, 10, N_DAYS),
            "feature_b": rng.normal(0, 1, N_DAYS),
            "feature_c": rng.normal(5, 2, N_DAYS),
            "feature_d": rng.normal(-3, 1, N_DAYS),
        },
        index=[f"C{i}" for i in range(N_DAYS)],
    )
    df.index.name = "CLM_ID"
    return df


def _load_all_artifacts(model_out_dir) -> dict:
    return {
        model_type.value: pickle.loads((model_out_dir / f"{model_type.value}.pkl").read_bytes())
        for model_type in ModelType
    }


def test_corrupting_test_split_portion_does_not_change_fitted_parameters_or_thresholds(tmp_path):
    matrix = _matrix()
    split = compute_temporal_split(matrix["CLM_FROM_DT"])

    baseline_reports = tmp_path / "baseline_reports"
    baseline_models = tmp_path / "baseline_models"
    run_benchmark(matrix=matrix, split=split, out_dir=baseline_reports, model_out_dir=baseline_models)
    baseline_artifacts = _load_all_artifacts(baseline_models)

    corrupted = matrix.copy()
    test_mask = corrupted["CLM_FROM_DT"] > pd.Timestamp(split.validation_date_range.end)
    assert test_mask.sum() > 0, "fixture must actually have rows in the test portion"
    corrupted.loc[test_mask, FEATURE_COLUMNS] = corrupted.loc[test_mask, FEATURE_COLUMNS] + 1_000_000.0

    corrupted_reports = tmp_path / "corrupted_reports"
    corrupted_models = tmp_path / "corrupted_models"
    run_benchmark(matrix=corrupted, split=split, out_dir=corrupted_reports, model_out_dir=corrupted_models)
    corrupted_artifacts = _load_all_artifacts(corrupted_models)

    for model_type in ModelType:
        baseline = baseline_artifacts[model_type.value]
        corrupted_artifact = corrupted_artifacts[model_type.value]
        assert corrupted_artifact["parameters"] == baseline["parameters"], model_type.value
        assert corrupted_artifact["calibrated_thresholds"] == baseline["calibrated_thresholds"], model_type.value
