"""Wraps `pyod.models.hbos.HBOS` -- the standard, tested implementation of
the exact histogram-based formula MVP_CONTEXT.md Section 3.1 documents
(`Hj(x) = -log(Pj(x) + eps)`, `HBOS(x) = sum_j Hj(x)`) (research.md).
"""

import numpy as np
import pandas as pd
from pyod.models.hbos import HBOS

DEFAULT_N_BINS = 10
DEFAULT_ALPHA = 0.1
DEFAULT_CONTAMINATION = 0.1


class HBOSDetector:
    """`fit`/`score`/`parameters` match `IQRDetector`'s interface."""

    def __init__(
        self,
        n_bins: int = DEFAULT_N_BINS,
        alpha: float = DEFAULT_ALPHA,
        contamination: float = DEFAULT_CONTAMINATION,
    ) -> None:
        self._model = HBOS(n_bins=n_bins, alpha=alpha, contamination=contamination)
        self._columns: list[str] = []
        self._train_medians: dict[str, float] = {}

    def fit(self, df: pd.DataFrame) -> "HBOSDetector":
        self._columns = list(df.columns)
        self._train_medians = {col: float(df[col].median()) for col in self._columns}
        self._model.fit(df.to_numpy(dtype=float))
        return self

    def _prepare(self, df: pd.DataFrame) -> np.ndarray:
        # Missing cells (e.g. a missing_value_spike injection) are filled
        # with the fitted train median for scoring purposes only -- pyod's
        # HBOS has no native NaN support.
        filled = df[self._columns].copy()
        for col in self._columns:
            filled[col] = filled[col].fillna(self._train_medians[col])
        return filled.to_numpy(dtype=float)

    def score(self, df: pd.DataFrame) -> np.ndarray:
        return self._model.decision_function(self._prepare(df))

    @property
    def parameters(self) -> dict:
        return {
            "n_bins": self._model.n_bins,
            "alpha": self._model.alpha,
            "contamination": self._model.contamination,
        }
