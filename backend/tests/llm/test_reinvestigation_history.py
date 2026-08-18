from app.llm import investigation_log
from app.llm.investigation_service import investigate
from tests.llm._fixtures import always_returns, make_draft, make_payload


def test_reinvestigating_same_incident_preserves_both_records(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)

    client_1 = always_returns(make_draft("First analysis: GX check pattern A."))
    result_1 = investigate("incident-1", make_payload(), mistral_client_override=client_1)

    client_2 = always_returns(make_draft("Second analysis after reject/recalculate: pattern B."))
    result_2 = investigate("incident-1", make_payload(), mistral_client_override=client_2)

    assert result_1.investigation_id != result_2.investigation_id

    investigations, failures = investigation_log.read_investigation_history("incident-1")
    assert len(investigations) == 2
    assert failures == []

    # newest first
    assert investigations[0].investigation_id == result_2.investigation_id
    assert investigations[1].investigation_id == result_1.investigation_id

    # the first record is preserved unmodified
    preserved_first = next(i for i in investigations if i.investigation_id == result_1.investigation_id)
    assert preserved_first.likely_root_cause == result_1.likely_root_cause
