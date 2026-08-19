"""Quality validation layer's external API surface.

Endpoints per specs/003-quality-validation-layer/contracts/api.md.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit.aggregation_service import append_entries
from app.core.database import get_db
from app.data_engineering.dtype_conversion import CategoriesUnavailableError, load_column_categories
from app.quality import quality_results_log
from app.quality.data_loader import QualityInputUnavailableError
from app.quality.schemas import ColumnCategory, ExpectationCheckResult, QualityScoreResult
from app.quality.scoring_service import run_validation

router = APIRouter(prefix="/quality", tags=["quality"])


@router.post("/validate", response_model=QualityScoreResult)
def validate(db: Session = Depends(get_db)) -> QualityScoreResult:
    try:
        result = run_validation()
    except (QualityInputUnavailableError, CategoriesUnavailableError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # One audit entry per contributing ExpectationCheckResult (Phase 16
    # FR-001). Volume is bounded by the number of checks, not the number
    # of rows, so per-check granularity is viable here -- unlike Phase 2
    # cleaning, which is per-claim for exactly that reason. Batch-scoped:
    # a quality run evaluates the whole cleaned batch, not one claim.
    append_entries(
        db,
        [
            {
                "entity_type": "batch",
                "entity_id": result.run_id,
                "pipeline_stage": "quality",
                "source_module": "quality",
                "source_record_id": check_id,
                "occurred_at": result.generated_at,
            }
            for check_id in result.contributing_check_ids
        ],
    )
    db.commit()
    return result


@router.get("/results")
def get_results(band: str | None = None, category: str | None = None) -> dict:
    result = quality_results_log.read_quality_results()
    if result is None:
        raise HTTPException(status_code=404, detail="No quality run has been performed yet.")
    score_result, check_results = result

    if band is not None:
        check_results = [c for c in check_results if c.band.value == band]
    if category is not None:
        target_category = ColumnCategory(category)
        try:
            categories = load_column_categories()
        except CategoriesUnavailableError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        check_results = [
            c for c in check_results if c.column_name is not None and categories.get(c.column_name) == target_category
        ]

    return {
        "quality_score_result": score_result,
        "check_results": check_results,
    }


@router.get("/checks/{check_id}", response_model=ExpectationCheckResult)
def get_check(check_id: str) -> ExpectationCheckResult:
    check = quality_results_log.find_check(check_id)
    if check is None:
        raise HTTPException(status_code=404, detail=f"Unknown check_id: {check_id}")
    return check
