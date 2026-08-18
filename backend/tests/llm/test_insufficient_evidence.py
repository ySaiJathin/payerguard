from app.llm.investigation_service import investigate
from app.llm.prompt_templates import INSUFFICIENCY_PHRASE
from app.llm import investigation_log
from tests.llm._fixtures import always_returns, make_draft, make_payload


def test_insufficiency_phrase_is_tagged_true_in_every_run(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)

    for i in range(5):  # "100% of test runs", not probabilistic
        draft = make_draft(
            likely_root_cause=f"{INSUFFICIENCY_PHRASE}. More claim-level detail would be needed."
        )
        client = always_returns(draft)
        result = investigate(f"incident-sparse-{i}", make_payload(), mistral_client_override=client)
        assert result.insufficient_evidence is True


def test_substantive_root_cause_is_tagged_false_not_applied_indiscriminately(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)

    draft = make_draft(
        likely_root_cause=(
            "A single dominant CRITICAL GX failure on CLM_DRG_CD, co-occurring with a 0.97 "
            "anomaly percentile, indicates a systematic upstream coding error for this window."
        )
    )
    client = always_returns(draft)
    result = investigate("incident-clear", make_payload(), mistral_client_override=client)

    assert result.insufficient_evidence is False
