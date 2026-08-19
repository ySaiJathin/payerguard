"""Spec SC-006 / Edge Cases: a handler selected for a claim whose
precondition is invalidated before execution (e.g. a race with
re-ingestion) falls back to Manual Action Required instead of blindly
applying a now-stale action.
"""

from app.remediation import precedence
from app.remediation.remediation_service import _process_claim
from app.remediation.schemas import ManualActionRequired, ReasonCode, RemediationAction
from tests.remediation._fixtures import make_claim


def test_status_mapping_precondition_invalidated_before_execution_falls_back_to_manual():
    rule_tables = precedence.load_rule_tables()
    claim = make_claim(claim_id="CLM-RACE", fields={"PTNT_DSCHRG_STUS_CD": "01"})

    # Confirm the rule would have been selected under the original condition.
    selected = precedence.select_rule(claim, rule_tables)
    assert selected is not None
    assert selected.rule_id == "stat-001"

    # Simulate the precondition no longer holding by the time execution
    # actually runs (e.g. a concurrent re-ingestion already corrected the
    # column) -- _process_claim must re-verify against the claim's
    # current state, not reuse the stale selection. `preselected_rule`
    # models "this handler was already chosen, now execute it" so the
    # re-verification path is exercised honestly rather than masked by
    # select_rule silently finding no candidate at all.
    claim.fields["PTNT_DSCHRG_STUS_CD"] = "1"

    result = _process_claim(claim, rule_tables, incident_id="INC1", preselected_rule=selected)

    assert isinstance(result, ManualActionRequired)
    assert result.reason_code == ReasonCode.precondition_invalidated
    assert "stat-001" in result.description


def test_imputation_precondition_invalidated_before_execution_falls_back_to_manual():
    rule_tables = precedence.load_rule_tables()
    claim = make_claim(claim_id="CLM-RACE2", fields={"ADMTG_DGNS_CD": None})

    selected = precedence.select_rule(claim, rule_tables)
    assert selected is not None
    assert selected.rule_id == "imp-001"

    # The field got populated between selection and execution.
    claim.fields["ADMTG_DGNS_CD"] = "J45"

    result = _process_claim(claim, rule_tables, incident_id="INC1", preselected_rule=selected)

    assert isinstance(result, ManualActionRequired)
    assert result.reason_code == ReasonCode.precondition_invalidated


def test_precondition_still_valid_produces_a_real_action_not_a_manual_fallback():
    """Sanity check: the revalidation path doesn't fire a false positive
    when nothing has actually changed."""
    rule_tables = precedence.load_rule_tables()
    claim = make_claim(claim_id="CLM-OK", is_duplicate=True)

    result = _process_claim(claim, rule_tables, incident_id="INC1")

    assert isinstance(result, RemediationAction)
