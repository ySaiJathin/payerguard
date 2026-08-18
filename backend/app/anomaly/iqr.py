"""Hand-rolled IQR baseline (MVP_CONTEXT.md Section 3.1): simple enough
(Q1/Q3/1.5xIQR bounds) that a hand-rolled implementation is more transparent
than pulling in a dependency for it (research.md).
"""

import numpy as np
import pandas as pd

IQR_MULTIPLIER = 1.5


class IQRDetector:
    """`fit` computes per-feature Q1/Q3/1.5xIQR bounds on train; `score`
    returns a per-row anomaly score (summed out-of-bound distance across
    features, so rows violating more features' bounds score higher);
    `parameters` returns the fitted bounds.
    """

    def __init__(self) -> None:
        self._bounds: dict[str, tuple[float, float]] = {}
        self._train_medians: dict[str, float] = {}

    def fit(self, df: pd.DataFrame) -> "IQRDetector":
        for col in df.columns:
            values = df[col].dropna()
            if values.empty:
                self._bounds[col] = (float("-inf"), float("inf"))
                self._train_medians[col] = 0.0
                continue
            q1, q3 = values.quantile(0.25), values.quantile(0.75)
            iqr = q3 - q1
            self._bounds[col] = (float(q1 - IQR_MULTIPLIER * iqr), float(q3 + IQR_MULTIPLIER * iqr))
            self._train_medians[col] = float(values.median())
        return self

    def score(self, df: pd.DataFrame) -> np.ndarray:
        scores = np.zeros(len(df))
        for col, (lo, hi) in self._bounds.items():
            if col not in df.columns:
                continue
            # Missing cells (e.g. a missing_value_spike injection) are
            # filled with the fitted train median for scoring purposes only
            # -- consistent with the train-median imputation policy applied
            # elsewhere in the benchmark, never with validation/test data.
            values = df[col].fillna(self._train_medians[col]).to_numpy(dtype=float)
            below = np.clip(lo - values, 0, None)
            above = np.clip(values - hi, 0, None)
            scores += below + above
        return scores

    @property
    def parameters(self) -> dict:
        return {col: {"lower": lo, "upper": hi} for col, (lo, hi) in self._bounds.items()}
