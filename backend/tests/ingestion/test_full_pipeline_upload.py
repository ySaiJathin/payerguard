"""spec SC-001: an accepted upload is driven through the full existing
pipeline and produces real quality/anomaly/risk/incident references.

Phases 2-16 already have their own extensive real-data test suites
proving each stage's own internal correctness (MVP_CONTEXT.md Section
9.4). This file's job is narrower and specific to `ingestion`: prove
`pipeline_runner.run` calls every stage in order, records each stage's
real result honestly on the `IngestedBatch`, and creates an incident only
for a window whose risk score actually crosses the threshold -- so each
stage function is stubbed with a realistic-shaped fake return value
(mirroring `tests/audit/test_registry_completeness.py`'s own precedent of
stubbing the heavy model-fitting behind a call under test).
"""

from pathlib import Path

from app.ingestion import batch_service, pipeline_runner
from app.ingestion.schemas import BatchStatus
from tests._db_fixtures import make_test_session
from tests.ingestion._fixtures import (
    fake_enrich_result,
    fake_incident,
    fake_quality_result,
    fake_window_row,
)


def _patch_common_stages(monkeypatch, *, rows):
    monkeypatch.setattr(pipeline_runner, "run_cleaning", lambda **kwargs: None)
    monkeypatch.setattr(pipeline_runner, "run_validation", lambda: fake_quality_result())
    monkeypatch.setattr(pipeline_runner, "compute_features", lambda: ([], []))
    monkeypatch.setattr(pipeline_runner.features_log, "write_claim_features", lambda _: None)
    monkeypatch.setattr(pipeline_runner.features_log, "write_window_features", lambda _: None)
    monkeypatch.setattr(pipeline_runner, "enrich_windows", lambda: fake_enrich_result())
    monkeypatch.setattr(pipeline_runner, "assemble_rows", lambda: rows)
    monkeypatch.setattr(pipeline_runner, "read_quality_results", lambda: None)


def test_full_pipeline_produces_real_results_and_incident(monkeypatch):
    db = make_test_session()
    batch = batch_service.create_batch(db, filename="inpatient.csv", row_count=500)

    # Window 1 crosses INCIDENT_RISK_FLOOR (10.0); window 2 does not.
    rows = [fake_window_row("W1"), fake_window_row("W2")]
    _patch_common_stages(monkeypatch, rows=rows)
    monkeypatch.setattr(
        pipeline_runner, "score_window", lambda row: 55.0 if row["window_id"] == "W1" else 2.0
    )

    created_incidents = []

    def _fake_create_incident(db_arg, payload):
        created_incidents.append(payload)
        return fake_incident(f"incident-for-{payload.window_id}")

    monkeypatch.setattr(pipeline_runner, "create_incident", _fake_create_incident)

    pipeline_runner.run(db, batch.batch_id, Path("unused-raw-path.csv"))

    result = batch_service.get_batch(db, batch.batch_id)
    assert result.status == BatchStatus.completed
    assert result.pipeline_stage_reached == "incidents"
    assert result.quality_result_id == "qual-run-1"
    assert result.anomaly_result_id == "isolation_forest"
    assert result.incident_ids == ["incident-for-W1"]
    # Only the crossing window's evidence was built and passed through.
    assert len(created_incidents) == 1
    assert created_incidents[0].window_id == "W1"
    assert created_incidents[0].evidence.risk_score == 55.0
