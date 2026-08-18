from datetime import datetime, timezone

from app.anomaly.model_selection import RANKING_RULE, select_production_model
from app.anomaly.schemas import BenchmarkResult, MeasurementContext, ModelType

CONTEXT = MeasurementContext(hardware="test-runner", python_version="3.11", run_timestamp=datetime.now(timezone.utc))


def _result(model_type: ModelType, f1: float, fpr: float, execution_time_s: float) -> BenchmarkResult:
    return BenchmarkResult(
        model_type=model_type,
        precision=0.8,
        recall=0.8,
        f1=f1,
        fpr=fpr,
        detection_latency_ms=1.0,
        execution_time_s=execution_time_s,
        measurement_context=CONTEXT,
        per_injection_type_breakdown={},
    )


def test_selects_highest_f1_and_reproduces_recorded_numbers():
    results = [
        _result(ModelType.iqr, f1=0.5, fpr=0.2, execution_time_s=1.0),
        _result(ModelType.hbos, f1=0.9, fpr=0.1, execution_time_s=2.0),
        _result(ModelType.isolation_forest, f1=0.7, fpr=0.05, execution_time_s=0.5),
        _result(ModelType.lof, f1=0.6, fpr=0.3, execution_time_s=0.8),
    ]

    selection = select_production_model(results)

    best_f1 = max(results, key=lambda r: r.f1)
    assert selection.selected_model == best_f1.model_type
    assert selection.selected_model == ModelType.hbos
    assert selection.tie_break_applied is False
    assert selection.ranking_rule == RANKING_RULE
    assert set(selection.benchmark_result_ids) == {r.model_type.value for r in results}


def test_ties_on_f1_are_broken_by_lower_fpr_then_lower_execution_time():
    results = [
        _result(ModelType.iqr, f1=0.8, fpr=0.2, execution_time_s=1.0),
        _result(ModelType.hbos, f1=0.8, fpr=0.1, execution_time_s=5.0),
        _result(ModelType.isolation_forest, f1=0.8, fpr=0.1, execution_time_s=2.0),
        _result(ModelType.lof, f1=0.4, fpr=0.05, execution_time_s=0.1),
    ]

    selection = select_production_model(results)

    # iqr, hbos, and isolation_forest all tie on f1 (0.8). hbos and
    # isolation_forest also tie on the first tie-break, fpr (0.1), beating
    # iqr's fpr (0.2); isolation_forest then wins the second tie-break,
    # execution_time (2.0 < 5.0).
    assert selection.selected_model == ModelType.isolation_forest
    assert selection.tie_break_applied is True


def test_selection_does_not_default_to_hbos_when_it_loses():
    results = [
        _result(ModelType.iqr, f1=0.95, fpr=0.01, execution_time_s=1.0),
        _result(ModelType.hbos, f1=0.5, fpr=0.3, execution_time_s=1.0),
        _result(ModelType.isolation_forest, f1=0.6, fpr=0.2, execution_time_s=1.0),
        _result(ModelType.lof, f1=0.4, fpr=0.4, execution_time_s=1.0),
    ]

    selection = select_production_model(results)

    assert selection.selected_model == ModelType.iqr
