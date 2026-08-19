"""LLM category / hallucination, unsupported claims, and
incorrect-recommendation detection (spec 015 FR-007).

**Documented limitation (spec Assumptions, FR-007, SC-006).** This is not
a general-purpose hallucination classifier -- no such classifier is in
scope for this MVP, and claiming otherwise would overstate what these
tests prove. What they do check is the most common and most consequential
form of hallucination for this use case: the model citing a specific
claim ID or dollar figure that was never in the evidence it was given.
Every citation is traced back to the `StructuredIncidentPayload` the
investigation actually received; a citation that doesn't trace is
reported as ungrounded.

Per research.md the grounding check *flags* rather than hard-fails on an
unverifiable citation, because a best-effort tracer will always have
false positives (prose that looks like a citation but isn't). So the
assertions below are on the tracer correctly flagging or not flagging --
not on `investigate()` itself raising.

The fourth LLM scenario, insufficient-evidence handling, is deliberately
absent here: Phase 11 SC-002 already covers it in
`tests/llm/test_insufficient_evidence.py`, and spec FR-009 forbids
duplicating existing coverage.
"""

import re

import pytest

from app.llm.schemas import InvestigationDraft, StructuredIncidentPayload
from app.llm.payload_builder import build_payload
from tests.llm._fixtures import make_severity_and_impact

# A dollar figure is "traceable" if it matches a payload value to the cent.
# Rounding tolerance is deliberately tight: the point is to catch invented
# figures, and a loose tolerance would let a fabricated number match a real
# one by coincidence.
AMOUNT_TOLERANCE = 0.01

CLAIM_ID_PATTERN = re.compile(r"\bC\d+\b")
AMOUNT_PATTERN = re.compile(r"\$?\d+\.\d{2}\b")


def _payload() -> StructuredIncidentPayload:
    """A payload with a known, small `affected_claims_sample` so every
    citation in the drafts below is unambiguously groundable or not."""
    severity_result, business_impact_result = make_severity_and_impact()
    return build_payload(
        incident_context={"window_id": "W1", "window_start": "2020-01-01", "window_end": "2020-01-07"},
        quality_check_results=[{"check_id": "chk-1", "band": "CRITICAL", "column_name": "CLM_DRG_CD"}],
        anomaly_evidence={"anomaly_score": 0.97, "model_used": "hbos"},
        risk_evidence={"risk_score": 0.72, "model_type": "xgboost"},
        severity_result=severity_result,
        business_impact_result=business_impact_result,
        affected_claims_sample=[
            {"claim_id": "C1", "amount": 1200.50},
            {"claim_id": "C2", "amount": 340.25},
        ],
    )


def _known_claim_ids(payload: StructuredIncidentPayload) -> set[str]:
    return {str(claim["claim_id"]) for claim in payload.affected_claims_sample if "claim_id" in claim}


def _known_amounts(payload: StructuredIncidentPayload) -> list[float]:
    return [float(claim["amount"]) for claim in payload.affected_claims_sample if "amount" in claim]


def find_ungrounded_citations(text: str, payload: StructuredIncidentPayload) -> list[str]:
    """Returns every claim ID / dollar figure cited in `text` that cannot
    be traced to `payload`. An empty list means fully grounded.

    This is the best-effort tracer FR-007 describes -- it recognizes the
    two citation forms this pipeline's evidence actually contains (claim
    IDs and amounts), not arbitrary factual assertions in prose.
    """
    known_ids = _known_claim_ids(payload)
    known_amounts = _known_amounts(payload)

    ungrounded = []
    for cited_id in CLAIM_ID_PATTERN.findall(text):
        if cited_id not in known_ids:
            ungrounded.append(cited_id)
    for cited_amount in AMOUNT_PATTERN.findall(text):
        value = float(cited_amount.lstrip("$"))
        if not any(abs(value - known) <= AMOUNT_TOLERANCE for known in known_amounts):
            ungrounded.append(cited_amount)
    return ungrounded


@pytest.fixture(scope="module")
def payload() -> StructuredIncidentPayload:
    return _payload()


def test_grounded_evidence_citations_all_trace_to_the_payload(payload):
    """The favourable case: every claim ID and amount the draft cites is
    genuinely present in the evidence it was given."""
    draft = InvestigationDraft(
        summary="Window W1 shows repeated quality failures.",
        likely_root_cause="A CRITICAL GX failure on CLM_DRG_CD.",
        evidence="Claims C1 ($1200.50) and C2 ($340.25) both failed the CLM_DRG_CD check.",
        business_impact_narrative="Two sampled claims are affected.",
        recommended_fix="Review CLM_DRG_CD entry for C1 and C2.",
        prevention_recommendation="Add upstream validation for CLM_DRG_CD.",
    )

    assert find_ungrounded_citations(draft.evidence, payload) == []
    assert find_ungrounded_citations(draft.recommended_fix, payload) == []


def test_hallucinated_claim_id_in_evidence_is_flagged(payload):
    """FR-007 hallucination scenario: the model invents a claim ID that
    was never in the payload."""
    draft_evidence = "Claims C1 and C99 both failed the CLM_DRG_CD check."

    ungrounded = find_ungrounded_citations(draft_evidence, payload)

    assert "C99" in ungrounded, "An invented claim ID was not flagged as ungrounded."
    assert "C1" not in ungrounded, "A genuine claim ID was wrongly flagged."


def test_unsupported_dollar_figure_in_evidence_is_flagged(payload):
    """FR-007 unsupported-claims scenario: the narrative asserts a dollar
    figure that appears nowhere in the evidence."""
    draft_evidence = "Total exposure across the sampled claims is $98765.43."

    ungrounded = find_ungrounded_citations(draft_evidence, payload)

    assert "$98765.43" in ungrounded, "A fabricated dollar figure was not flagged as ungrounded."


def test_recommendation_citing_absent_claim_is_flagged(payload):
    """FR-007 incorrect-recommendation detection, explicitly distinct
    from hallucination: the *evidence* section may be perfectly grounded
    while the proposed action targets a claim that was never in scope.
    Acting on such a recommendation would touch the wrong records, so it
    is checked separately rather than assumed safe."""
    draft = InvestigationDraft(
        summary="Window W1 shows repeated quality failures.",
        likely_root_cause="A CRITICAL GX failure on CLM_DRG_CD.",
        evidence="Claim C1 ($1200.50) failed the CLM_DRG_CD check.",
        business_impact_narrative="One sampled claim is affected.",
        recommended_fix="Reprocess claims C1 and C404 to correct CLM_DRG_CD.",
        prevention_recommendation="Add upstream validation for CLM_DRG_CD.",
    )

    assert find_ungrounded_citations(draft.evidence, payload) == [], (
        "Precondition failed: this test needs grounded evidence so the flag can be attributed "
        "to the recommendation specifically."
    )
    assert "C404" in find_ungrounded_citations(draft.recommended_fix, payload), (
        "A recommendation targeting a claim absent from the evidence was not flagged."
    )


def test_prevention_recommendation_is_checked_too(payload):
    """The same tracer applies to the sixth section -- an ungrounded
    citation there is no more acceptable than in `recommended_fix`."""
    prevention = "Backfill validation for the C7 cohort."

    assert "C7" in find_ungrounded_citations(prevention, payload)


def test_tracer_does_not_flag_prose_without_citations(payload):
    """Guards against a tracer so aggressive it flags ordinary narrative
    text, which would make every result noise and the check worthless."""
    prose = "The window shows a systematic upstream coding error affecting several claims."

    assert find_ungrounded_citations(prose, payload) == []
