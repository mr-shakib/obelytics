import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings


class CopilotProviderError(RuntimeError):
    pass


class DeepSeekProvider:
    def __init__(self) -> None:
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")
        self.model = settings.DEEPSEEK_MODEL

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        if not self.api_key:
            raise CopilotProviderError("DEEPSEEK_API_KEY is not configured")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "thinking": {"type": "disabled"},
            "max_tokens": settings.COPILOT_MAX_OUTPUT_TOKENS,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode(errors="replace")[:500]
                        raise CopilotProviderError(
                            f"DeepSeek returned HTTP {response.status_code}: {body}"
                        )
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices") or []
                        if choices:
                            content = choices[0].get("delta", {}).get("content")
                            if content:
                                yield content
        except httpx.HTTPError as exc:
            raise CopilotProviderError("Could not connect to DeepSeek") from exc
