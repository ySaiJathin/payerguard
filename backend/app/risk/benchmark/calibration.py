"""Calibration metric for the risk model benchmark (spec FR-004; research.md).

Brier score (mean squared error between predicted probability and actual
binary outcome) is used rather than Expected Calibration Error: ECE needs
a bin-count choice to compute, which would itself be an undocumented
arbitrary parameter; Brier score needs none, keeping it exactly
reproducible from a model's own test-split predictions (spec SC-002).
"""

import numpy as np
from sklearn.metrics import brier_score_loss


def brier_score(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    return float(brier_score_loss(y_true, y_proba))
