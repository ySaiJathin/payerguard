import numpy as np
from sklearn.metrics import roc_auc_score

from app.risk.benchmark.benchmark_runner import run_benchmark
from app.risk.benchmark.calibration import brier_score
from app.risk.benchmark.data_loading import build_benchmark_frame
from tests.risk.benchmark._fixtures import make_rows, make_split


def test_every_model_reports_a_numeric_calibration_score(tmp_path):
    rows = make_rows(n_days=100, seed=4)
    split = make_split(n_days=100)

    frame = build_benchmark_frame(rows=rows, split=split)
    results, _warning = run_benchmark(frame, model_out_dir=tmp_path)

    assert len(results) == 3
    for result in results:
        assert isinstance(result.calibration_brier_score, float)
        assert 0.0 <= result.calibration_brier_score <= 1.0


def test_brier_score_exposes_a_calibration_gap_hidden_by_equal_discrimination():
    # Two prediction sets that rank identically (same ROC-AUC, i.e. same
    # discrimination) but one is systematically overconfident -- Brier
    # score must differ, proving the calibration gap is visible rather
    # than masked by a discrimination-only metric (spec Acceptance
    # Scenario 2).
    y_true = np.array([0, 0, 0, 1, 1, 1])
    well_calibrated = np.array([0.10, 0.20, 0.30, 0.60, 0.75, 0.90])
    overconfident = np.array([0.01, 0.02, 0.03, 0.97, 0.98, 0.99])

    assert roc_auc_score(y_true, well_calibrated) == roc_auc_score(y_true, overconfident)

    calibrated_brier = brier_score(y_true, well_calibrated)
    overconfident_brier = brier_score(y_true, overconfident)
    assert overconfident_brier != calibrated_brier
