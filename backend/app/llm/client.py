"""The only module that talks to a model provider.

Default is a local Ollama server using its native API, because LFM3's thinking
mode behaves differently there: thinking must be disabled explicitly and JSON
output can be forced with format="json". The OpenAI and Anthropic branches exist
for other providers; they are not used by default and must not be pointed at a
coding-plan / harness endpoint.
"""

import json
import re

import httpx

from ..config import get_settings


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        protocol: str | None = None,
        timeout: float | None = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.protocol = (protocol or settings.llm_protocol).lower()
        base = (base_url or settings.llm_base_url).rstrip("/")
        # Ollama's native endpoints sit at the root, not under /v1.
        self.base_url = base.removesuffix("/v1") if self.protocol == "ollama" else base
        self.timeout = timeout or settings.llm_timeout
        self.num_ctx = settings.llm_num_ctx

    @property
    def available(self) -> bool:
        return self.protocol == "ollama" or bool(self.api_key)

    def complete(
        self,
        system: str,
        user: str,
        *,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        json_mode: bool = False,
        json_schema: dict | None = None,
    ) -> str:
        if not self.available:
            raise LLMError("No LLM configured. Is Ollama running and LLM_MODEL pulled?")

        if self.protocol == "ollama":
            return self._ollama(
                system, user, model, max_tokens, temperature, json_mode, json_schema
            )
        if self.protocol == "anthropic":
            return self._anthropic(system, user, model, max_tokens, temperature)
        return self._openai(system, user, model, max_tokens, temperature, json_mode)

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        model: str,
        max_tokens: int = 1024,
        json_schema: dict | None = None,
    ) -> object:
        raw = self.complete(
            system,
            user + "\n\nReturn ONLY valid JSON. No prose, no markdown fences.",
            model=model,
            max_tokens=max_tokens,
            json_mode=True,
            json_schema=json_schema,
        )
        return extract_json(raw)

    # --- providers -------------------------------------------------------

    def _ollama(
        self,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool,
        json_schema: dict | None,
    ) -> str:
        payload: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "think": False,  # LFM3 thinking mode returns empty content over chat APIs
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": self.num_ctx,
            },
        }
        if json_schema is not None:
            payload["format"] = json_schema
        elif json_mode:
            payload["format"] = "json"

        response = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")

    def _anthropic(self, system: str, user: str, model: str, max_tokens: int, temperature: float) -> str:
        import anthropic

        client = anthropic.Anthropic(
            api_key=self.api_key, base_url=self.base_url, timeout=self.timeout
        )
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )

    def _openai(
        self,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


def extract_json(text: str) -> object:
    """Parse JSON even if the model wrapped it in prose or fences."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = cleaned.find(opener), cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise LLMError(f"Model did not return valid JSON: {cleaned[:200]!r}")
