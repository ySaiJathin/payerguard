# API Contracts: Risk Dataset Construction

New `risk` module router (dataset construction; Phase 9 adds model-benchmark endpoints to the same module).

## `POST /risk/dataset/build`

Assembles `RiskDatasetRow[]` from Phase 3/4/5/7 outputs and computes/persists the `InvestigationRiskLabelFormula` and `LabelDistributionReport`.

**Response `200 OK`**:
```json
{
  "rows_built": 42,
  "label_distribution": "...LabelDistributionReport",
  "formula_version": "v1"
}
```

**Response `409 Conflict`**: Phase 7's `anomaly_count` enrichment incomplete, or Phase 3/4/5 outputs missing (spec FR-008).

## `GET /risk/dataset`

Returns the full `RiskDatasetRow[]`.

**Response `200 OK`**: `RiskDatasetRow[]`.

## `GET /risk/dataset/label-formula`

Returns the current `InvestigationRiskLabelFormula` document (also available as `data/risk/investigation_risk_label_formula.md`).

**Response `200 OK`**: `InvestigationRiskLabelFormula`.

## Notes

- `POST /risk/dataset/build` is safe to re-run after Phase 15 adds new historical batches; historical rows reproduce identically (spec FR-010, SC-006) while new windows are added.
