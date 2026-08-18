"""Wraps `sklearn.neighbors.LocalOutlierFactor` with `novelty=True`, which
is required to score data outside the fit set -- the default `novelty=False`
only supports `fit_predict` on the training data itself and has no
`score_samples`/`predict` for held-out validation/test data (research.md).
"""

import numpy as np
import pandas as pd
from sklearn.neighbors import LocalOutlierFactor

DEFAULT_N_NEIGHBORS = 20
DEFAULT_CONTAMINATION = "auto"


class LOFDetector:
    """`fit`/`score`/`parameters` match `IQRDetector`'s interface. `score`
    returns `-model.score_samples(...)` so higher always means more
    anomalous, matching the other three detectors' convention.
    """

    def __init__(self, n_neighbors: int = DEFAULT_N_NEIGHBORS, contamination: str | float = DEFAULT_CONTAMINATION) -> None:
        self._n_neighbors = n_neighbors
        self._contamination = contamination
        self._model: LocalOutlierFactor | None = None
        self._columns: list[str] = []
        self._train_medians: dict[str, float] = {}

    def fit(self, df: pd.DataFrame) -> "LOFDetector":
        self._columns = list(df.columns)
        self._train_medians = {col: float(df[col].median()) for col in self._columns}
        # n_neighbors can't exceed the number of training samples.
        n_neighbors = min(self._n_neighbors, max(1, len(df) - 1))
        self._model = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=self._contamination, novelty=True)
        self._model.fit(df.to_numpy(dtype=float))
        return self

    def _prepare(self, df: pd.DataFrame) -> np.ndarray:
        filled = df[self._columns].copy()
        for col in self._columns:
            filled[col] = filled[col].fillna(self._train_medians[col])
        return filled.to_numpy(dtype=float)

    def score(self, df: pd.DataFrame) -> np.ndarray:
        assert self._model is not None, "LOFDetector.score called before fit"
        return -self._model.score_samples(self._prepare(df))

    @property
    def parameters(self) -> dict:
        assert self._model is not None, "LOFDetector.parameters accessed before fit"
        return {"n_neighbors": self._model.n_neighbors, "contamination": self._contamination}
