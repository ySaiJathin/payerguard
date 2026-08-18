"""Anomaly detection API endpoints.

Endpoints per specs/007-anomaly-detection-benchmark/contracts/api.md.
"""

from fastapi import APIRouter, HTTPException

from app.anomaly.benchmark import read_benchmark_run_result, run_benchmark
from app.anomaly.data_loading import AnomalyInputUnavailableError
from app.anomaly.schemas import BenchmarkRunResult, EnrichWindowsResult
from app.anomaly.window_enrichment import NoProductionModelSelectedError, enrich_windows

router = APIRouter(prefix="/anomaly", tags=["anomaly"])


@router.post("/benchmark", response_model=BenchmarkRunResult)
def benchmark() -> BenchmarkRunResult:
    try:
        return run_benchmark()
    except AnomalyInputUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/results", response_model=BenchmarkRunResult)
def results() -> BenchmarkRunResult:
    run_result = read_benchmark_run_result()
    if run_result is None:
        raise HTTPException(status_code=404, detail="No benchmark run yet -- call POST /anomaly/benchmark first.")
    return run_result


@router.post("/enrich-windows", response_model=EnrichWindowsResult)
def enrich() -> EnrichWindowsResult:
    try:
        return enrich_windows()
    except NoProductionModelSelectedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
