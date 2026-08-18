"""XGBoost candidate (spec FR-001; MVP_CONTEXT.md Section 6 -- pending
benchmark, not hard-selected in advance, constitution Principle I)."""

from xgboost import XGBClassifier

from app.risk.benchmark.schemas import ModelType

MODEL_TYPE = ModelType.xgboost

HYPERPARAMETER_GRID: list[dict] = [
    {"n_estimators": 100, "max_depth": 3},
    {"n_estimators": 100, "max_depth": 6},
    {"n_estimators": 300, "max_depth": 3},
    {"n_estimators": 300, "max_depth": 6},
]


def build_model(params: dict) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=20260818,
    )
