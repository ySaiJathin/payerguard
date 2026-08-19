"""Loads the three versioned rule tables and selects the correct handler
for a claim, applying FR-007's documented precedence order (spec
FR-001, FR-007; research.md).

Precedence is invasiveness-based, lowest number applied first: duplicate
flagging (1, non-destructive/reversible) before approved status mapping
(2, a single known-correct categorical change) before approved
imputation (3, the most invasive -- it fills a genuine gap rather than
correcting/flagging an existing value). When more than one handler could
plausibly apply to the same claim, the lower `precedence_rank` wins --
never an arbitrary/undocumented choice.
"""

from pathlib import Path

import yaml

from app.remediation import duplicate_handler, imputation_handler, status_mapping_handler
from app.remediation.schemas import AffectedClaimInput, HandlerType, RemediationRule

HANDLER_MODULES = {
    HandlerType.duplicate_flagging: duplicate_handler,
    HandlerType.approved_status_mapping: status_mapping_handler,
    HandlerType.approved_imputation: imputation_handler,
}

_RULE_FILES = {
    HandlerType.duplicate_flagging: "duplicate_flagging_rules.yaml",
    HandlerType.approved_status_mapping: "status_mapping_rules.yaml",
    HandlerType.approved_imputation: "imputation_rules.yaml",
}


def _config_dir() -> Path:
    return Path(__file__).resolve().parent / "config"


def load_rule_tables() -> dict[HandlerType, list[RemediationRule]]:
    rule_tables: dict[HandlerType, list[RemediationRule]] = {}
    for handler_type, filename in _RULE_FILES.items():
        with open(_config_dir() / filename, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        version = raw["version"]
        rule_tables[handler_type] = [
            RemediationRule(handler_type=handler_type, rule_table_version=version, **entry)
            for entry in raw["rules"]
        ]
    return rule_tables


def select_rule(
    claim: AffectedClaimInput, rule_tables: dict[HandlerType, list[RemediationRule]]
) -> RemediationRule | None:
    candidates: list[RemediationRule] = []
    for handler_type, rules in rule_tables.items():
        handler = HANDLER_MODULES[handler_type]
        for rule in rules:
            if handler.matches(claim, rule):
                candidates.append(rule)

    if not candidates:
        return None
    return min(candidates, key=lambda rule: rule.precedence_rank)
