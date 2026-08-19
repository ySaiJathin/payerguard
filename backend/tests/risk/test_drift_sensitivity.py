"""Risk category / "drift sensitivity" (spec 015 FR-003, SC-002).

MVP_CONTEXT.md Phase 15 names "drift sensitivity" without defining it, so
this feature operationalizes it (research.md) as the concrete, testable
property: *the production risk model is not frozen* -- when the input
distribution genuinely shifts, its scores move measurably in response.

A model that returned near-identical scores regardless of input would
still pass Phase 9's discrimination and calibration checks on its own
test split while being useless for detecting the distributional change
Phase 21-style monitoring exists to catch. That gap is what this test
closes; it does not duplicate Phase 9's SC-001 (leakage), SC-005
(calibration), or SC-006 (split correctness).

Scope note (FR-008): this proves the *model* responds to drift. It is not
a drift-*detection* system (population stability index, monitoring
thresholds, alerting) -- MVP_CONTEXT.md assigns that to Phase 21, and
research.md records the decision to keep it out of scope here.

Data-scale note (FR-008): no persisted Phase 8 risk dataset or Phase 9
model artifact exists in this environment, so this test builds its own
fixture via `tests/risk/benchmark/_fixtures.py` (the same builders Phase
9's own benchmark tests use) rather than reading a production artifact.
The fixture is a window-per-day synthetic set, so "measurable" is defined
against that scale, not against real production volume.
"""

import numpy as np
import pandas as pd
import pytest

from app.risk.benchmark.data_loading import FEATURE_COLUMNS, build_benchmark_frame
from app.risk.benchmark.logistic import HYPERPARAMETER_GRID, build_model
from tests.risk.benchmark._fixtures import make_rows, make_split

N_DAYS = 100

# The drifted window's scores must differ from the undrifted window's by
# more than this, on average. Set well above floating-point noise but
# below the ~0.5 shift a genuinely responsive model shows on this
# fixture, so the test fails loudly if a future change flattens the
# model's response rather than passing on a technicality.
MIN_MEAN_SCORE_DELTA = 0.05

# Multipliers applied to the drift-bearing features. Large enough to sit
# well outside the fixture's historical range (mirroring Phase 7's
# "distribution shift" injection concept, per research.md), which is
# exactly the situation a drift check must not sleep through.
DRIFT_MULTIPLIER = 8.0
DRIFTED_FEATURES = ["anomaly_score", "anomaly_frequency", "volume_deviation", "amount_deviation"]


@pytest.fixture(scope="module")
def fitted_model_and_test_features():
    """Fits a production-representative risk model on the fixture's train
    split only -- never on the drifted data it is later asked to score,
    which would defeat the point."""
    rows = make_rows(n_days=N_DAYS, seed=4, separable=True)
    split = make_split(n_days=N_DAYS)
    frame = build_benchmark_frame(rows=rows, split=split)

    x_train, y_train = frame.train
    # Uses the module's own documented hyperparameter grid rather than an
    # invented value, so this test tracks the real candidate space Phase 9
    # tunes over.
    model = build_model(HYPERPARAMETER_GRID[1])
    model.fit(x_train, y_train)

    x_test, _y_test = frame.test
    assert not x_test.empty, "Fixture produced an empty test split -- cannot measure drift response."
    return model, x_test


def _drifted(x: pd.DataFrame) -> pd.DataFrame:
    drifted = x.copy()
    for column in DRIFTED_FEATURES:
        assert column in drifted.columns, f"{column} missing from risk FEATURE_COLUMNS: {FEATURE_COLUMNS}"
        drifted[column] = drifted[column] * DRIFT_MULTIPLIER
    return drifted


def test_risk_scores_shift_measurably_under_distribution_drift(fitted_model_and_test_features):
    """FR-003: the model is sensitive to genuine distributional change."""
    model, x_test = fitted_model_and_test_features

    baseline_scores = model.predict_proba(x_test)[:, 1]
    drifted_scores = model.predict_proba(_drifted(x_test))[:, 1]

    mean_delta = float(np.mean(np.abs(drifted_scores - baseline_scores)))
    assert mean_delta > MIN_MEAN_SCORE_DELTA, (
        f"Risk scores barely moved under a {DRIFT_MULTIPLIER}x distribution shift "
        f"(mean abs delta {mean_delta:.6f} <= {MIN_MEAN_SCORE_DELTA}). The model appears "
        f"insensitive to drift, which is the exact failure this test exists to catch."
    )


def test_unshifted_data_produces_identical_scores(fitted_model_and_test_features):
    """Guards the test above from being vacuous: confirms the score
    movement is caused by the drift specifically, not by nondeterminism
    in scoring. Without this, a model that returned random scores would
    also 'pass' the drift check."""
    model, x_test = fitted_model_and_test_features

    first = model.predict_proba(x_test)[:, 1]
    second = model.predict_proba(x_test.copy())[:, 1]

    assert np.allclose(first, second, rtol=1e-12, atol=1e-12), (
        "Scoring the same unshifted data twice produced different results -- the drift test's "
        "measured delta cannot be attributed to drift."
    )


def test_drift_direction_is_consistent_with_higher_risk_features(fitted_model_and_test_features):
    """The fixture's drifted features all correlate positively with the
    risk label (`_fixtures.make_rows(separable=True)` builds them that
    way), so inflating them should push scores up, not down. A model that
    moved strongly in the *wrong* direction would satisfy the magnitude
    check above while being clearly broken."""
    model, x_test = fitted_model_and_test_features

    baseline_mean = float(np.mean(model.predict_proba(x_test)[:, 1]))
    drifted_mean = float(np.mean(model.predict_proba(_drifted(x_test))[:, 1]))

    assert drifted_mean > baseline_mean, (
        f"Inflating positively-correlated risk features moved the mean score down "
        f"({baseline_mean:.6f} -> {drifted_mean:.6f}), the opposite of the expected direction."
    )
