"""
The AI gateway — the one place features call models through.

For every call it:
- uses the provider the organization chose for that feature (or the server default),
- redacts personal data from text when the provider is external,
- limits how many calls one job or request runs at once (AI_*_CONCURRENCY),
- records a usage row (tokens, latency, cost, redactions, model, prompt version).

Usage rows are collected in memory and written by the caller with record_usage(),
so a feature can release its database connection during slow model calls.
"""
import asyncio
import time
from collections.abc import AsyncIterator, Callable, Iterable
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ai.models import AICall, OrganizationAISettings
from app.modules.ai.providers import (
    AIBackend,
    AIError,
    Completion,
    ModelKind,
    StreamUsage,
    build_backend,
)
from app.modules.ai.redaction import redact

BackendFactory = Callable[[str], AIBackend | None]

_DEFAULTS = {
    "integrity": lambda: settings.AI_INTEGRITY_PROVIDER,
    "copilot": lambda: settings.AI_COPILOT_PROVIDER,
}


class AIUnavailableError(AIError):
    """AI is turned off for this feature, or its provider is not configured."""


def get_backend_factory() -> BackendFactory:
    """FastAPI dependency; tests override it to plug in a fake backend."""
    return build_backend


def default_provider(feature: str) -> str:
    return _DEFAULTS[feature]()


async def provider_choice(session: AsyncSession, organization_id: UUID, feature: str) -> str:
    row = await session.get(OrganizationAISettings, organization_id)
    chosen = getattr(row, f"{feature}_provider", None) if row else None
    return chosen or default_provider(feature)


class AIGateway:
    def __init__(
        self,
        backend: AIBackend | None,
        *,
        provider: str,
        feature: str,
        organization_id: UUID,
        user_id: UUID | None,
    ) -> None:
        self.backend = backend
        self.provider = provider
        self.feature = feature
        self.organization_id = organization_id
        self.user_id = user_id
        self._calls: list[AICall] = []
        self._limit = asyncio.Semaphore(backend.info.concurrency if backend else 1)

    @classmethod
    async def for_feature(
        cls,
        session: AsyncSession,
        *,
        feature: str,
        organization_id: UUID,
        user_id: UUID | None,
        backend_factory: BackendFactory = build_backend,
    ) -> "AIGateway":
        provider = await provider_choice(session, organization_id, feature)
        backend = None if provider == "off" else backend_factory(provider)
        return cls(
            backend, provider=provider, feature=feature,
            organization_id=organization_id, user_id=user_id,
        )

    # ── Introspection ─────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self.backend is not None

    @property
    def concurrency(self) -> int:
        return self.backend.info.concurrency if self.backend else 1

    def model_for(self, kind: ModelKind) -> str | None:
        return self.backend.model_for(kind) if self.backend else None

    def unavailable_reason(self) -> str:
        if self.provider == "off":
            return f"AI is turned off for {self.feature} in this organization"
        return f"The {self.provider} AI provider is not configured on the server"

    def _require(self) -> AIBackend:
        if self.backend is None:
            raise AIUnavailableError(self.unavailable_reason())
        return self.backend

    def _redact(self, text: str, names: Iterable[str | None]) -> tuple[str, int]:
        if self.backend is None or not self.backend.info.is_external:
            return text, 0
        result = redact(text, names)
        return result.text, result.count

    # ── Calls ─────────────────────────────────────────────────────────────────

    async def complete_json(
        self,
        *,
        purpose: str,
        prompt: str,
        schema: dict,
        prompt_version: str,
        images: list[bytes] | None = None,
        temperature: float = 0.0,
        seed: int | None = None,
        names: Iterable[str | None] = (),
    ) -> Completion:
        backend = self._require()
        prompt, redactions = self._redact(prompt, names)
        model = backend.model_for("vision" if images else "text") or "unknown"
        async with self._limit:
            started = time.perf_counter()
            try:
                result = await backend.complete_json(
                    prompt=prompt, schema=schema, images=images,
                    temperature=temperature, seed=seed,
                )
            except AIError as exc:
                self._log(purpose, model, prompt_version, started, images, redactions, error=str(exc))
                raise
        self._log(
            purpose, result.model, prompt_version, started, images, redactions,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            cost=result.cost_usd,
        )
        return result

    async def stream_chat(
        self,
        *,
        purpose: str,
        messages: list[dict[str, str]],
        prompt_version: str,
        max_tokens: int,
        names: Iterable[str | None] = (),
    ) -> AsyncIterator[str]:
        backend = self._require()
        names = list(names)
        redactions = 0
        safe_messages = []
        for message in messages:
            content, n = self._redact(message["content"], names)
            redactions += n
            safe_messages.append({**message, "content": content})
        usage = StreamUsage(model=backend.model_for("chat") or "unknown")
        started = time.perf_counter()
        try:
            async with self._limit:
                async for token in backend.stream_chat(
                    messages=safe_messages, max_tokens=max_tokens, usage=usage
                ):
                    yield token
        except AIError as exc:
            self._log(purpose, usage.model, prompt_version, started, None, redactions, error=str(exc))
            raise
        self._log(
            purpose, usage.model, prompt_version, started, None, redactions,
            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        )

    # ── Usage ─────────────────────────────────────────────────────────────────

    def _log(
        self,
        purpose: str,
        model: str,
        prompt_version: str | None,
        started: float,
        images: list[bytes] | None,
        redactions: int,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        error: str | None = None,
        cost: float | None = None,
    ) -> None:
        if cost is None:
            cost = self.backend.cost_usd(input_tokens, output_tokens) if self.backend else 0.0
        self._calls.append(AICall(
            organization_id=self.organization_id,
            user_id=self.user_id,
            feature=self.feature,
            purpose=purpose,
            provider=self.provider,
            model=model[:100],
            prompt_version=prompt_version,
            status="ERROR" if error else "OK",
            error=error[:2000] if error else None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            image_count=len(images or []),
            redactions=redactions,
            latency_ms=int((time.perf_counter() - started) * 1000),
            cost_usd=Decimal(str(round(cost, 6))),
        ))

    @property
    def pending_calls(self) -> list[AICall]:
        return list(self._calls)

    def record_usage(self, session: AsyncSession) -> None:
        """Add the usage rows collected so far to the session; the caller commits."""
        session.add_all(self._calls)
        self._calls = []


async def load_settings(session: AsyncSession, organization_id: UUID) -> OrganizationAISettings | None:
    return (await session.execute(
        select(OrganizationAISettings).where(OrganizationAISettings.organization_id == organization_id)
    )).scalar_one_or_none()
