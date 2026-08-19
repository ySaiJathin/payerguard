"""The demo pipeline's model contracts: leakage, banding, and end-to-end shape."""

import numpy as np
import pandas as pd
import pytest

from app.data_engineering.dtype_conversion import load_column_categories
from app.demo import anomaly_runner, batches, risk_model
from app.demo.generator import NO_INJECTION
from app.demo.schemas import SubScores


@pytest.fixture(scope="module")
def categories() -> dict:
    return load_column_categories()


@pytest.fixture(scope="module")
def batch_one():
    return batches.load_batch("batch-1")


# --------------------------------------------------------------------------
# Isolation Forest
# --------------------------------------------------------------------------


def test_training_split_never_contains_an_injected_row(batch_one, categories, monkeypatch):
    """The stated constraint, asserted from outside the module: whatever
    `fit` is handed must be entirely clean."""
    df, labels = batch_one
    seen: list[pd.DataFrame] = []
    original = anomaly_runner.IsolationForestDetector.fit

    def spy(self, frame):
        seen.append(frame)
        return original(self, frame)

    monkeypatch.setattr(anomaly_runner.IsolationForestDetector, "fit", spy)
    anomaly_runner.fit_and_evaluate(df, labels, categories)

    assert seen, "IsolationForest.fit was never called"
    for frame in seen:
        assert (labels.reindex(frame.index) == NO_INJECTION).all()


def test_evaluation_covers_every_injected_row(batch_one, categories):
    df, labels = batch_one
    evaluation, _flags = anomaly_runner.fit_and_evaluate(df, labels, categories)
    assert evaluation.injected_eval_rows == int((labels != NO_INJECTION).sum())


def test_every_injection_type_gets_a_reported_breakdown(batch_one, categories):
    df, labels = batch_one
    evaluation, _flags = anomaly_runner.fit_and_evaluate(df, labels, categories)
    expected = set(labels.unique()) - {NO_INJECTION}
    assert set(evaluation.per_injection_type) == expected


def test_metrics_are_in_range_and_self_consistent(batch_one, categories):
    df, labels = batch_one
    evaluation, _flags = anomaly_runner.fit_and_evaluate(df, labels, categories)
    for value in (evaluation.precision, evaluation.recall, evaluation.f1, evaluation.fpr):
        assert 0.0 <= value <= 1.0
    if evaluation.precision + evaluation.recall > 0:
        expected_f1 = (
            2 * evaluation.precision * evaluation.recall / (evaluation.precision + evaluation.recall)
        )
        assert evaluation.f1 == pytest.approx(expected_f1, abs=1e-9)


def test_feature_matrix_separates_each_failure_mode(batch_one, categories):
    """Each injection type must move at least one feature away from normal --
    otherwise the detector has no dimension that could isolate it."""
    df, labels = batch_one
    matrix = anomaly_runner.build_feature_matrix(df, categories)
    clean = matrix.loc[labels == NO_INJECTION]

    expectations = {
        "missing_value_spike": anomaly_runner.ROW_MISSING_FEATURE,
        "duplicate_spike": anomaly_runner.DUPLICATE_FEATURE,
        "amount_spike": anomaly_runner.AMOUNT_DEVIATION_FEATURE,
    }
    for injection_type, feature in expectations.items():
        rows = labels.index[labels == injection_type]
        if len(rows) == 0:
            continue
        assert matrix.loc[rows, feature].median() > clean[feature].median(), feature


# --------------------------------------------------------------------------
# XGBoost risk model
# --------------------------------------------------------------------------


def test_severity_bands_match_the_documented_thresholds():
    assert risk_model.severity_band(100.0) == "CRITICAL"
    assert risk_model.severity_band(80.1) == "CRITICAL"
    assert risk_model.severity_band(80.0) == "HIGH"
    assert risk_model.severity_band(60.1) == "HIGH"
    assert risk_model.severity_band(60.0) == "MEDIUM"
    assert risk_model.severity_band(30.1) == "MEDIUM"
    assert risk_model.severity_band(30.0) == "LOW"
    assert risk_model.severity_band(0.0) == "LOW"


def test_label_weights_form_a_distribution_over_every_feature():
    assert set(risk_model.LABEL_WEIGHTS) == set(risk_model.FEATURE_ORDER)
    assert sum(risk_model.LABEL_WEIGHTS.values()) == pytest.approx(1.0)


def test_risk_prediction_is_bounded_and_monotone_in_the_signals():
    quiet = SubScores(**{name: 0.0 for name in risk_model.FEATURE_ORDER})
    severe = SubScores(**{name: 100.0 for name in risk_model.FEATURE_ORDER})
    scores = risk_model.predict_risk([quiet, severe])
    assert all(0.0 <= score <= 100.0 for score in scores)
    assert scores[0] < scores[1]


def test_the_model_tracks_its_own_documented_formula():
    """The score on the dashboard is a real prediction, but it must not have
    drifted away from the formula it was trained on."""
    rng = np.random.default_rng(3)
    features = rng.uniform(0.0, 100.0, size=(200, len(risk_model.FEATURE_ORDER)))
    expected = risk_model.rule_label(features)
    predicted = risk_model.predict_risk(
        [SubScores(**dict(zip(risk_model.FEATURE_ORDER, row))) for row in features]
    )
    assert np.abs(np.array(predicted) - expected).mean() < 3.0


def test_sub_scores_are_relative_to_the_batch_baseline(batch_one, categories):
    """A window identical to the batch it came from carries no excess risk."""
    df, labels = batch_one
    flags = pd.Series(False, index=df.index)
    context = risk_model.build_batch_context(df, categories, flags)
    scores = risk_model.compute_sub_scores(df, flags, context)
    assert scores.missing_data_risk == 0.0
    assert scores.null_risk == 0.0
    assert scores.anomaly_risk == 0.0
