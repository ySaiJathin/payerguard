import httpx
import pytest

from app.llm import investigation_log
from app.llm.errors import MalformedResponseError, MistralAPIError
from app.llm.investigation_service import investigate
from tests.llm._fixtures import always_raises, always_returns, fails_then_succeeds, make_draft, make_payload


def test_persistent_timeout_persists_failure_not_a_fabricated_investigation(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)
    client = always_raises(httpx.TimeoutException("timed out"))

    with pytest.raises(MistralAPIError):
        investigate("incident-1", make_payload(), mistral_client_override=client)

    investigations, failures = investigation_log.read_investigation_history("incident-1")
    assert investigations == []
    assert len(failures) == 1
    assert failures[0].failure_type.value == "api_error"


def test_single_retry_on_transient_error_then_success(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)
    client = fails_then_succeeds(httpx.ConnectError("connection reset"), make_draft())

    result = investigate("incident-2", make_payload(), mistral_client_override=client)

    assert client.chat.call_count == 2  # one failed attempt, one retry that succeeded
    investigations, failures = investigation_log.read_investigation_history("incident-2")
    assert len(investigations) == 1
    assert failures == []
    assert result.investigation_id == investigations[0].investigation_id


def test_malformed_response_persists_failure_with_malformed_response_type(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)
    # Mistral's structured-output mode guarantees valid JSON shape, but not
    # non-empty content -- response_parser.validate_and_tag is what catches
    # this, after a successful (not raising) client call.
    incomplete_draft = make_draft().model_copy(update={"summary": ""})
    client = always_returns(incomplete_draft)

    with pytest.raises(MalformedResponseError):
        investigate("incident-3", make_payload(), mistral_client_override=client)

    _investigations, failures = investigation_log.read_investigation_history("incident-3")
    assert len(failures) == 1
    assert failures[0].failure_type.value == "malformed_response"
