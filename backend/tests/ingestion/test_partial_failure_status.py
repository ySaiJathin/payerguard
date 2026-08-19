"""spec SC-004: a batch that fails partway through the pipeline is
honestly reported as `failed`, naming the last stage it actually
completed -- never silently `completed` (FR-007, constitution
Principle II).
"""

import pytest

from app.ingestion import batch_service, pipeline_runner
from app.ingestion.schemas import BatchStatus
from tests._db_fixtures import make_test_session
from tests.ingestion._fixtures import fake_quality_result
from pathlib import Path


def test_failure_during_quality_reports_cleaning_as_last_completed_stage(monkeypatch):
    db = make_test_session()
    batch = batch_service.create_batch(db, filename="inpatient.csv", row_count=500)

    monkeypatch.setattr(pipeline_runner, "run_cleaning", lambda **kwargs: None)

    def _boom():
        raise RuntimeError("Great Expectations suite exploded")

    monkeypatch.setattr(pipeline_runner, "run_validation", _boom)

    with pytest.raises(pipeline_runner.PipelineRunError):
        pipeline_runner.run(db, batch.batch_id, Path("unused-raw-path.csv"))

    result = batch_service.get_batch(db, batch.batch_id)
    assert result.status == BatchStatus.failed
    assert result.pipeline_stage_reached == "cleaning"
    # Never advanced past what actually completed -- no quality/anomaly/
    # risk references were fabricated for a stage that never finished.
    assert result.quality_result_id is None
    assert result.incident_ids == []


def test_failure_during_cleaning_reports_no_completed_stage(monkeypatch):
    db = make_test_session()
    batch = batch_service.create_batch(db, filename="inpatient.csv", row_count=500)

    def _boom(**kwargs):
        raise RuntimeError("schema validation failed")

    monkeypatch.setattr(pipeline_runner, "run_cleaning", _boom)

    with pytest.raises(pipeline_runner.PipelineRunError):
        pipeline_runner.run(db, batch.batch_id, Path("unused-raw-path.csv"))

    result = batch_service.get_batch(db, batch.batch_id)
    assert result.status == BatchStatus.failed
    assert result.pipeline_stage_reached is None
