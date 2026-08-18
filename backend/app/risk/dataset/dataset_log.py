"""Persists `RiskDatasetRow[]` as data/risk/risk_dataset.csv and the
`InvestigationRiskLabelFormula` as data/risk/investigation_risk_label_formula.json
(machine-readable, for `GET /risk/dataset/label-formula`) plus a regenerated
data/risk/investigation_risk_label_formula.md (human-reviewable, spec FR-003,
FR-004). Each write overwrites the prior file -- mirroring Phase 3's
quality_results_log.py precedent -- so re-running dataset construction on
unmodified upstream data produces an identical persisted file, not an
accumulating one (spec SC-006).
"""

import json
from pathlib import Path

import pandas as pd

from app.data_engineering.paths import risk_dir
from app.risk.dataset.label_formula import render_formula_markdown
from app.risk.dataset.schemas import InvestigationRiskLabelFormula, RiskDatasetRow

RISK_DATASET_FILENAME = "risk_dataset.csv"
LABEL_FORMULA_JSON_FILENAME = "investigation_risk_label_formula.json"
LABEL_FORMULA_MD_FILENAME = "investigation_risk_label_formula.md"


def _dataset_path(out_dir: Path | None = None) -> Path:
    return (out_dir or risk_dir()) / RISK_DATASET_FILENAME


def _formula_json_path(out_dir: Path | None = None) -> Path:
    return (out_dir or risk_dir()) / LABEL_FORMULA_JSON_FILENAME


def _formula_md_path(out_dir: Path | None = None) -> Path:
    return (out_dir or risk_dir()) / LABEL_FORMULA_MD_FILENAME


def write_risk_dataset_rows(rows: list[RiskDatasetRow], out_dir: Path | None = None) -> Path:
    out_dir = out_dir or risk_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = _dataset_path(out_dir)
    records = [json.loads(row.model_dump_json()) for row in rows]
    pd.DataFrame(records).to_csv(path, index=False)
    return path


def read_risk_dataset_rows(out_dir: Path | None = None) -> list[RiskDatasetRow]:
    path = _dataset_path(out_dir)
    if not path.exists():
        return []
    df = pd.read_csv(path, dtype={"window_id": str})
    return [RiskDatasetRow.model_validate(record) for record in df.to_dict(orient="records")]


def write_label_formula(formula: InvestigationRiskLabelFormula, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or risk_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = _formula_json_path(out_dir)
    json_path.write_text(formula.model_dump_json(indent=2), encoding="utf-8")
    md_path = _formula_md_path(out_dir)
    md_path.write_text(render_formula_markdown(formula), encoding="utf-8")
    return json_path


def read_label_formula(out_dir: Path | None = None) -> InvestigationRiskLabelFormula | None:
    path = _formula_json_path(out_dir)
    if not path.exists():
        return None
    return InvestigationRiskLabelFormula.model_validate(json.loads(path.read_text(encoding="utf-8")))
