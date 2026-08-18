import pickle

from app.risk.benchmark.benchmark_runner import run_benchmark
from app.risk.benchmark.data_loading import FEATURE_COLUMNS, build_benchmark_frame
from app.risk.benchmark.schemas import ModelType
from tests.risk.benchmark._fixtures import make_rows, make_split


def _load_all_artifacts(model_out_dir) -> dict:
    return {
        model_type.value: pickle.loads((model_out_dir / f"{model_type.value}.pkl").read_bytes())
        for model_type in ModelType
    }


def test_corrupting_test_split_portion_does_not_change_fitted_hyperparameters(tmp_path):
    rows = make_rows(n_days=100, seed=1)
    split = make_split(n_days=100)

    frame = build_benchmark_frame(rows=rows, split=split)
    baseline_out = tmp_path / "baseline_models"
    run_benchmark(frame, model_out_dir=baseline_out)
    baseline_artifacts = _load_all_artifacts(baseline_out)

    corrupted_rows = []
    for row in rows:
        if split.test_date_range.start <= row.window_start <= split.test_date_range.end:
            update = {
                c: getattr(row, c) + 1_000_000.0
                for c in FEATURE_COLUMNS
                if c not in ("claim_count", "gx_failure_count")
            }
            corrupted_rows.append(row.model_copy(update=update))
        else:
            corrupted_rows.append(row)

    corrupted_frame = build_benchmark_frame(rows=corrupted_rows, split=split)
    corrupted_out = tmp_path / "corrupted_models"
    run_benchmark(corrupted_frame, model_out_dir=corrupted_out)
    corrupted_artifacts = _load_all_artifacts(corrupted_out)

    X_train, _y_train = frame.train
    for model_type in ModelType:
        baseline = baseline_artifacts[model_type.value]
        corrupted = corrupted_artifacts[model_type.value]
        assert corrupted["candidate"]["hyperparameters"] == baseline["candidate"]["hyperparameters"], model_type.value

        # Train is untouched by the corruption, so predictions on train
        # should be exactly reproduced if fitting truly never saw the
        # corrupted test-split rows.
        baseline_preds = baseline["model"].predict_proba(X_train)[:, 1]
        corrupted_preds = corrupted["model"].predict_proba(X_train)[:, 1]
        assert (baseline_preds == corrupted_preds).all(), model_type.value
