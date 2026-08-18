"""Risk model benchmark API endpoints.

Endpoints per specs/009-risk-model-benchmark/contracts/api.md.
"""

from fastapi import APIRouter, HTTPException

from app.risk.benchmark import benchmark_log
from app.risk.benchmark.benchmark_runner import run_benchmark
from app.risk.benchmark.data_loading import build_benchmark_frame
from app.risk.benchmark.errors import RiskModelInputUnavailableError
from app.risk.benchmark.model_selection import select_production_model
from app.risk.benchmark.schemas import RiskBenchmarkRunResult

router = APIRouter(prefix="/risk/benchmark", tags=["risk"])


def _run_and_persist() -> RiskBenchmarkRunResult:
    frame = build_benchmark_frame()
    results, data_scale_warning = run_benchmark(frame)

    _, y_test = frame.test
    test_label_base_rate = float(y_test.mean()) if len(y_test) else 0.0
    selection = select_production_model(results, test_label_base_rate)

    run_result = RiskBenchmarkRunResult(
        benchmark_results=results,
        production_model_selection=selection,
        data_scale_warning=data_scale_warning,
    )
    benchmark_log.append_run_result(run_result, frame.risk_dataset_version, frame.split.split_id)
    return run_result


@router.post("", response_model=RiskBenchmarkRunResult)
def benchmark() -> RiskBenchmarkRunResult:
    try:
        return _run_and_persist()
    except RiskModelInputUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/results", response_model=RiskBenchmarkRunResult)
def get_results(risk_dataset_version: str | None = None) -> RiskBenchmarkRunResult:
    if risk_dataset_version is not None:
        run_result = benchmark_log.read_run_result_by_version(risk_dataset_version)
        if run_result is None:
            raise HTTPException(
                status_code=404, detail=f"No benchmark run found for risk_dataset_version={risk_dataset_version!r}."
            )
        return run_result

    run_result = benchmark_log.read_latest_run_result()
    if run_result is None:
        raise HTTPException(status_code=404, detail="No benchmark run yet -- call POST /risk/benchmark first.")
    return run_result
