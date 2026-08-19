"""Anomaly detection API endpoints.

Endpoints per specs/007-anomaly-detection-benchmark/contracts/api.md.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.anomaly.benchmark import read_benchmark_run_result, run_benchmark
from app.anomaly.data_loading import AnomalyInputUnavailableError
from app.anomaly.schemas import BenchmarkRunResult, EnrichWindowsResult
from app.anomaly.window_enrichment import NoProductionModelSelectedError, enrich_windows
from app.audit.aggregation_service import append_entries
from app.core.database import get_db

router = APIRouter(prefix="/anomaly", tags=["anomaly"])


@router.post("/benchmark", response_model=BenchmarkRunResult)
def benchmark(db: Session = Depends(get_db)) -> BenchmarkRunResult:
    try:
        run_result = run_benchmark()
    except AnomalyInputUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # One audit entry per benchmarked model result (Phase 16 FR-001).
    # `benchmark_result_ids` are real ids in the persisted run result, so
    # each entry's provenance resolves; there are four of them, so
    # per-result granularity costs nothing.
    selection = run_result.production_model_selection
    append_entries(
        db,
        [
            {
                "entity_type": "batch",
                "entity_id": selection.selected_model.value,
                "pipeline_stage": "anomaly",
                "source_module": "anomaly",
                "source_record_id": result_id,
                "occurred_at": selection.selected_at,
            }
            for result_id in selection.benchmark_result_ids
        ],
    )
    db.commit()
    return run_result


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
