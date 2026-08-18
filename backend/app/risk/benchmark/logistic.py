"""Logistic Regression candidate (baseline classifier, spec FR-001)."""

from sklearn.linear_model import LogisticRegression

from app.risk.benchmark.schemas import ModelType

MODEL_TYPE = ModelType.logistic_regression

HYPERPARAMETER_GRID: list[dict] = [
    {"C": 0.1},
    {"C": 1.0},
    {"C": 10.0},
]


def build_model(params: dict) -> LogisticRegression:
    return LogisticRegression(C=params["C"], class_weight="balanced", max_iter=1000)
