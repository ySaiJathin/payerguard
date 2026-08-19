"""Orchestrates remediation for an accepted incident (spec FR-002, FR-003,
FR-006, FR-008, FR-009, FR-010).

`_process_claim` is the pure claim-level decision function -- selection,
precondition re-verification, apply-or-fall-back-to-manual -- with no DB
access and no accepted-status gate; it's usable standalone (US2's tests
call it directly) and is the building block `run_remediation` wraps with
the full accepted-gate/scope/idempotency/conflict machinery (US3).
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.incidents.service import get_incident_orm
from app.remediation import manual_handler, precedence
from app.remediation.errors import NotAcceptedIncidentError
from app.remediation.models import ManualActionRequired as ManualActionRequiredORM
from app.remediation.models import RemediationAction as RemediationActionORM
from app.remediation.models import RemediationRun as RemediationRunORM
from app.remediation.models import RemediationRunReusedAction
from app.remediation.precedence import HANDLER_MODULES
from app.remediation.schemas import (
    AffectedClaimInput,
    HandlerType,
    ManualActionRequired,
    ReasonCode,
    RemediationAction,
    RemediationRule,
    RemediationRun,
)


def _process_claim(
    claim: AffectedClaimInput,
    rule_tables: dict[HandlerType, list[RemediationRule]],
    incident_id: str,
    *,
    preselected_rule: RemediationRule | None = None,
) -> RemediationAction | ManualActionRequired:
    """`preselected_rule` lets a caller supply a rule chosen at an
    earlier point against a possibly-since-changed claim snapshot
    (FR-006's race scenario: a handler is selected, then the affected
    claim's real-world state moves on before execution actually reaches
    it) -- when omitted, selection happens fresh against `claim` as
    normal. Either way, `verify_precondition` always re-checks against
    the `claim` passed in *here*, immediately before applying, never a
    stale snapshot from selection time."""
    rule = preselected_rule if preselected_rule is not None else precedence.select_rule(claim, rule_tables)
    if rule is None:
        return manual_handler.flag_manual_action(
            incident_id,
            claim.claim_id,
            ReasonCode.no_matching_rule,
            f"No approved handler matches the current condition for claim {claim.claim_id}.",
        )

    handler = HANDLER_MODULES[rule.handler_type]
    if not handler.verify_precondition(claim, rule):
        return manual_handler.flag_manual_action(
            incident_id,
            claim.claim_id,
            ReasonCode.precondition_invalidated,
            f"Handler {rule.rule_id} was selected for claim {claim.claim_id} but its "
            "precondition no longer held at execution time.",
        )

    before_value, after_value = handler.apply(claim, rule)
    return RemediationAction(
        action_id=str(uuid4()),
        incident_id=incident_id,
        claim_id=claim.claim_id,
        rule_id=rule.rule_id,
        before_value=before_value,
        after_value=after_value,
        applied_at=datetime.now(timezone.utc),
    )


def _find_conflicting_action(db: Session, incident_id: str, claim_id: str) -> RemediationActionORM | None:
    """FR-010: a claim already touched by a *different* incident's
    remediation must not be silently overwritten/interfered with by this
    incident's run -- flagged as an explicit conflict instead. This is a
    sequenced check (does another incident already have an action on
    this claim), appropriate for this synchronous, single-process MVP
    service, not a distributed lock (research.md)."""
    stmt = select(RemediationActionORM).where(
        RemediationActionORM.claim_id == claim_id,
        RemediationActionORM.incident_id != incident_id,
    )
    return db.execute(stmt).scalars().first()


def _find_existing_action(db: Session, incident_id: str, claim_id: str, rule_id: str) -> RemediationActionORM | None:
    """FR-008/SC-005 idempotency key: (incident_id, claim_id, rule_id).
    Re-running remediation on an incident with some already-completed
    handlers resumes rather than re-applies them."""
    stmt = select(RemediationActionORM).where(
        RemediationActionORM.incident_id == incident_id,
        RemediationActionORM.claim_id == claim_id,
        RemediationActionORM.rule_id == rule_id,
    )
    return db.execute(stmt).scalars().first()


def run_remediation(db: Session, incident_id: str, affected_claims: list[AffectedClaimInput]) -> RemediationRun:
    incident_orm = get_incident_orm(db, incident_id)
    if incident_orm is None:
        raise LookupError(f"Unknown incident_id {incident_id!r}.")
    if incident_orm.status != "accepted":
        raise NotAcceptedIncidentError(
            f"Incident {incident_id!r} has status {incident_orm.status!r}, not 'accepted' -- "
            "remediation refuses to execute against a non-accepted incident (spec FR-002)."
        )

    rule_tables = precedence.load_rule_tables()
    run_id = str(uuid4())
    started_at = datetime.now(timezone.utc)
    run_orm = RemediationRunORM(run_id=run_id, incident_id=incident_id, started_at=started_at, completed_at=None)
    db.add(run_orm)

    actions: list[RemediationAction] = []
    manual_actions: list[ManualActionRequired] = []

    for claim in affected_claims:
        conflict = _find_conflicting_action(db, incident_id, claim.claim_id)
        if conflict is not None:
            manual = manual_handler.flag_manual_action(
                incident_id,
                claim.claim_id,
                ReasonCode.concurrent_incident_conflict,
                f"Claim {claim.claim_id} already has a remediation action from a different "
                f"incident ({conflict.incident_id}) -- flagged instead of proceeding.",
            )
            db.add(
                ManualActionRequiredORM(
                    record_id=manual.record_id,
                    run_id=run_id,
                    incident_id=manual.incident_id,
                    claim_id=manual.claim_id,
                    description=manual.description,
                    reason_code=manual.reason_code.value,
                    flagged_at=manual.flagged_at,
                )
            )
            manual_actions.append(manual)
            continue

        rule = precedence.select_rule(claim, rule_tables)
        if rule is not None:
            existing = _find_existing_action(db, incident_id, claim.claim_id, rule.rule_id)
            if existing is not None:
                # Idempotent resume (FR-008/SC-005): don't re-apply, but
                # still link this run to the earlier action so this run's
                # own persisted record satisfies FR-009/SC-003's per-run
                # completeness rule for the claim (see
                # RemediationRunReusedAction's docstring in models.py).
                db.add(RemediationRunReusedAction(id=str(uuid4()), run_id=run_id, action_id=existing.action_id))
                actions.append(RemediationAction.model_validate(existing))
                continue

        result = _process_claim(claim, rule_tables, incident_id, preselected_rule=rule)
        if isinstance(result, RemediationAction):
            db.add(
                RemediationActionORM(
                    action_id=result.action_id,
                    run_id=run_id,
                    incident_id=result.incident_id,
                    claim_id=result.claim_id,
                    rule_id=result.rule_id,
                    before_value=result.before_value,
                    after_value=result.after_value,
                    applied_at=result.applied_at,
                )
            )
            actions.append(result)
        else:
            db.add(
                ManualActionRequiredORM(
                    record_id=result.record_id,
                    run_id=run_id,
                    incident_id=result.incident_id,
                    claim_id=result.claim_id,
                    description=result.description,
                    reason_code=result.reason_code.value,
                    flagged_at=result.flagged_at,
                )
            )
            manual_actions.append(result)

    completed_at = datetime.now(timezone.utc)
    run_orm.completed_at = completed_at
    db.commit()

    return RemediationRun(
        run_id=run_id,
        incident_id=incident_id,
        actions=actions,
        manual_actions_required=manual_actions,
        started_at=started_at,
        completed_at=completed_at,
    )


def list_remediation_runs(db: Session, incident_id: str) -> list[RemediationRun]:
    run_rows = (
        db.execute(
            select(RemediationRunORM).where(RemediationRunORM.incident_id == incident_id).order_by(RemediationRunORM.started_at)
        )
        .scalars()
        .all()
    )

    runs: list[RemediationRun] = []
    for run_orm in run_rows:
        action_rows = (
            db.execute(select(RemediationActionORM).where(RemediationActionORM.run_id == run_orm.run_id)).scalars().all()
        )

        # Actions this run resumed rather than newly created (idempotent
        # re-run) -- resolved via RemediationRunReusedAction so this
        # run's own record still shows every claim it processed, per
        # data-model.md's per-run completeness rule.
        reused_action_ids = (
            db.execute(
                select(RemediationRunReusedAction.action_id).where(RemediationRunReusedAction.run_id == run_orm.run_id)
            )
            .scalars()
            .all()
        )
        reused_rows = (
            db.execute(select(RemediationActionORM).where(RemediationActionORM.action_id.in_(reused_action_ids)))
            .scalars()
            .all()
            if reused_action_ids
            else []
        )

        manual_rows = (
            db.execute(select(ManualActionRequiredORM).where(ManualActionRequiredORM.run_id == run_orm.run_id))
            .scalars()
            .all()
        )
        runs.append(
            RemediationRun(
                run_id=run_orm.run_id,
                incident_id=run_orm.incident_id,
                actions=[RemediationAction.model_validate(row) for row in (*action_rows, *reused_rows)],
                manual_actions_required=[ManualActionRequired.model_validate(row) for row in manual_rows],
                started_at=run_orm.started_at,
                completed_at=run_orm.completed_at,
            )
        )
    return runs
