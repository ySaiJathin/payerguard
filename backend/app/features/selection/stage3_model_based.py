"""Stage 3: model-based feature selection -- XGBoost importance,
permutation importance, and RFE (if the post-Stage-2 feature count still
warrants it), fit exclusively on train+validation data (spec FR-007).

Only numeric candidate columns are scored -- XGBoost importance needs a
numeric feature matrix, and encoding leftover raw categoricals is out of
this phase's scope. Non-numeric survivors from Stage 2 pass through
unscored, neither dropped nor ranked by this stage.
"""

import pandas as pd
from sklearn.feature_selection import RFE
from sklearn.inspection import permutation_importance
from xgboost import XGBRegressor

from app.features.selection.schemas import FeatureDropDecision

STAGE = 3
STAGE_COMPUTED_ON = "train_validation"

DEFAULT_IMPORTANCE_THRESHOLD = 0.01
DEFAULT_RFE_FEATURE_COUNT_CEILING = 40


def _decision(feature_name: str, reason: str, statistic_value: float | None) -> FeatureDropDecision:
    return FeatureDropDecision(
        feature_name=feature_name,
        stage=STAGE,
        reason=reason,
        statistic_value=statistic_value,
        stage_computed_on=STAGE_COMPUTED_ON,
    )


def apply_stage3(
    train_val_df: pd.DataFrame,
    columns: list[str],
    target: pd.Series,
    importance_threshold: float = DEFAULT_IMPORTANCE_THRESHOLD,
    rfe_feature_count_ceiling: int = DEFAULT_RFE_FEATURE_COUNT_CEILING,
) -> tuple[list[str], list[FeatureDropDecision]]:
    numeric_columns = [c for c in columns if pd.api.types.is_numeric_dtype(train_val_df[c])]
    non_numeric_columns = [c for c in columns if c not in numeric_columns]

    if len(numeric_columns) == 0:
        return list(columns), []

    X = train_val_df[numeric_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y = pd.to_numeric(pd.Series(target).reset_index(drop=True), errors="coerce").fillna(0.0)
    y = y.reindex(range(len(X))).fillna(0.0)

    model = XGBRegressor(n_estimators=100, max_depth=4, random_state=0, verbosity=0)
    model.fit(X, y)
    xgb_importances = dict(zip(numeric_columns, model.feature_importances_))

    perm_result = permutation_importance(model, X, y, n_repeats=5, random_state=0)
    perm_importances = dict(zip(numeric_columns, perm_result.importances_mean))

    decisions: list[FeatureDropDecision] = []
    survivors: list[str] = []
    for col in numeric_columns:
        xgb_importance = float(xgb_importances[col])
        perm_importance_value = float(perm_importances[col])
        if xgb_importance < importance_threshold:
            decisions.append(
                _decision(
                    col,
                    f"XGBoost importance {xgb_importance:.4f} below threshold {importance_threshold:.4f} "
                    f"(permutation importance {perm_importance_value:.4f}), train+validation, "
                    "target=provisional_deviation_magnitude",
                    xgb_importance,
                )
            )
        else:
            survivors.append(col)

    if len(survivors) > rfe_feature_count_ceiling:
        rfe_model = XGBRegressor(n_estimators=50, max_depth=4, random_state=0, verbosity=0)
        selector = RFE(rfe_model, n_features_to_select=rfe_feature_count_ceiling)
        selector.fit(X[survivors], y)
        rfe_survivors = [c for c, keep in zip(survivors, selector.support_) if keep]
        rfe_dropped = [c for c in survivors if c not in rfe_survivors]
        for col in rfe_dropped:
            decisions.append(
                _decision(col, f"dropped by RFE narrowing surviving features to {rfe_feature_count_ceiling}", None)
            )
        survivors = rfe_survivors

    return survivors + non_numeric_columns, decisions
