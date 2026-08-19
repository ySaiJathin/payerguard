"""Anomaly category / "model stability" (spec 015 FR-002, SC-002).

MVP_CONTEXT.md Phase 15 names "model stability" without defining it
numerically, so this feature defines and documents a concrete, testable
interpretation (research.md): fit and score the same detector N times
against the same unchanged data and require the resulting scores to agree
within a documented tolerance. A model whose scores wander between
identical runs cannot support the reproducibility guarantees Phase 7's
benchmark and Phase 14's revalidation both depend on.

This extends -- rather than duplicates -- Phase 7's SC-003, which asserts
one benchmark run reproduces its own metrics. Stability here is the
stronger property: repeated *independent* fit/score cycles, constructed
from scratch each time, still agree.

Scope note (FR-008): no persisted production model artifact exists in this
environment (`data/` holds no `.pkl`, and `read_benchmark_run_result()`
returns None), so this test cannot read Phase 7's *selected* model and
instead covers all four detectors in `_DETECTOR_FACTORIES` directly.
That is strictly broader than testing whichever one was selected, so the
guarantee holds whichever model Phase 7 later promotes.
"""

import numpy as np
import pandas as pd
import pytest

from app.anomaly.benchmark import _DETECTOR_FACTORIES
from app.anomaly.schemas import ModelType

N_ROWS = 300
N_CYCLES = 5
FEATURE_COLUMNS = ["amount_col", "feature_b", "feature_c", "feature_d"]

# All four detectors are deterministic given identical input: IQR and HBOS
# are closed-form, Isolation Forest pins `random_state`, and LOF is a
# deterministic nearest-neighbour computation. So the tolerance is set at
# floating-point noise rather than a loose statistical band. If a future
# model with genuine run-to-run randomness is added to
# `_DETECTOR_FACTORIES`, it needs its own documented, wider tolerance here
# -- widening this one silently would hide a real stability regression in
# the existing four.
RELATIVE_TOLERANCE = 1e-9


def _data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """A fixed-seed synthetic matrix, mirroring the fixture style of
    `tests/anomaly/test_leakage_isolation.py`. The seed is fixed so the
    *input* is unchanged across cycles -- the whole point is to vary
    nothing and observe whether the model's output varies anyway."""
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "amount_col": rng.normal(100, 10, N_ROWS),
            "feature_b": rng.normal(0, 1, N_ROWS),
            "feature_c": rng.normal(5, 2, N_ROWS),
            "feature_d": rng.normal(-3, 1, N_ROWS),
        }
    )
    train = df.iloc[:200].reset_index(drop=True)
    test = df.iloc[200:].reset_index(drop=True)
    return train, test


@pytest.mark.parametrize("model_type", list(_DETECTOR_FACTORIES.keys()), ids=lambda m: m.value)
def test_repeated_fit_score_cycles_produce_consistent_scores(model_type: ModelType):
    """FR-002: N independent fit/score cycles on unchanged data agree."""
    train, test = _data()
    factory = _DETECTOR_FACTORIES[model_type]

    runs = []
    for _ in range(N_CYCLES):
        # A brand-new detector instance each cycle -- this is what makes
        # the cycles independent rather than just re-scoring one fitted
        # object (which would prove far less).
        detector = factory().fit(train)
        runs.append(np.asarray(detector.score(test), dtype=float))

    baseline = runs[0]
    assert len(baseline) == len(test), f"{model_type.value} scored {len(baseline)} of {len(test)} rows"
    assert np.all(np.isfinite(baseline)), f"{model_type.value} produced non-finite scores"

    for cycle_index, scores in enumerate(runs[1:], start=2):
        assert np.allclose(scores, baseline, rtol=RELATIVE_TOLERANCE, atol=RELATIVE_TOLERANCE), (
            f"{model_type.value} is unstable: cycle {cycle_index}'s scores diverge from cycle 1's "
            f"beyond the documented tolerance {RELATIVE_TOLERANCE}. "
            f"Max abs delta: {np.max(np.abs(scores - baseline))}"
        )


@pytest.mark.parametrize("model_type", list(_DETECTOR_FACTORIES.keys()), ids=lambda m: m.value)
def test_stability_check_would_catch_a_genuinely_drifting_model(model_type: ModelType):
    """Guards the assertion above from being vacuous. If the comparison
    were written so loosely that any two score vectors "agree," the test
    would pass while proving nothing -- so confirm the same comparison
    rejects a perturbed vector."""
    train, test = _data()
    detector = _DETECTOR_FACTORIES[model_type]().fit(train)
    baseline = np.asarray(detector.score(test), dtype=float)

    perturbed = baseline.copy()
    scale = np.abs(baseline).max() or 1.0
    perturbed[0] += scale * 0.5

    assert not np.allclose(perturbed, baseline, rtol=RELATIVE_TOLERANCE, atol=RELATIVE_TOLERANCE), (
        f"The stability tolerance for {model_type.value} is so loose it accepts a visibly "
        f"perturbed score vector -- the stability assertion above would be vacuous."
    )
