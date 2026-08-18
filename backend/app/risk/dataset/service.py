"""Orchestrates risk dataset construction end-to-end: assemble rows (Phase
3/4/5/7 provenance) -> compute + apply the label formula (Phase 6 train-
split calibration) -> compute the label distribution -> persist everything.
Used by `POST /risk/dataset/build`.
"""

from app.features.selection.temporal_split import read_temporal_split
from app.risk.dataset import dataset_log, label_formula
from app.risk.dataset.errors import RiskDatasetInputUnavailableError
from app.risk.dataset.label_distribution import compute_label_distribution
from app.risk.dataset.row_assembly import assemble_rows
from app.risk.dataset.schemas import RiskDatasetBuildResult, RiskDatasetRow


def build_risk_dataset() -> RiskDatasetBuildResult:
    split = read_temporal_split()
    if split is None:
        raise RiskDatasetInputUnavailableError(
            "No Phase 6 temporal split found -- run POST /features/split first."
        )

    pre_label_rows = assemble_rows()  # raises RiskDatasetInputUnavailableError / AnomalyEnrichmentIncompleteError

    formula = label_formula.compute_formula(pre_label_rows, split)
    labeled_rows = label_formula.apply_formula(pre_label_rows, formula, split)

    distribution = compute_label_distribution(labeled_rows)

    rows = [RiskDatasetRow.model_validate(row) for row in labeled_rows]
    dataset_log.write_risk_dataset_rows(rows)
    dataset_log.write_label_formula(formula)

    return RiskDatasetBuildResult(
        rows_built=len(rows),
        label_distribution=distribution,
        formula_version=formula.formula_version,
    )
