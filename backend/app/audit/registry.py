"""Audit-source registry and its completeness check (spec FR-008, SC-005).

The point of this module is that a *new or modified pipeline stage cannot
silently skip auditing*. `EXPECTED_AUDITED_MODULES` names every module
that produces a decision, score, or action; `check_registry_completeness`
reports which of them have actually contributed at least one real audit
entry. `backend/tests/audit/test_registry_completeness.py` turns that into
a failing test, which is what the spec requires -- a documented intention
would not survive a refactor, an executable check does.
"""

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.audit.schemas import AuditSourceRegistryEntry

# Every module producing a decision/score/action, mapped to the record
# types it contributes. Two deliberate departures from research.md's
# original list, both decided explicitly rather than drifted into:
#
# 1. `ingestion` is PRESENT. Through Phase 16 it was absent -- continuous
#    ingestion was removed 2026-08-18 and `app/ingestion/` had no write
#    path to instrument, so keeping it would have failed permanently and
#    trained readers to ignore a red test. Spec 017-batch-file-ingestion
#    (2026-08-20) built a real one: `app.ingestion.batch_service` appends
#    one entry per accepted or rejected upload, so this is re-added now
#    that a genuine write path exists.
#
# 2. `data_engineering` is PRESENT. research.md's list omits it, but
#    FR-001 explicitly names "Phase 2's QualityIssueRecord" as an
#    aggregated source and User Story 1's first acceptance scenario is
#    entirely about a Phase 2 cleaning correction appearing in a claim's
#    trail. Following the list literally would leave this feature unable
#    to satisfy its own P1 scenario. Phase 2 is not among the
#    pure-computation modules spec Assumptions exclude (profiling, feature
#    engineering, feature selection).
EXPECTED_AUDITED_MODULES: dict[str, list[str]] = {
    "data_engineering": ["QualityIssueRecord"],
    "quality": ["ExpectationCheckResult"],
    "anomaly": ["BenchmarkRunResult"],
    "risk": ["RiskBenchmarkRunResult"],
    "risk.scoring": ["SeverityResult", "BusinessImpactResult", "PriorityResult"],
    "llm": ["LLMInvestigation"],
    "incidents": ["Incident"],
    "hitl": ["IncidentStatusTransition", "HumanFeedback"],
    "remediation": ["RemediationAction", "ManualActionRequired"],
    "revalidation": ["RevalidationRun"],
    "ingestion": ["IngestedBatch"],
}


def registered_modules(db: Session) -> set[str]:
    """The modules that have actually written at least one audit entry --
    observed from the log itself, never from a declaration, so a module
    that merely *claims* to audit cannot pass the check."""
    rows = db.execute(select(distinct(AuditLog.source_module))).scalars().all()
    return set(rows)


def check_registry_completeness(
    db: Session, expected: dict[str, list[str]] | None = None
) -> list[AuditSourceRegistryEntry]:
    """One entry per expected module, `registered=True` iff a real audit
    row from it exists. `expected` is injectable so the completeness test
    can prove the check actually catches an unregistered module rather
    than passing vacuously."""
    expected = EXPECTED_AUDITED_MODULES if expected is None else expected
    actual = registered_modules(db)
    return [
        AuditSourceRegistryEntry(
            module_name=module,
            record_types_contributed=record_types,
            registered=module in actual,
        )
        for module, record_types in expected.items()
    ]


def unregistered_modules(
    db: Session, expected: dict[str, list[str]] | None = None
) -> list[str]:
    """Convenience for the test and any future CI gate: just the gaps."""
    return [e.module_name for e in check_registry_completeness(db, expected) if not e.registered]
