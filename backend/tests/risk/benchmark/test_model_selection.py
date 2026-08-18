from app.risk.benchmark.model_selection import select_production_model
from app.risk.benchmark.schemas import ModelType, RiskBenchmarkResult

COMMON = dict(
    accuracy=0.9,
    f1=0.5,
    label_distribution_context={},
    risk_dataset_version="v1",
    split_id="s1",
)


def _result(model_type: ModelType, recall: float, pr_auc: float, brier: float, fnr: float) -> RiskBenchmarkResult:
    return RiskBenchmarkResult(
        model_type=model_type,
        precision=0.5,
        recall=recall,
        roc_auc=0.7,
        pr_auc=pr_auc,
        calibration_brier_score=brier,
        false_negative_rate=fnr,
        **COMMON,
    )


def test_highest_recall_survivor_wins_even_with_lower_accuracy():
    results = [
        _result(ModelType.logistic_regression, recall=0.60, pr_auc=0.50, brier=0.20, fnr=0.40),
        _result(ModelType.random_forest, recall=0.85, pr_auc=0.55, brier=0.25, fnr=0.15),
        _result(ModelType.xgboost, recall=0.70, pr_auc=0.60, brier=0.10, fnr=0.30),
    ]
    selection = select_production_model(results, test_label_base_rate=0.30)
    assert selection.selected_model == ModelType.random_forest
    assert selection.tie_break_applied is False


def test_pr_auc_floor_excludes_models_no_better_than_random():
    results = [
        _result(ModelType.logistic_regression, recall=0.95, pr_auc=0.30, brier=0.20, fnr=0.05),  # at the floor, excluded
        _result(ModelType.random_forest, recall=0.70, pr_auc=0.55, brier=0.25, fnr=0.30),
        _result(ModelType.xgboost, recall=0.60, pr_auc=0.60, brier=0.10, fnr=0.40),
    ]
    selection = select_production_model(results, test_label_base_rate=0.30)
    # logistic_regression has the best raw recall but doesn't clear the floor
    assert selection.selected_model == ModelType.random_forest


def test_recall_tie_broken_by_lower_brier_score_then_fnr():
    results = [
        _result(ModelType.logistic_regression, recall=0.700, pr_auc=0.50, brier=0.30, fnr=0.300),
        _result(ModelType.random_forest, recall=0.700, pr_auc=0.55, brier=0.10, fnr=0.300),
        _result(ModelType.xgboost, recall=0.690, pr_auc=0.60, brier=0.05, fnr=0.310),
    ]
    selection = select_production_model(results, test_label_base_rate=0.10)
    assert selection.selected_model == ModelType.random_forest
    assert selection.tie_break_applied is True


def test_xgboost_not_selected_when_it_has_the_worst_recall():
    results = [
        _result(ModelType.logistic_regression, recall=0.80, pr_auc=0.50, brier=0.20, fnr=0.20),
        _result(ModelType.random_forest, recall=0.75, pr_auc=0.55, brier=0.15, fnr=0.25),
        _result(ModelType.xgboost, recall=0.40, pr_auc=0.60, brier=0.05, fnr=0.60),
    ]
    selection = select_production_model(results, test_label_base_rate=0.10)
    assert selection.selected_model == ModelType.logistic_regression
    assert selection.selected_model != ModelType.xgboost


def test_falls_back_to_full_candidate_set_when_none_clear_the_floor():
    results = [
        _result(ModelType.logistic_regression, recall=0.50, pr_auc=0.10, brier=0.20, fnr=0.50),
        _result(ModelType.random_forest, recall=0.60, pr_auc=0.15, brier=0.25, fnr=0.40),
        _result(ModelType.xgboost, recall=0.30, pr_auc=0.05, brier=0.10, fnr=0.70),
    ]
    selection = select_production_model(results, test_label_base_rate=0.30)
    # none clear the floor (base_rate=0.30 > all pr_auc values) -- selection
    # still proceeds among all three, picking the best recall.
    assert selection.selected_model == ModelType.random_forest
    assert selection.pr_auc_floor_used == 0.30
