"""US2 Acceptance Scenarios 1-2 (spec.md): unmatched conditions are
explicitly marked Manual Action Required, and a mix of handleable/
unhandleable conditions doesn't let one block the other.
"""

from app.remediation import precedence
from app.remediation.remediation_service import _process_claim
from app.remediation.schemas import ManualActionRequired, ReasonCode, RemediationAction
from tests.remediation._fixtures import make_claim


def test_claim_matching_no_rule_is_flagged_manual_action_required():
    rule_tables = precedence.load_rule_tables()
    claim = make_claim(claim_id="CLM-UNMATCHED", fields={"PTNT_DSCHRG_STUS_CD": "1", "ADMTG_DGNS_CD": "J45"})

    result = _process_claim(claim, rule_tables, incident_id="INC1")

    assert isinstance(result, ManualActionRequired)
    assert result.incident_id == "INC1"
    assert result.claim_id == "CLM-UNMATCHED"
    assert result.reason_code == ReasonCode.no_matching_rule
    assert "CLM-UNMATCHED" in result.description


def test_mixed_batch_remediates_matched_claims_without_blocking_on_unmatched():
    rule_tables = precedence.load_rule_tables()
    claims = [
        make_claim(claim_id="CLM-DUP", is_duplicate=True),
        make_claim(claim_id="CLM-UNMATCHED", fields={"PTNT_DSCHRG_STUS_CD": "1", "ADMTG_DGNS_CD": "J45"}),
        make_claim(claim_id="CLM-IMPUTE", fields={"ADMTG_DGNS_CD": None}),
    ]

    results = {claim.claim_id: _process_claim(claim, rule_tables, incident_id="INC1") for claim in claims}

    assert isinstance(results["CLM-DUP"], RemediationAction)
    assert isinstance(results["CLM-IMPUTE"], RemediationAction)
    assert isinstance(results["CLM-UNMATCHED"], ManualActionRequired)
    assert results["CLM-UNMATCHED"].reason_code == ReasonCode.no_matching_rule
