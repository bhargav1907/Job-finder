from app.llm.client import LLMClient

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
