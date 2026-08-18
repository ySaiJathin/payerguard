from app.llm.payload_builder import build_payload, compute_evidence_snapshot_id
from tests.llm._fixtures import make_payload, make_severity_and_impact


def test_unavailable_business_impact_components_are_explicit_strings_not_zero():
    payload = make_payload()
    components = payload.severity_business_impact["business_impact_components"]

    # compute_business_impact([]) marks dollar_exposure/member_harm/
    # provider_reputation all unavailable -- none should appear as 0 or
    # be silently dropped from the payload.
    for name in ("dollar_exposure", "member_harm_impact", "provider_reputation_impact"):
        assert name in components
        assert components[name] != 0
        assert isinstance(components[name], str)
        assert components[name].startswith("unavailable -")


def test_evidence_snapshot_id_is_deterministic_for_identical_content():
    severity_result, business_impact_result = make_severity_and_impact()

    payload_1 = build_payload(
        incident_context={"window_id": "W1"},
        quality_check_results=[{"check_id": "chk-1", "band": "CRITICAL"}],
        anomaly_evidence={"anomaly_score": 0.9},
        risk_evidence={"risk_score": 0.5},
        severity_result=severity_result,
        business_impact_result=business_impact_result,
    )
    payload_2 = build_payload(
        incident_context={"window_id": "W1"},
        quality_check_results=[{"check_id": "chk-1", "band": "CRITICAL"}],
        anomaly_evidence={"anomaly_score": 0.9},
        risk_evidence={"risk_score": 0.5},
        severity_result=severity_result,
        business_impact_result=business_impact_result,
    )

    assert compute_evidence_snapshot_id(payload_1) == compute_evidence_snapshot_id(payload_2)

    payload_3 = build_payload(
        incident_context={"window_id": "W2"},  # different content
        quality_check_results=[{"check_id": "chk-1", "band": "CRITICAL"}],
        anomaly_evidence={"anomaly_score": 0.9},
        risk_evidence={"risk_score": 0.5},
        severity_result=severity_result,
        business_impact_result=business_impact_result,
    )
    assert compute_evidence_snapshot_id(payload_1) != compute_evidence_snapshot_id(payload_3)
