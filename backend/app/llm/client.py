"""The only module that talks to a model provider.

Two protocols are supported because the provider (BytePlus Ark) exposes an
Anthropic-compatible endpoint for coding tools and an OpenAI-compatible one for
general API use. Pick with LLM_PROTOCOL in .env.
"""

import json
import re

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
        timeout: float = 60.0,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.ark_api_key
        self.base_url = (base_url or settings.ark_base_url).rstrip("/")
        self.protocol = (protocol or settings.llm_protocol).lower()
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def complete(
        self,
        system: str,
        user: str,
        *,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> str:
        if not self.available:
            raise LLMError("ARK_API_KEY is not set in backend/.env")

        if self.protocol == "anthropic":
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

        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return response.choices[0].message.content or ""

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> object:
        raw = self.complete(
            system,
            user + "\n\nReturn ONLY valid JSON. No prose, no markdown fences.",
            model=model,
            max_tokens=max_tokens,
        )
        return extract_json(raw)


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
