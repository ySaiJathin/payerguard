import httpx

from app.incidents.service import create_incident
from tests._db_fixtures import make_test_session
from tests.incidents._fixtures import make_incident_create
from tests.llm._fixtures import always_raises


def test_persistent_investigation_failure_still_persists_incident_with_pending_status():
    db = make_test_session()
    client = always_raises(httpx.TimeoutException("timed out"))

    incident = create_incident(db, make_incident_create(), mistral_client_override=client)

    # Real Phase 10 scores exist regardless of the investigation outcome.
    assert incident.quality_score == (100.0 + 50.0) / 2
    assert incident.priority_result["priority"] >= 0.0

    # Investigation failed -- reflected honestly, not fabricated.
    assert incident.status.value == "pending_investigation"
    assert incident.current_investigation_id is None
