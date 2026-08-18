from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.llm import investigation_log, investigation_service, router as router_module
from tests.llm._fixtures import always_returns, make_draft, make_payload


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router_module.router)
    return app


def test_investigate_without_structured_payload_returns_404():
    client = TestClient(_app())
    response = client.post("/llm/investigate", json={"incident_id": "unknown-incident"})
    assert response.status_code == 404


def test_investigate_with_structured_payload_returns_full_report(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)
    fake_client = always_returns(make_draft())
    real_investigate = investigation_service.investigate
    monkeypatch.setattr(
        router_module.investigation_service,
        "investigate",
        lambda incident_id, payload, **kw: real_investigate(
            incident_id, payload, mistral_client_override=fake_client
        ),
    )

    payload = make_payload()
    response = TestClient(_app()).post(
        "/llm/investigate",
        json={"incident_id": "incident-42", "structured_payload": payload.model_dump()},
    )

    assert response.status_code == 200
    body = response.json()
    for field in (
        "summary",
        "likely_root_cause",
        "evidence",
        "business_impact_narrative",
        "recommended_fix",
        "prevention_recommendation",
    ):
        assert body[field].strip()


def test_get_investigations_returns_accumulated_history(monkeypatch, tmp_path):
    monkeypatch.setattr(investigation_log, "reports_dir", lambda: tmp_path)
    fake_client = always_returns(make_draft())
    investigation_service.investigate("incident-99", make_payload(), mistral_client_override=fake_client)
    investigation_service.investigate("incident-99", make_payload(), mistral_client_override=fake_client)

    response = TestClient(_app()).get("/llm/investigations/incident-99")
    assert response.status_code == 200
    body = response.json()
    assert len(body["investigations"]) == 2
    assert body["failures"] == []
