"""Random Forest candidate (spec FR-001)."""

from sklearn.ensemble import RandomForestClassifier

from app.risk.benchmark.schemas import ModelType

MODEL_TYPE = ModelType.random_forest

HYPERPARAMETER_GRID: list[dict] = [
    {"n_estimators": 100, "max_depth": None},
    {"n_estimators": 100, "max_depth": 5},
    {"n_estimators": 300, "max_depth": None},
    {"n_estimators": 300, "max_depth": 5},
]


def build_model(params: dict) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        class_weight="balanced",
        random_state=20260818,
    )
