"""Data engineering module's external API surface.

Endpoints per specs/001-data-profiling-foundation/contracts/api.md.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.data_engineering import quality_issue_log, report_writer
from app.data_engineering.cleaning_service import (
    CategoriesUnavailableError,
    CleaningError,
    SchemaValidationError,
    run_cleaning,
)
from app.data_engineering.profiling_service import ProfilingError, generate_profiling_report
from app.data_engineering.sampling_service import (
    DEFAULT_SEED,
    DEFAULT_TARGET_CLAIM_FRACTION,
    SamplingError,
    generate_sample,
)
from app.data_engineering.schemas import CleaningRunSummary, ProfilingReport, QualityIssueRecord, SampleManifest

router = APIRouter(prefix="/data-engineering", tags=["data-engineering"])


class SampleRequest(BaseModel):
    seed: int | None = None
    target_claim_fraction: float | None = None


class CleanRequest(BaseModel):
    source: str = "raw"


@router.post("/profile")
def run_profile() -> dict:
    try:
        report = generate_profiling_report()
    except ProfilingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    paths = report_writer.write_profiling_report(report)
    return {
        "generated_at": report.generated_at,
        "total_rows": report.total_rows,
        "total_columns": report.total_columns,
        "unique_claim_count": report.unique_claim_count,
        "unique_beneficiary_count": report.unique_beneficiary_count,
        "duplicate_row_count": report.duplicate_row_count,
        "report_markdown_path": str(paths["markdown"]),
        "report_json_path": str(paths["json"]),
        "column_categories_path": str(paths["categories"]),
    }


@router.get("/profile", response_model=ProfilingReport)
def get_profile() -> ProfilingReport:
    report = report_writer.read_profiling_report()
    if report is None:
        raise HTTPException(status_code=404, detail="No profiling run has been performed yet.")
    return report


@router.post("/sample", response_model=SampleManifest)
def run_sample(body: SampleRequest | None = None) -> SampleManifest:
    body = body or SampleRequest()
    seed = body.seed if body.seed is not None else DEFAULT_SEED
    fraction = (
        body.target_claim_fraction
        if body.target_claim_fraction is not None
        else DEFAULT_TARGET_CLAIM_FRACTION
    )
    try:
        return generate_sample(seed=seed, target_claim_fraction=fraction)
    except SamplingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/clean", response_model=CleaningRunSummary)
def run_clean(
    body: CleanRequest | None = None, db: Session = Depends(get_db)
) -> CleaningRunSummary:
    body = body or CleanRequest()
    try:
        summary = run_cleaning(source=body.source, db=db)
        db.commit()  # run_cleaning's audit entries join this transaction
        return summary
    except CategoriesUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SchemaValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.result.model_dump()) from exc
    except CleaningError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/clean", response_model=CleaningRunSummary)
def get_clean() -> CleaningRunSummary:
    summary = quality_issue_log.read_cleaning_run_summary()
    if summary is None:
        raise HTTPException(status_code=404, detail="No cleaning run has been performed yet.")
    return summary


@router.get("/quality-issues", response_model=list[QualityIssueRecord])
def get_quality_issues(
    quality_issue: str | None = None, column_name: str | None = None
) -> list[QualityIssueRecord]:
    records = quality_issue_log.read_quality_issues()
    if records is None:
        raise HTTPException(status_code=404, detail="No cleaning run has been performed yet.")
    if quality_issue is not None:
        records = [r for r in records if r.quality_issue.value == quality_issue]
    if column_name is not None:
        records = [r for r in records if r.column_name == column_name]
    return records
