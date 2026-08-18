"""Shared fixture builders for llm tests -- not a test module itself (no
`test_` prefix, so pytest doesn't collect it)."""

from app.llm.schemas import InvestigationDraft, StructuredIncidentPayload
from app.risk.scoring.business_impact import compute_business_impact
from app.risk.scoring.severity import compute_severity


def make_severity_and_impact():
    severity_result = compute_severity(
        quality_check_bands=["CRITICAL", "CRITICAL", "WARNING"],
        anomaly_score_percentile=0.97,
        affected_claim_pct=0.25,
    )
    business_impact_result = compute_business_impact(affected_claims_amounts=[])  # no baseline -> unavailable
    return severity_result, business_impact_result


def make_payload() -> StructuredIncidentPayload:
    from app.llm.payload_builder import build_payload

    severity_result, business_impact_result = make_severity_and_impact()
    return build_payload(
        incident_context={"window_id": "W1", "window_start": "2020-01-01", "window_end": "2020-01-07"},
        quality_check_results=[
            {"check_id": "chk-1", "band": "CRITICAL", "column_name": "CLM_DRG_CD"},
            {"check_id": "chk-2", "band": "WARNING", "column_name": "PRVDR_NUM"},
        ],
        anomaly_evidence={"anomaly_score": 0.97, "model_used": "hbos"},
        risk_evidence={"risk_score": 0.72, "model_type": "xgboost"},
        severity_result=severity_result,
        business_impact_result=business_impact_result,
        affected_claims_sample=[{"claim_id": "C1", "amount": 1200.5}],
    )


def make_draft(
    likely_root_cause: str = "Two CRITICAL GX checks (CLM_DRG_CD, PRVDR_NUM) coincide with a high anomaly score.",
) -> InvestigationDraft:
    return InvestigationDraft(
        summary="Window W1 shows repeated quality failures and a high anomaly score.",
        likely_root_cause=likely_root_cause,
        evidence="2 CRITICAL GX checks failed; anomaly percentile 0.97; risk score 0.72.",
        business_impact_narrative="Dollar exposure is unavailable for this window; affected claims sampled.",
        recommended_fix="Review CLM_DRG_CD and PRVDR_NUM entry for affected claims.",
        prevention_recommendation="Add upstream validation for provider number format.",
    )


class _FakeMessage:
    def __init__(self, parsed):
        self.parsed = parsed


class _FakeChoice:
    def __init__(self, parsed):
        self.message = _FakeMessage(parsed)


class _FakeResponse:
    def __init__(self, parsed):
        self.choices = [_FakeChoice(parsed)]


class FakeChat:
    def __init__(self, behavior):
        self._behavior = behavior
        self.call_count = 0

    def parse(self, **kwargs):
        self.call_count += 1
        result = self._behavior(self.call_count)
        if isinstance(result, Exception):
            raise result
        return _FakeResponse(result)


class FakeMistralClient:
    """Minimal stand-in for `mistralai.client.Mistral`, exposing only the
    `.chat.parse(...)` surface `mistral_client.call_mistral` uses.
    `behavior(call_count) -> InvestigationDraft | Exception` lets tests
    script failure-then-success sequences for retry testing."""

    def __init__(self, behavior):
        self.chat = FakeChat(behavior)


def always_returns(draft: InvestigationDraft) -> FakeMistralClient:
    return FakeMistralClient(lambda call_count: draft)


def always_raises(exc: Exception) -> FakeMistralClient:
    return FakeMistralClient(lambda call_count: exc)


def fails_then_succeeds(exc: Exception, draft: InvestigationDraft) -> FakeMistralClient:
    return FakeMistralClient(lambda call_count: exc if call_count == 1 else draft)
