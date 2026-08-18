from app.incidents.schemas import IncidentUpdate
from app.incidents.service import create_incident, get_incident, list_incidents, update_incident
from tests._db_fixtures import make_test_session
from tests.incidents._fixtures import make_incident_create
from tests.llm._fixtures import always_returns, make_draft


def test_created_incident_carries_real_phase10_scores_and_linked_investigation():
    db = make_test_session()
    client = always_returns(make_draft())

    incident = create_incident(db, make_incident_create(), mistral_client_override=client)

    assert incident.status.value == "ready_for_review"
    assert incident.current_investigation_id is not None
    # real Phase 10 scores -- not placeholders
    assert incident.quality_score == (100.0 + 50.0) / 2  # CRITICAL, WARNING averaged
    assert 0.0 <= incident.priority_result["priority"] <= 100.0
    assert incident.severity_result["severity"] > 0.0


def test_list_and_get_return_real_persisted_data():
    db = make_test_session()
    client = always_returns(make_draft())
    created = create_incident(db, make_incident_create(window_id="W-list"), mistral_client_override=client)

    fetched = get_incident(db, created.incident_id)
    assert fetched is not None
    assert fetched.window_id == "W-list"
    assert fetched.incident_id == created.incident_id

    all_incidents = list_incidents(db)
    assert any(i.incident_id == created.incident_id for i in all_incidents)

    filtered = list_incidents(db, status="ready_for_review")
    assert all(i.status.value == "ready_for_review" for i in filtered)


def test_get_unknown_incident_returns_none():
    db = make_test_session()
    assert get_incident(db, "does-not-exist") is None


def test_patch_updates_non_status_field_and_cannot_touch_status():
    db = make_test_session()
    client = always_returns(make_draft())
    created = create_incident(db, make_incident_create(), mistral_client_override=client)

    updated = update_incident(db, created.incident_id, IncidentUpdate(quality_score=99.0))
    assert updated is not None
    assert updated.quality_score == 99.0
    # status is untouched -- IncidentUpdate has no status field to smuggle one through
    assert updated.status == created.status
    assert not hasattr(IncidentUpdate(), "status")
