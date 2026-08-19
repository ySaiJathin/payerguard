"""HITL round-trip: accept -> remediate -> revalidate (spec 015 FR-004,
SC-003).

This is the cross-module round-trip no single prior phase's test covers.
Phase 12 tests accepting, Phase 13 tests remediating, and Phase 14 tests
revalidating -- each in isolation, each against its own fixtures. What
none of them prove is that the three *compose*: that the run_id Phase 13
actually returns is the one Phase 14 will accept, that the status Phase 12
sets is the one Phase 13 requires, and that an incident driven through all
three by real HTTP calls arrives at a terminal status.

Every module boundary here is real. The three routers are mounted on one
app over one shared session, and each stage's input is the previous
stage's actual HTTP response body -- never a hand-built fixture standing
in for it. The spies assert the real service functions ran; they wrap
rather than replace, so nothing is mocked away (FR-004's "real (not
mocked) cross-module calls").

The one seam left patched is `patch_recompute_dependencies`, which swaps
Phase 14's *I/O* boundaries (reading Phase 1 profiling artifacts and
Phase 7/9 model pickles from disk) for small fixture objects, because no
such artifacts exist in this environment. Every actual computation --
GX suite execution, `detector.score`, `model.predict_proba`, Phase 10's
scoring functions -- still runs for real. That is the same seam Phase
14's own router test uses.

The reverse round-trip (reject -> feedback -> recalculate -> re-review)
is deliberately absent: Phase 12's
`tests/hitl/test_router_hitl_flow.py::test_full_create_reject_recalculate_accept_flow`
already covers it end-to-end over real HTTP, and spec FR-009 forbids
duplicating existing coverage.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.hitl.router import router as hitl_router
from app.remediation import remediation_service
from app.remediation.router import router as remediation_router
from app.revalidation import revalidation_service
from app.revalidation.router import router as revalidation_router
from tests._db_fixtures import make_test_session
from tests.revalidation._fixtures import (
    make_anomaly_artifact,
    make_incident,
    make_risk_artifact,
    patch_recompute_dependencies,
)

TERMINAL_STATUSES = {"resolved", "reopened"}

# Mirrors tests/remediation/test_router_remediation_flow.py's payload: one
# claim per deterministic handler, plus one nothing handles (which must
# fall through to Manual Action Required rather than being silently
# dropped or LLM-guessed).
AFFECTED_CLAIMS = [
    {"claim_id": "CLM-DUP", "is_duplicate": True},
    {"claim_id": "CLM-STATUS", "fields": {"PTNT_DSCHRG_STUS_CD": "01"}},
    {"claim_id": "CLM-IMPUTE", "fields": {"ADMTG_DGNS_CD": None}},
    {"claim_id": "CLM-UNHANDLED", "fields": {"PTNT_DSCHRG_STUS_CD": "1", "ADMTG_DGNS_CD": "J45"}},
]


def _revalidation_body(remediation_run_id: str) -> dict:
    return {
        "remediation_run_id": remediation_run_id,
        "current_claims": [
            {
                "claim_id": "1001",
                "raw_fields": {
                    "BENE_ID": "5001",
                    "CLM_FROM_DT": "2015-04-01",
                    "CLM_THRU_DT": "2015-04-05",
                    "CLM_PMT_AMT": 1200.50,
                    "CLM_IP_ADMSN_TYPE_CD": "1",
                    "PRNCPAL_DGNS_CD": "I10",
                    "OT_PHYSN_UPIN": "UPIN001",
                    "CLM_LINE_NUM": "1",
                },
            }
        ],
        "anomaly_features": {"f1": 1.0, "f2": 2.0},
        "risk_features": {"f1": 1.0, "f2": 2.0},
    }


class _Spy:
    """Wraps a real service function so the test can prove it was
    genuinely invoked, without replacing its behaviour."""

    def __init__(self, func):
        self._func = func
        self.call_count = 0

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        return self._func(*args, **kwargs)


@pytest.fixture
def wired(monkeypatch):
    """One app, one session, all three real routers, plus spies on the
    two services whose genuine invocation FR-004 requires proving."""
    db = make_test_session()
    patch_recompute_dependencies(
        monkeypatch,
        make_anomaly_artifact(scores=[0.1], feature_columns=["f1", "f2"]),
        make_risk_artifact(probabilities=[0.05], feature_columns=["f1", "f2"]),
    )

    remediate_spy = _Spy(remediation_service.run_remediation)
    revalidate_spy = _Spy(revalidation_service.run_revalidation)
    monkeypatch.setattr(remediation_service, "run_remediation", remediate_spy)
    monkeypatch.setattr(revalidation_service, "run_revalidation", revalidate_spy)

    app = FastAPI()
    app.include_router(hitl_router)
    app.include_router(remediation_router)
    app.include_router(revalidation_router)
    app.dependency_overrides[get_db] = lambda: db

    return {
        "db": db,
        "client": TestClient(app),
        "remediate_spy": remediate_spy,
        "revalidate_spy": revalidate_spy,
    }


def test_accept_remediate_revalidate_round_trip(wired):
    """SC-003: the full loop end-to-end across Phases 12, 13, and 14."""
    client = wired["client"]
    # `tests.revalidation._fixtures.make_incident` (not remediation's) --
    # Phase 14's recompute needs a populated evidence_snapshot, which
    # remediation's leaner fixture leaves empty.
    incident = make_incident(wired["db"], status="ready_for_review")
    incident_id = incident.incident_id

    # --- Phase 12: accept ---------------------------------------------
    accept = client.post(f"/hitl/{incident_id}/accept", json={"reviewer_id": "r1"})
    assert accept.status_code == 200, accept.text
    assert accept.json()["status"] == "accepted"

    # --- Phase 13: remediate (gated on the status Phase 12 just set) ---
    remediate = client.post(
        f"/remediation/{incident_id}/run", json={"affected_claims": AFFECTED_CLAIMS}
    )
    assert remediate.status_code == 200, remediate.text
    remediation_body = remediate.json()

    handled = {a["claim_id"] for a in remediation_body["actions"]}
    manual = {m["claim_id"] for m in remediation_body["manual_actions_required"]}
    assert handled == {"CLM-DUP", "CLM-STATUS", "CLM-IMPUTE"}
    assert manual == {"CLM-UNHANDLED"}, "The unhandled claim must fall through to Manual Action Required."

    # The run_id handed to Phase 14 is the one Phase 13 actually produced.
    run_id = remediation_body["run_id"]
    assert remediation_body["completed_at"] is not None, (
        "Phase 14 refuses an incomplete run, so the composition depends on Phase 13 "
        "completing synchronously before it returns."
    )

    # --- Phase 14: revalidate -----------------------------------------
    revalidate = client.post(f"/revalidation/{incident_id}/run", json=_revalidation_body(run_id))
    assert revalidate.status_code == 200, revalidate.text
    revalidation_body = revalidate.json()

    assert revalidation_body["revalidation_run"]["remediation_run_id"] == run_id, (
        "Revalidation recorded a different remediation run than the one it was given."
    )
    for section in ("revalidation_run", "comparison", "resolution"):
        assert section in revalidation_body

    # The outcome is asserted as terminal, not as a fixed value: whether
    # this fixture resolves or reopens is a property of the recomputed
    # signals, and pinning it would re-introduce exactly the forced-outcome
    # assumption Phase 14 was built to avoid.
    status = revalidation_body["incident_status"]
    assert status in TERMINAL_STATUSES, f"Expected a terminal status, got {status!r}."

    # The outstanding manual action above must block "resolved" (Phase 14 FR-007).
    assert status == "reopened", (
        "CLM-UNHANDLED left an outstanding manual action, which must prevent resolution."
    )

    # --- the loop is persisted, not just returned ----------------------
    history = client.get(f"/revalidation/{incident_id}")
    assert history.status_code == 200
    assert len(history.json()) == 1

    wired["db"].refresh(incident)
    assert incident.status == status, "The persisted incident status diverged from the response."


def test_all_three_modules_were_really_invoked(wired):
    """FR-004: proves the round trip above crossed real module
    boundaries. If a future refactor short-circuited remediation or
    revalidation, the flow test could still pass on cached rows while
    this one fails."""
    client = wired["client"]
    incident = make_incident(wired["db"], status="ready_for_review")
    incident_id = incident.incident_id

    client.post(f"/hitl/{incident_id}/accept", json={"reviewer_id": "r1"})
    run_id = client.post(
        f"/remediation/{incident_id}/run", json={"affected_claims": AFFECTED_CLAIMS}
    ).json()["run_id"]
    client.post(f"/revalidation/{incident_id}/run", json=_revalidation_body(run_id))

    assert wired["remediate_spy"].call_count == 1, "Phase 13's real service was not invoked."
    assert wired["revalidate_spy"].call_count == 1, "Phase 14's real service was not invoked."


def test_revalidation_refuses_a_run_from_a_different_incident(wired):
    """The composition must not be loose enough to revalidate incident A
    against incident B's remediation run -- a cross-incident mix-up would
    attribute one incident's fixes to another."""
    client = wired["client"]
    first = make_incident(wired["db"], status="ready_for_review")
    second = make_incident(wired["db"], status="ready_for_review")

    client.post(f"/hitl/{first.incident_id}/accept", json={"reviewer_id": "r1"})
    client.post(f"/hitl/{second.incident_id}/accept", json={"reviewer_id": "r1"})
    first_run_id = client.post(
        f"/remediation/{first.incident_id}/run", json={"affected_claims": AFFECTED_CLAIMS}
    ).json()["run_id"]

    crossed = client.post(
        f"/revalidation/{second.incident_id}/run", json=_revalidation_body(first_run_id)
    )

    assert crossed.status_code == 409, (
        f"Revalidating one incident against another's remediation run must be refused, "
        f"got {crossed.status_code}."
    )


def test_remediation_before_accept_is_refused(wired):
    """The ordering the round trip depends on is enforced, not
    conventional: Phase 13 must reject an incident Phase 12 hasn't
    accepted yet."""
    client = wired["client"]
    incident = make_incident(wired["db"], status="ready_for_review")

    premature = client.post(
        f"/remediation/{incident.incident_id}/run", json={"affected_claims": AFFECTED_CLAIMS}
    )

    assert premature.status_code == 409
