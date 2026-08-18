"""Risk dataset construction API endpoints.

Endpoints per specs/008-risk-dataset-construction/contracts/api.md.
"""

from fastapi import APIRouter, HTTPException

from app.risk.dataset import dataset_log
from app.risk.dataset.errors import RiskDatasetInputUnavailableError
from app.risk.dataset.schemas import InvestigationRiskLabelFormula, RiskDatasetBuildResult, RiskDatasetRow
from app.risk.dataset.service import build_risk_dataset

router = APIRouter(prefix="/risk/dataset", tags=["risk"])


@router.post("/build", response_model=RiskDatasetBuildResult)
def build() -> RiskDatasetBuildResult:
    try:
        return build_risk_dataset()
    except RiskDatasetInputUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_model=list[RiskDatasetRow])
def get_dataset() -> list[RiskDatasetRow]:
    rows = dataset_log.read_risk_dataset_rows()
    if not rows:
        raise HTTPException(status_code=404, detail="No risk dataset built yet -- call POST /risk/dataset/build first.")
    return rows


@router.get("/label-formula", response_model=InvestigationRiskLabelFormula)
def get_label_formula() -> InvestigationRiskLabelFormula:
    formula = dataset_log.read_label_formula()
    if formula is None:
        raise HTTPException(
            status_code=404, detail="No label formula computed yet -- call POST /risk/dataset/build first."
        )
    return formula
