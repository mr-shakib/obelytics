"""
Model backends behind the AI gateway. Features never use these directly.

- OllamaBackend           — "local": an Ollama server you run; nothing leaves your servers.
- OpenAICompatibleBackend — "hosted": any Chat Completions API (DeepSeek, OpenAI, vLLM…).
"""
import base64
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal, Protocol

import httpx

from app.core.config import settings

ModelKind = Literal["text", "vision", "chat"]


class AIError(RuntimeError):
    """The model could not be reached or returned something unusable."""


@dataclass
class Completion:
    data: dict
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    # Set by backends whose price depends on the call (e.g. a separate vision endpoint).
    cost_usd: float | None = None


@dataclass
class StreamUsage:
    """Filled in by stream_chat once the stream ends."""
    model: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass
class BackendInfo:
    name: str
    is_external: bool
    concurrency: int
    models: dict[str, str] = field(default_factory=dict)


class AIBackend(Protocol):
    info: BackendInfo

    def model_for(self, kind: ModelKind) -> str | None: ...

    def cost_usd(self, input_tokens: int | None, output_tokens: int | None) -> float: ...

    async def complete_json(
        self,
        *,
        prompt: str,
        schema: dict,
        images: list[bytes] | None,
        temperature: float,
        seed: int | None,
    ) -> Completion: ...

    def stream_chat(
        self, *, messages: list[dict[str, str]], max_tokens: int, usage: StreamUsage
    ) -> AsyncIterator[str]: ...


def _timeout() -> httpx.Timeout:
    return httpx.Timeout(settings.AI_TIMEOUT_SECONDS, connect=10.0)


_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$")


def _parse_json(content: str) -> dict:
    try:
        data = json.loads(_FENCE.sub("", content or ""))
    except ValueError as exc:
        raise AIError("The model returned output that is not valid JSON") from exc
    if not isinstance(data, dict):
        raise AIError("The model returned JSON that is not an object")
    return data


