"""Shared builders for `tests/ingestion/` -- not a test module itself (no
`test_` prefix, so pytest doesn't collect it).
"""

import json
from pathlib import Path
from types import SimpleNamespace

from app.data_engineering.categorization import categorize
from tests.data_engineering.test_cleaning_service import CLEAN_FIXTURE, FIXTURE_COLUMNS


def raw_claims_fixture() -> bytes:
    """A small, real, pipe-delimited claims file -- the same fixture
    `tests/data_engineering/` already uses, so it is genuinely schema-
    conformant against `write_fixture_categories`'s output."""
    return CLEAN_FIXTURE.read_bytes()


def write_fixture_categories(tmp_path: Path) -> Path:
    """Writes a tmp `column_categories.json` scoped to `FIXTURE_COLUMNS`,
    so `upload_validation.validate_and_load`'s `categories_path` override
    can validate the small fixture against a matching (not the real
    197-column) schema -- mirrors
    `tests/data_engineering/test_cleaning_service.py`'s own pattern."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    categories = {col: categorize(col).value for col in FIXTURE_COLUMNS}
    path = reports_dir / "column_categories.json"
    path.write_text(json.dumps(categories), encoding="utf-8")
    return reports_dir


def fake_window_row(window_id: str = "W1", *, anomaly_score: float = 40.0, affected_claim_pct: float = 12.0) -> dict:
    """One row shaped like `risk.dataset.row_assembly.assemble_rows`'s
    output -- what `pipeline_runner.run` reads to build an
    `EvidenceBundle`."""
    return {
        "window_id": window_id,
        "window_start": "2020-01-01T00:00:00+00:00",
        "window_end": "2020-01-08T00:00:00+00:00",
        "claim_count": 25,
        "gx_failure_count": 1,
        "anomaly_score": anomaly_score,
        "anomaly_frequency": anomaly_score / 100.0,
        "affected_claim_pct": affected_claim_pct,
        "volume_deviation": 0.1,
        "amount_deviation": 0.05,
        "historical_quality_failure_rate": 0.02,
    }


def fake_quality_result(run_id: str = "qual-run-1"):
    return SimpleNamespace(run_id=run_id)


def fake_enrich_result(model_used: str = "isolation_forest"):
    return SimpleNamespace(model_used=model_used)


def fake_incident(incident_id: str):
    return SimpleNamespace(incident_id=incident_id)
