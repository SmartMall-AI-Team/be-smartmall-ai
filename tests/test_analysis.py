import json
from types import SimpleNamespace

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI

from app.core.config import Settings
from app.main import create_app
from app.schemas.analysis import AnalysisSuggestion
from app.services import analysis
from tests.test_occurrences import PAYLOAD

SUGGESTION = {
    "category": "hvac",
    "suggested_priority": "medium",
    "suggested_team": "Climatização",
    "rationale": "Perda de refrigeração relatada, sem inspeção no local.",
    "recommendation": "Solicitar avaliação por equipe habilitada.",
}


def test_simulation_review_and_source_edit(client):
    client.app.state.settings.ai_simulation = True
    occurrence = client.post("/api/v1/occurrences", json=PAYLOAD).json()
    path = "/api/v1/occurrences/" + occurrence["id"]
    result = client.post(path + "/analyze")
    assert result.status_code == 200
    assert result.json()["is_simulation"] is True
    saved = client.get(path).json()
    assert saved["ai_analysis"] == result.json()
    assert saved["priority"] == "untriaged"
    reviewed = client.patch(path, json={"priority": "high", "confirm_ai_review": True}).json()
    assert reviewed["ai_reviewed_at"] is not None
    assert reviewed["priority"] == "high"
    changed = client.patch(path, json={"description": "Novo relato fictício."}).json()
    assert changed["ai_analysis"] is None
    assert changed["ai_reviewed_at"] is None
    assert client.patch(path, json={"confirm_ai_review": True}).status_code == 409


def test_missing_key_does_not_delete_occurrence(client, monkeypatch):
    client.app.state.settings.openai_api_key = None
    occurrence = client.post("/api/v1/occurrences", json=PAYLOAD).json()
    path = "/api/v1/occurrences/" + occurrence["id"]
    assert client.post(path + "/analyze").status_code == 503
    assert client.get(path).json()["ai_analysis"] is None
    assert (
        client.post("/api/v1/occurrences/00000000-0000-0000-0000-000000000000/analyze").status_code
        == 404
    )


def test_real_sdk_request_and_structured_response(monkeypatch):
    sent = []

    def respond(request):
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "gpt-5.4-mini",
                "output": [
                    {
                        "id": "msg_test",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(SUGGESTION),
                                "annotations": [],
                            }
                        ],
                    }
                ],
            },
        )

    def factory(**kwargs):
        return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))

    monkeypatch.setattr(analysis, "OpenAI", factory)
    settings = Settings(_env_file=None, openai_api_key="not-a-real-key")
    result = analysis.request_analysis(settings, PAYLOAD)
    assert result.model_dump() == {**SUGGESTION, "is_simulation": False}
    assert sent[0]["store"] is False
    assert sent[0]["text"]["format"]["strict"] is True
    assert sent[0]["model"] == settings.ai_model


@pytest.mark.parametrize("mode", ["timeout", "rate_limit", "refusal", "invalid"])
def test_provider_errors_preserve_previous_analysis(client, monkeypatch, mode):
    client.app.state.settings.ai_simulation = True
    occurrence = client.post("/api/v1/occurrences", json=PAYLOAD).json()
    path = "/api/v1/occurrences/" + occurrence["id"]
    previous = client.post(path + "/analyze").json()
    client.app.state.settings.ai_simulation = False
    client.app.state.settings.openai_api_key = "not-a-real-key"

    def respond(request):
        if mode == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        if mode == "rate_limit":
            return httpx.Response(429, json={"error": {"message": "quota", "type": "rate_limit"}})
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "gpt-5.4-mini",
                "output": [
                    {
                        "id": "msg_test",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {"type": "refusal", "refusal": "recusado"}
                            if mode == "refusal"
                            else {
                                "type": "output_text",
                                "text": '{"category":"invalid"}',
                                "annotations": [],
                            }
                        ],
                    }
                ],
            },
        )

    def factory(**kwargs):
        return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))

    monkeypatch.setattr(analysis, "OpenAI", factory)
    response = client.post(path + "/analyze")
    assert response.status_code == 503
    assert "not-a-real-key" not in response.text
    assert client.get(path).json()["ai_analysis"] == previous


def test_concurrent_change_discards_stale_analysis(clean_database, monkeypatch):
    settings = Settings(_env_file=None, database_url=clean_database, ai_simulation=True)
    with TestClient(create_app(settings)) as client:
        occurrence = client.post("/api/v1/occurrences", json=PAYLOAD).json()
        path = "/api/v1/occurrences/" + occurrence["id"]

        def concurrent(*args):
            assert client.patch(path, json={"location": "Outro setor"}).status_code == 200
            return analysis.AIAnalysis(**SUGGESTION, is_simulation=False)

        monkeypatch.setattr(analysis, "request_analysis", concurrent)
        assert client.post(path + "/analyze").status_code == 409
        assert client.get(path).json()["ai_analysis"] is None


def test_incomplete_response_is_rejected(monkeypatch):
    class Client:
        def __init__(self, **kwargs):
            self.responses = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def parse(self, **kwargs):
            return SimpleNamespace(
                status="incomplete", output_parsed=AnalysisSuggestion(**SUGGESTION)
            )

    monkeypatch.setattr(analysis, "OpenAI", Client)
    with pytest.raises(Exception) as error:
        analysis.request_analysis(Settings(_env_file=None, openai_api_key="fake"), PAYLOAD)
    assert error.value.status_code == 503
