from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any
from urllib import error, request


class AIClient(ABC):
    @abstractmethod
    def generate_json_draft(self, raw_text: str, prompt: str) -> str:
        raise NotImplementedError


class OpenAIChatClient(AIClient):
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout_s: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def generate_json_draft(self, raw_text: str, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": f"{prompt}\n\nSOURCE TEXT:\n{raw_text}"},
            ],
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_s) as resp:
                response_text = resp.read().decode("utf-8", errors="replace")
        except error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"AI provider HTTP error {e.code}: {detail}") from e
        except Exception as e:
            raise RuntimeError(f"AI provider request failed: {e}") from e

        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI provider returned non-JSON response: {e}") from e

        try:
            content = payload["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError("AI provider response missing choices/message/content.") from e

        return _normalize_message_content(content)


class UnavailableAIClient(AIClient):
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def generate_json_draft(self, raw_text: str, prompt: str) -> str:
        raise RuntimeError(self.reason)


def _normalize_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
            elif isinstance(part, str):
                chunks.append(part)
        return "".join(chunks)
    return str(content)


def create_default_client() -> AIClient:
    provider = (os.environ.get("SDRE_AI_PROVIDER") or "openai").strip().lower()
    if provider != "openai":
        return UnavailableAIClient(f"Unsupported AI provider '{provider}'.")

    api_key = (os.environ.get("SDRE_AI_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return UnavailableAIClient("Missing AI API key. Set SDRE_AI_API_KEY or OPENAI_API_KEY.")

    base_url = (os.environ.get("SDRE_AI_BASE_URL") or "https://api.openai.com/v1").strip()
    model = (os.environ.get("SDRE_AI_MODEL") or "gpt-4o-mini").strip()
    return OpenAIChatClient(api_key=api_key, base_url=base_url, model=model)
