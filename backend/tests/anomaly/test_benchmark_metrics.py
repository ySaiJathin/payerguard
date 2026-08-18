import numpy as np
import pandas as pd

from app.anomaly.benchmark import run_benchmark
from app.anomaly.schemas import InjectionType, ModelType
from app.features.selection.temporal_split import compute_temporal_split

N_DAYS = 300


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


def test_every_result_has_all_five_injection_type_keys_and_measurement_context(tmp_path):
    matrix = _matrix()
    split = compute_temporal_split(matrix["CLM_FROM_DT"])

    run_result = run_benchmark(
        matrix=matrix, split=split, out_dir=tmp_path / "reports", model_out_dir=tmp_path / "models"
    )

    assert {r.model_type for r in run_result.benchmark_results} == set(ModelType)
    expected_keys = {t.value for t in InjectionType}
    for result in run_result.benchmark_results:
        assert set(result.per_injection_type_breakdown.keys()) == expected_keys
        assert result.measurement_context.hardware
        assert result.measurement_context.python_version
        assert result.measurement_context.run_timestamp is not None

    assert run_result.production_model_selection.selected_model in {r.model_type for r in run_result.benchmark_results}


def test_rerunning_the_same_benchmark_reproduces_identical_metrics(tmp_path):
    matrix = _matrix()
    split = compute_temporal_split(matrix["CLM_FROM_DT"])

    run_1 = run_benchmark(matrix=matrix, split=split, out_dir=tmp_path / "r1", model_out_dir=tmp_path / "m1")
    run_2 = run_benchmark(matrix=matrix, split=split, out_dir=tmp_path / "r2", model_out_dir=tmp_path / "m2")

    results_1 = {r.model_type: r for r in run_1.benchmark_results}
    results_2 = {r.model_type: r for r in run_2.benchmark_results}

    for model_type in ModelType:
        r1, r2 = results_1[model_type], results_2[model_type]
        assert r1.precision == r2.precision
        assert r1.recall == r2.recall
        assert r1.f1 == r2.f1
        assert r1.fpr == r2.fpr
        assert r1.per_injection_type_breakdown == r2.per_injection_type_breakdown

    assert run_1.production_model_selection.selected_model == run_2.production_model_selection.selected_model
