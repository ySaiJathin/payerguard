"""US1 Acceptance Scenarios 1-3 (spec.md) and FR-007's precedence order.

Exercises `precedence.select_rule` directly against the real YAML rule
tables under backend/app/remediation/config/ -- no DB, no HTTP.
"""

from app.remediation import precedence
from app.remediation.schemas import HandlerType
from tests.remediation._fixtures import make_claim


def test_duplicate_claim_selects_duplicate_flagging_rule():
    rule_tables = precedence.load_rule_tables()
    claim = make_claim(is_duplicate=True)

    selected = precedence.select_rule(claim, rule_tables)

    assert selected is not None
    assert selected.rule_id == "dup-001"
    assert selected.handler_type == HandlerType.duplicate_flagging


def test_missing_admitting_diagnosis_selects_imputation_rule():
    rule_tables = precedence.load_rule_tables()
    claim = make_claim(fields={"ADMTG_DGNS_CD": None})

    selected = precedence.select_rule(claim, rule_tables)

    assert selected is not None
    assert selected.rule_id == "imp-001"
    assert selected.handler_type == HandlerType.approved_imputation


def test_leading_zero_discharge_status_selects_status_mapping_rule():
    rule_tables = precedence.load_rule_tables()
    claim = make_claim(fields={"PTNT_DSCHRG_STUS_CD": "01"})

    selected = precedence.select_rule(claim, rule_tables)

    assert selected is not None
    assert selected.rule_id == "stat-001"
    assert selected.handler_type == HandlerType.approved_status_mapping


def test_no_matching_condition_selects_nothing():
    rule_tables = precedence.load_rule_tables()
    claim = make_claim(fields={"PTNT_DSCHRG_STUS_CD": "1", "ADMTG_DGNS_CD": "J45"})

    assert precedence.select_rule(claim, rule_tables) is None


def test_precedence_prefers_duplicate_flagging_over_status_mapping():
    """FR-007: when a claim satisfies both the duplicate-flagging and
    status-mapping preconditions, the documented precedence order picks
    duplicate flagging (precedence_rank 1, least invasive) over status
    mapping (precedence_rank 2), never an arbitrary choice."""
    rule_tables = precedence.load_rule_tables()
    claim = make_claim(is_duplicate=True, fields={"PTNT_DSCHRG_STUS_CD": "01"})

    selected = precedence.select_rule(claim, rule_tables)

    assert selected is not None
    assert selected.rule_id == "dup-001"
