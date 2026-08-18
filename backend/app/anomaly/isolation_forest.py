"""Wraps `sklearn.ensemble.IsolationForest` -- the canonical scikit-learn
implementation referenced generically by name in MVP_CONTEXT.md
(research.md).
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

DEFAULT_N_ESTIMATORS = 100
DEFAULT_CONTAMINATION = "auto"
DEFAULT_RANDOM_STATE = 0


class IsolationForestDetector:
    """`fit`/`score`/`parameters` match `IQRDetector`'s interface. `score`
    returns `-model.score_samples(...)` so higher always means more
    anomalous, matching the other three detectors' convention.
    """

    def __init__(
        self,
        n_estimators: int = DEFAULT_N_ESTIMATORS,
        contamination: str | float = DEFAULT_CONTAMINATION,
        random_state: int = DEFAULT_RANDOM_STATE,
    ) -> None:
        self._model = IsolationForest(
            n_estimators=n_estimators, contamination=contamination, random_state=random_state
        )
        self._columns: list[str] = []
        self._train_medians: dict[str, float] = {}

    def fit(self, df: pd.DataFrame) -> "IsolationForestDetector":
        self._columns = list(df.columns)
        self._train_medians = {col: float(df[col].median()) for col in self._columns}
        self._model.fit(df.to_numpy(dtype=float))
        return self

    def _prepare(self, df: pd.DataFrame) -> np.ndarray:
        filled = df[self._columns].copy()
        for col in self._columns:
            filled[col] = filled[col].fillna(self._train_medians[col])
        return filled.to_numpy(dtype=float)

    def score(self, df: pd.DataFrame) -> np.ndarray:
        return -self._model.score_samples(self._prepare(df))

    @property
    def parameters(self) -> dict:
        return {
            "n_estimators": self._model.n_estimators,
            "contamination": self._model.contamination,
            "random_state": self._model.random_state,
        }
