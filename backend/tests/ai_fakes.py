"""A fake AI backend and a synchronous job runner, so AI tests need no model server or worker."""
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.modules.ai.gateway import get_backend_factory
from app.modules.ai.providers import AIError, BackendInfo, Completion
from app.modules.integrity.jobs import execute_job, get_job_runner
from tests.conftest import _make_engine


class FakeBackend:
    """
    - vision calls return `pages` in order (one dict per page),
    - text-splitting calls (prompts with <document>) return `splits` in order,
    - audit calls return the first `verdicts` entry whose key appears in the prompt;
      a value may be a function of the call's temperature, to vary samples.
    """

    def __init__(self, pages=None, splits=None, verdicts=None, fail=False, external=False):
        self.info = BackendInfo(
            name="fake", is_external=external, concurrency=4,
            models={"text": "fake-text", "vision": "fake-vision", "chat": "fake-chat"},
        )
        self.pages = list(pages or [])
        self.splits = list(splits or [])
        self.verdicts = verdicts or {}
        self.fail = fail
        self.prompts: list[str] = []
        self.calls: list[dict] = []
        self.messages: list[dict] | None = None

    def model_for(self, kind):
        return self.info.models.get(kind)

    def cost_usd(self, input_tokens, output_tokens):
        return ((input_tokens or 0) + (output_tokens or 0)) / 1_000_000

    async def complete_json(self, *, prompt, schema, images, temperature, seed):
        self.prompts.append(prompt)
        self.calls.append({"images": len(images or []), "temperature": temperature, "seed": seed})
        if self.fail:
            raise AIError("model server offline")
        if images:
            data = self.pages.pop(0) if self.pages else {"questions": []}
            return Completion(data=data, model="fake-vision", input_tokens=1000, output_tokens=200)
        if "<document>" in prompt:
            data = self.splits.pop(0) if self.splits else {"questions": []}
            return Completion(data=data, model="fake-text", input_tokens=500, output_tokens=200)
        for needle, verdict in self.verdicts.items():
            if needle in prompt:
                data = verdict(temperature) if callable(verdict) else verdict
                return Completion(data=data, model="fake-text", input_tokens=300, output_tokens=60)
        return Completion(
            data={"bloom": "C3", "co": None, "confidence": 0.1, "evidence": "", "rationale": "",
                  "abstain": True},
            model="fake-text", input_tokens=300, output_tokens=60,
        )

    async def stream_chat(self, *, messages, max_tokens, usage):
        self.messages = messages
        usage.model = "fake-chat"
        if self.fail:
            raise AIError("model server offline")
        for token in ("Hel", "lo"):
            yield token
        usage.input_tokens, usage.output_tokens = 70, 2


class SyncJobRunner:
    """Runs a job to completion inside submit(), on its own database session."""

    def __init__(self, backend: FakeBackend) -> None:
        self.backend = backend

    async def submit(self, job_id, payload):
        engine = _make_engine()
        factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        try:
            await execute_job(factory, lambda provider: self.backend, job_id, payload)
        finally:
            await engine.dispose()


class DeferredJobRunner:
    """Records jobs without running them, to test what the page sees while one is queued."""

    def __init__(self) -> None:
        self.submitted: list = []

    async def submit(self, job_id, payload):
        self.submitted.append((job_id, payload))


def use_fake_ai(backend: FakeBackend, runner=None) -> FakeBackend:
    app.dependency_overrides[get_backend_factory] = lambda: (lambda provider: backend)
    app.dependency_overrides[get_job_runner] = lambda: runner or SyncJobRunner(backend)
    return backend


def verdict(bloom, co, confidence=0.9, abstain=False):
    return {"bloom": bloom, "co": co, "confidence": confidence, "evidence": "quoted words",
            "rationale": "Because.", "abstain": abstain}
