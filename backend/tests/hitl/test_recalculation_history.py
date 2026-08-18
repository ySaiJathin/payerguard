from app.hitl.models import HumanFeedback, IncidentStatusTransition
from app.hitl.recalculation_service import recalculate_incident
from app.hitl.reject_service import reject_incident
from app.incidents.schemas import EvidenceBundle
from app.incidents.service import create_incident, get_incident
from tests._db_fixtures import make_test_session
from tests.incidents._fixtures import make_evidence, make_incident_create
from tests.llm._fixtures import always_returns, make_draft


def _rejected_incident(db):
    client = always_returns(make_draft())
    incident = create_incident(db, make_incident_create(), mistral_client_override=client)
    rejected = reject_incident(db, incident.incident_id, "r1", "false_positive", "Known holiday volume dip.")
    return rejected


def test_recalculation_produces_new_investigation_preserving_prior_history():
    db = make_test_session()
    rejected = _rejected_incident(db)
    prior_investigation_id = rejected.current_investigation_id

    prior_feedback = db.query(HumanFeedback).filter_by(incident_id=rejected.incident_id).all()
    prior_transitions = db.query(IncidentStatusTransition).filter_by(incident_id=rejected.incident_id).all()
    assert len(prior_feedback) == 1
    reject_transition_id = next(t.transition_id for t in prior_transitions if t.action == "reject")

    client = always_returns(make_draft("A fresh read on the same evidence."))
    result = recalculate_incident(db, rejected.incident_id, new_evidence=None, mistral_client_override=client)

    assert result.evidence_changed is False
    assert result.new_investigation is not None
    assert result.new_investigation.investigation_id != prior_investigation_id
    assert result.incident.status.value == "ready_for_review"
    assert result.incident.current_investigation_id == result.new_investigation.investigation_id

    # prior feedback and the reject transition remain queryable, unmodified
    still_there = db.query(HumanFeedback).filter_by(incident_id=rejected.incident_id).all()
    assert len(still_there) == 1
    assert still_there[0].feedback_text == prior_feedback[0].feedback_text

    reject_transition = db.get(IncidentStatusTransition, reject_transition_id)
    assert reject_transition.to_status == "rejected"  # unmodified


def test_evidence_changed_flag_reflects_reality():
    db = make_test_session()
    rejected = _rejected_incident(db)

    client = always_returns(make_draft())

    # same evidence -> evidence_changed False
    unchanged = recalculate_incident(db, rejected.incident_id, new_evidence=None, mistral_client_override=client)
    assert unchanged.evidence_changed is False

    # need a fresh rejected incident to recalculate again (recalculate
    # only valid from "rejected"; the one above moved to ready_for_review)
    incident2 = create_incident(db, make_incident_create(window_id="W2"), mistral_client_override=client)
    rejected2 = reject_incident(db, incident2.incident_id, "r1", "other", "needs another look")

    identical_evidence = make_evidence()  # same values as make_incident_create's default
    same = recalculate_incident(db, rejected2.incident_id, new_evidence=identical_evidence, mistral_client_override=client)
    assert same.evidence_changed is False

    incident3 = create_incident(db, make_incident_create(window_id="W3"), mistral_client_override=client)
    rejected3 = reject_incident(db, incident3.incident_id, "r1", "other", "needs another look")
    different_evidence = make_evidence(anomaly_score_percentile=0.15, risk_score=0.1)
    changed = recalculate_incident(db, rejected3.incident_id, new_evidence=different_evidence, mistral_client_override=client)
    assert changed.evidence_changed is True
    assert changed.incident.severity_result != rejected3.severity_result