class OllamaBackend:
    def __init__(self) -> None:
        self.base_url = settings.AI_LOCAL_BASE_URL.rstrip("/")
        self.info = BackendInfo(
            name="local",
            is_external=False,
            concurrency=max(1, settings.AI_LOCAL_CONCURRENCY),
            models={
                "text": settings.AI_LOCAL_TEXT_MODEL,
                "vision": settings.AI_LOCAL_VISION_MODEL,
                "chat": settings.AI_LOCAL_CHAT_MODEL,
            },
        )

    def model_for(self, kind: ModelKind) -> str | None:
        return self.info.models.get(kind) or None

    def cost_usd(self, input_tokens: int | None, output_tokens: int | None) -> float:
        return 0.0

    async def complete_json(self, *, prompt, schema, images, temperature, seed) -> Completion:
        model = self.model_for("vision" if images else "text")
        if not model:
            raise AIError("No local model is configured for this task")
        message: dict = {"role": "user", "content": prompt}
        if images:
            message["images"] = [base64.b64encode(image).decode() for image in images]
        options: dict = {"temperature": temperature, "num_ctx": settings.AI_LOCAL_CONTEXT_TOKENS}
        if seed is not None:
            options["seed"] = seed
        payload = {
            "model": model,
            "messages": [message],
            "stream": False,
            "think": False,
            "format": schema,
            "options": options,
        }
        try:
            async with httpx.AsyncClient(timeout=_timeout()) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.HTTPError as exc:
            raise AIError(f"Could not reach the local model server at {self.base_url}") from exc
        if response.status_code >= 400:
            raise AIError(f"Local model server returned HTTP {response.status_code}: {response.text[:300]}")
        try:
            body = response.json()
            content = body["message"]["content"]
        except (KeyError, ValueError) as exc:
            raise AIError("Local model server returned an unexpected response") from exc
        return Completion(
            data=_parse_json(content),
            model=model,
            input_tokens=body.get("prompt_eval_count"),
            output_tokens=body.get("eval_count"),
        )

    async def stream_chat(self, *, messages, max_tokens, usage) -> AsyncIterator[str]:
        model = self.model_for("chat")
        if not model:
            raise AIError("No local chat model is configured")
        usage.model = model
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": {"num_ctx": settings.AI_LOCAL_CONTEXT_TOKENS, "num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=_timeout()) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode(errors="replace")[:300]
                        raise AIError(f"Local model server returned HTTP {response.status_code}: {body}")
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        content = (chunk.get("message") or {}).get("content")
                        if content:
                            yield content
                        if chunk.get("done"):
                            usage.input_tokens = chunk.get("prompt_eval_count")
                            usage.output_tokens = chunk.get("eval_count")
        except httpx.HTTPError as exc:
            raise AIError(f"Could not reach the local model server at {self.base_url}") from exc

    async def installed_models(self) -> list[str] | None:
        """Models the server has pulled, or None if it cannot be reached."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
                response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return [m["name"] for m in response.json().get("models", [])]
        except (httpx.HTTPError, ValueError, KeyError):
            return None


@dataclass
class _Endpoint:
    base_url: str
    api_key: str
    json_mode: str
    extra_body: dict
    input_usd_per_mtok: float
    output_usd_per_mtok: float


class OpenAICompatibleBackend:
    def __init__(self) -> None:
        self.base_url = settings.AI_HOSTED_BASE_URL.rstrip("/")
        self.api_key = settings.AI_HOSTED_API_KEY
        main = _Endpoint(
            self.base_url, self.api_key, settings.AI_HOSTED_JSON_MODE, settings.AI_HOSTED_EXTRA_BODY,
            settings.AI_HOSTED_INPUT_USD_PER_MTOK, settings.AI_HOSTED_OUTPUT_USD_PER_MTOK,
        )
        separate = bool(settings.AI_HOSTED_VISION_BASE_URL)
        self.vision = _Endpoint(
            (settings.AI_HOSTED_VISION_BASE_URL or self.base_url).rstrip("/"),
            settings.AI_HOSTED_VISION_API_KEY or self.api_key,
            settings.AI_HOSTED_VISION_JSON_MODE or settings.AI_HOSTED_JSON_MODE,
            settings.AI_HOSTED_VISION_EXTRA_BODY if separate else settings.AI_HOSTED_EXTRA_BODY,
            _price(settings.AI_HOSTED_VISION_INPUT_USD_PER_MTOK, main.input_usd_per_mtok),
            _price(settings.AI_HOSTED_VISION_OUTPUT_USD_PER_MTOK, main.output_usd_per_mtok),
        )
        self.main = main
        self.info = BackendInfo(
            name="hosted",
            is_external=not settings.AI_HOSTED_SELF_HOSTED,
            concurrency=max(1, settings.AI_HOSTED_CONCURRENCY),
            models={
                "text": settings.AI_HOSTED_TEXT_MODEL,
                "vision": settings.AI_HOSTED_VISION_MODEL,
                "chat": settings.AI_HOSTED_CHAT_MODEL,
            },
        )

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key) or self.vision_configured

    @property
    def vision_configured(self) -> bool:
        return bool(self.vision.base_url and self.vision.api_key and self.info.models.get("vision"))

    def model_for(self, kind: ModelKind) -> str | None:
        return self.info.models.get(kind) or None

    def cost_usd(self, input_tokens: int | None, output_tokens: int | None) -> float:
        return (
            (input_tokens or 0) * settings.AI_HOSTED_INPUT_USD_PER_MTOK
            + (output_tokens or 0) * settings.AI_HOSTED_OUTPUT_USD_PER_MTOK
        ) / 1_000_000

    def _headers(self, endpoint: "_Endpoint | None" = None) -> dict[str, str]:
        key = (endpoint or self.main).api_key
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    async def complete_json(self, *, prompt, schema, images, temperature, seed) -> Completion:
        model = self.model_for("vision" if images else "text")
        endpoint = self.vision if images else self.main
        if not (endpoint.base_url and endpoint.api_key) or not model:
            raise AIError("The hosted AI provider is not configured for this task")
        if endpoint.json_mode == "json_object":
            # JSON mode does not take a schema, so state it in the prompt.
            prompt = f"{prompt}\n\nRespond with one JSON object matching this JSON Schema:\n{json.dumps(schema)}"
            response_format: dict = {"type": "json_object"}
        else:
            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "output", "schema": schema},
            }
        content: str | list = prompt
        if images:
            content = [{"type": "text", "text": prompt}] + [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image).decode()}"}}
                for image in images
            ]
        payload = {
            **endpoint.extra_body,
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": temperature,
            "response_format": response_format,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=_timeout()) as client:
                response = await client.post(
                    f"{endpoint.base_url}/chat/completions", headers=self._headers(endpoint), json=payload
                )
        except httpx.HTTPError as exc:
            raise AIError("Could not reach the hosted AI provider") from exc
        if response.status_code >= 400:
            raise AIError(f"Hosted AI provider returned HTTP {response.status_code}: {response.text[:300]}")
        try:
            body = response.json()
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise AIError("Hosted AI provider returned an unexpected response") from exc
        tokens = body.get("usage") or {}
        input_tokens, output_tokens = tokens.get("prompt_tokens"), tokens.get("completion_tokens")
        return Completion(
            data=_parse_json(text),
            model=body.get("model") or model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=(
                (input_tokens or 0) * endpoint.input_usd_per_mtok
                + (output_tokens or 0) * endpoint.output_usd_per_mtok
            ) / 1_000_000,
        )

    async def stream_chat(self, *, messages, max_tokens, usage) -> AsyncIterator[str]:
        model = self.model_for("chat")
        if not self.configured or not model:
            raise AIError("The hosted AI provider is not configured for chat")
        usage.model = model
        payload = {
            **settings.AI_HOSTED_EXTRA_BODY,
            "model": model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/chat/completions", headers=self._headers(), json=payload
                ) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode(errors="replace")[:500]
                        raise AIError(f"Hosted AI provider returned HTTP {response.status_code}: {body}")
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
                        if chunk.get("usage"):
                            usage.input_tokens = chunk["usage"].get("prompt_tokens")
                            usage.output_tokens = chunk["usage"].get("completion_tokens")
                        choices = chunk.get("choices") or []
                        if choices:
                            text = (choices[0].get("delta") or {}).get("content")
                            if text:
                                yield text
        except httpx.HTTPError as exc:
            raise AIError("Could not connect to the hosted AI provider") from exc


def _price(value: float | None, fallback: float) -> float:
    return fallback if value is None else value


def build_backend(provider: str) -> AIBackend | None:
    """The backend for a provider name, or None when it is off or not configured."""
    if provider == "local":
        return OllamaBackend() if settings.AI_LOCAL_BASE_URL else None
    if provider == "hosted":
        backend = OpenAICompatibleBackend()
        return backend if backend.configured else None
    return None
