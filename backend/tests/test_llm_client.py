import logging

import openai
import pytest

from app.llm.client import LLMClient, LLMError, LLMResponseError

SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
}


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"message": {"content": '{"name": "Priya"}'}}


def capture_post(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured.update(json)
        return FakeResponse()

    monkeypatch.setattr("app.llm.client.httpx.post", fake_post)
    return captured


def test_schema_is_sent_as_format_and_num_ctx_is_capped(monkeypatch):
    captured = capture_post(monkeypatch)
    client = LLMClient(protocol="ollama", base_url="http://localhost:11434")
    result = client.complete_json("system", "user", model="qwen3:4b", json_schema=SCHEMA)
    assert result == {"name": "Priya"}
    assert captured["format"] == SCHEMA
    assert captured["options"]["num_ctx"] == 8192
    assert captured["think"] is False


def test_plain_json_mode_still_works(monkeypatch):
    captured = capture_post(monkeypatch)
    client = LLMClient(protocol="ollama", base_url="http://localhost:11434")
    client.complete_json("system", "user", model="lfm3:1.7b")
    assert captured["format"] == "json"


def test_ollama_token_counts_are_logged(monkeypatch, caplog):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {"content": '{"name": "Priya"}'},
                "prompt_eval_count": 812,
                "eval_count": 143,
                "total_duration": 2_140_000_000,
            }

    monkeypatch.setattr("app.llm.client.httpx.post", lambda *a, **k: FakeResponse())
    client = LLMClient(protocol="ollama", base_url="http://localhost:11434")
    with caplog.at_level(logging.INFO, logger="app.llm.client"):
        client.complete_json("system", "user", model="lfm3:1.7b", purpose="rerank")
    assert (
        "llm_call model=lfm3:1.7b purpose=rerank "
        "prompt_tokens=812 completion_tokens=143 total_ms=2140"
    ) in caplog.text


def test_openai_provider_errors_become_llm_error(monkeypatch):
    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = type(
                "Chat",
                (),
                {
                    "completions": type(
                        "Completions",
                        (),
                        {
                            "create": lambda self, **kwargs: (_ for _ in ()).throw(
                                openai.APIError(
                                    "rate limited", request=None, body=None
                                )
                            )
                        },
                    )()
                },
            )()

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    client = LLMClient(
        protocol="openai",
        base_url="https://api.groq.com/openai/v1",
        api_key="test",
    )
    with pytest.raises(LLMError, match="rate limited"):
        client.complete_json("system", "user", model="openai/gpt-oss-120b")


def test_prose_reply_is_a_response_error(monkeypatch):
    class ProseResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "I think this job fits well."}}

    monkeypatch.setattr("app.llm.client.httpx.post", lambda *a, **k: ProseResponse())
    client = LLMClient(protocol="ollama", base_url="http://localhost:11434")
    with pytest.raises(LLMResponseError, match="valid JSON"):
        client.complete_json("system", "user", model="lfm3:1.7b")


def test_empty_api_key_does_not_inherit_the_global_key():
    client = LLMClient(
        protocol="openai",
        base_url="https://api.groq.com/openai/v1",
        api_key="",
    )
    assert client.available is False


def test_missing_token_fields_log_dashes(monkeypatch, caplog):
    capture_post(monkeypatch)
    client = LLMClient(protocol="ollama", base_url="http://localhost:11434")
    with caplog.at_level(logging.INFO, logger="app.llm.client"):
        client.complete_json("system", "user", model="lfm3:1.7b")
    assert "prompt_tokens=- completion_tokens=- total_ms=-" in caplog.text
