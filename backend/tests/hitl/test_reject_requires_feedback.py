import pytest

from app.hitl.errors import MissingFeedbackError
from app.hitl.models import HumanFeedback
from app.hitl.reject_service import reject_incident
from app.incidents.service import create_incident
from tests._db_fixtures import make_test_session
from tests.incidents._fixtures import make_incident_create
from tests.llm._fixtures import always_returns, make_draft


def _ready_incident(db):
    client = always_returns(make_draft())
    return create_incident(db, make_incident_create(), mistral_client_override=client)


@pytest.mark.parametrize("feedback_text", ["", "   ", None])
def test_reject_without_feedback_raises_and_persists_nothing(feedback_text):
    db = make_test_session()
    incident = _ready_incident(db)

    with pytest.raises(MissingFeedbackError):
        reject_incident(db, incident.incident_id, "r1", "other", feedback_text)

    # zero side effects -- no feedback row, status unchanged
    assert db.query(HumanFeedback).count() == 0
    from app.incidents.service import get_incident

    unchanged = get_incident(db, incident.incident_id)
    assert unchanged.status == incident.status


def test_reject_with_feedback_persists_exactly_one_linked_record():
    db = make_test_session()
    incident = _ready_incident(db)

    reject_incident(db, incident.incident_id, "r1", "false_positive", "Known holiday volume dip.")

    rows = db.query(HumanFeedback).filter_by(incident_id=incident.incident_id).all()
    assert len(rows) == 1
    assert rows[0].feedback_text == "Known holiday volume dip."
    assert rows[0].investigation_id == incident.current_investigation_id
    assert rows[0].reviewer_id == "r1"
