import pytest

from app.hitl.errors import InvalidTransitionError
from app.hitl.state_machine import TRANSITIONS, validate_transition

ALL_STATUSES = list(TRANSITIONS.keys())
ALL_ACTIONS = {"accept", "reject", "recalculate"}


def test_every_declared_transition_is_valid():
    for from_status, actions in TRANSITIONS.items():
        for action, to_statuses in actions.items():
            result = validate_transition(from_status, action)
            assert result == to_statuses


@pytest.mark.parametrize("from_status", ALL_STATUSES)
@pytest.mark.parametrize("action", sorted(ALL_ACTIONS))
def test_every_undeclared_action_raises_invalid_transition(from_status, action):
    legal_actions = TRANSITIONS[from_status]
    if action in legal_actions:
        pytest.skip("declared transition, covered by test_every_declared_transition_is_valid")
    with pytest.raises(InvalidTransitionError):
        validate_transition(from_status, action)


def test_double_accept_is_rejected():
    validate_transition("ready_for_review", "accept")  # first accept is legal
    with pytest.raises(InvalidTransitionError):
        validate_transition("accepted", "accept")  # second is not


def test_reject_after_accept_is_rejected():
    with pytest.raises(InvalidTransitionError):
        validate_transition("accepted", "reject")


def test_accepting_a_rejected_incident_without_recalculation_is_rejected():
    with pytest.raises(InvalidTransitionError):
        validate_transition("rejected", "accept")


def test_unknown_status_is_rejected():
    with pytest.raises(InvalidTransitionError):
        validate_transition("not_a_real_status", "accept")
