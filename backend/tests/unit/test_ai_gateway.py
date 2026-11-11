"""The AI gateway: redaction for external providers, usage records, availability."""
import uuid

import pytest

from app.core.config import Settings
from app.modules.ai.gateway import AIGateway, AIUnavailableError
from app.modules.ai.providers import AIError
from app.modules.ai.redaction import redact
from tests.ai_fakes import FakeBackend, verdict


def _gateway(backend, provider="hosted") -> AIGateway:
    return AIGateway(backend, provider=provider, feature="integrity",
                     organization_id=uuid.uuid4(), user_id=uuid.uuid4())


# ── Redaction ─────────────────────────────────────────────────────────────────

def test_redacts_emails_phones_and_student_ids():
    result = redact(
        "Mail rahim.uddin@example.edu or call 01712-345678 / +880 1812345678 about 221-15-4567 "
        "(reg 0242310005101234)."
    )
    assert result.text == "Mail [EMAIL] or call [PHONE] / [PHONE] about [ID] (reg [ID])."
    assert result.kinds == {"email": 1, "phone": 2, "id": 2}


def test_redacts_known_names_case_insensitively():
    result = redact("Ask MD. RAHIM UDDIN, or Rahim, but not Rahimullah.", ["Md. Rahim Uddin", "Rahim", "", None])
    assert result.text == "Ask [PERSON], or [PERSON], but not Rahimullah."


def test_ordinary_exam_numbers_are_left_alone():
    text = "Insert 50, 30, 70 and solve x = 3.14159 for n = 1000000 iterations in 2026."
    assert redact(text).text == text


# ── Gateway ───────────────────────────────────────────────────────────────────

async def test_external_provider_gets_redacted_text_and_usage_is_recorded():
    backend = FakeBackend(external=True, verdicts={"Question": verdict("C3", "CO1")})
    gateway = _gateway(backend)
    await gateway.complete_json(
        purpose="audit_question", prompt="Question by karim@example.edu for Karim Ahmed",
        schema={}, prompt_version="audit-v2", names=["Karim Ahmed"],
    )
    assert backend.prompts == ["Question by [EMAIL] for [PERSON]"]
    [call] = gateway.pending_calls
    assert (call.status, call.redactions, call.model, call.prompt_version) == ("OK", 2, "fake-text", "audit-v2")
    assert (call.input_tokens, call.output_tokens) == (300, 60)
    assert float(call.cost_usd) == pytest.approx(0.00036)


async def test_local_provider_gets_the_text_unchanged():
    backend = FakeBackend(external=False)
    gateway = _gateway(backend, provider="local")
    await gateway.complete_json(purpose="p", prompt="mail karim@example.edu", schema={}, prompt_version="v")
    assert backend.prompts == ["mail karim@example.edu"]
    assert gateway.pending_calls[0].redactions == 0


async def test_failed_call_is_recorded_and_raised():
    gateway = _gateway(FakeBackend(fail=True))
    with pytest.raises(AIError):
        await gateway.complete_json(purpose="p", prompt="x", schema={}, prompt_version="v")
    [call] = gateway.pending_calls
    assert (call.status, call.error) == ("ERROR", "model server offline")


async def test_stream_redacts_every_message_and_records_usage():
    backend = FakeBackend(external=True)
    gateway = _gateway(backend)
    tokens = [t async for t in gateway.stream_chat(
        purpose="chat", prompt_version="copilot-v1", max_tokens=10, names=["Nadia Islam"],
        messages=[{"role": "system", "content": "User: Nadia Islam"},
                  {"role": "user", "content": "email me at nadia@x.org"}],
    )]
    assert "".join(tokens) == "Hello"
    assert [m["content"] for m in backend.messages] == ["User: [PERSON]", "email me at [EMAIL]"]
    [call] = gateway.pending_calls
    assert (call.redactions, call.input_tokens, call.output_tokens) == (2, 70, 2)


async def test_unavailable_gateway_explains_why():
    gateway = AIGateway(None, provider="off", feature="copilot",
                        organization_id=uuid.uuid4(), user_id=None)
    assert not gateway.available
    with pytest.raises(AIUnavailableError, match="turned off for copilot"):
        await gateway.complete_json(purpose="p", prompt="x", schema={}, prompt_version="v")


# ── Settings ──────────────────────────────────────────────────────────────────

def test_deepseek_settings_still_configure_the_hosted_provider():
    s = Settings(_env_file=None, DEEPSEEK_API_KEY="sk-test", DEEPSEEK_MODEL="deepseek-chat")
    assert (s.AI_HOSTED_API_KEY, s.AI_HOSTED_CHAT_MODEL, s.AI_HOSTED_BASE_URL) == (
        "sk-test", "deepseek-chat", "https://api.deepseek.com"
    )
    assert s.AI_HOSTED_JSON_MODE == "json_object"
    assert s.AI_HOSTED_EXTRA_BODY == {"thinking": {"type": "disabled"}}


def test_explicit_hosted_settings_win_over_deepseek():
    s = Settings(_env_file=None, DEEPSEEK_API_KEY="sk-old", AI_HOSTED_API_KEY="sk-new",
                 AI_HOSTED_BASE_URL="https://api.openai.com/v1")
    assert (s.AI_HOSTED_API_KEY, s.AI_HOSTED_BASE_URL, s.AI_HOSTED_JSON_MODE) == (
        "sk-new", "https://api.openai.com/v1", "json_schema"
    )


# ── Hosted provider endpoints ─────────────────────────────────────────────────

async def test_photos_can_go_to_a_separate_vision_endpoint(monkeypatch):
    import json as _json

    import httpx

    from app.core.config import settings
    from app.modules.ai import providers

    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = _json.loads(request.content)
        sent.append({"url": str(request.url), "auth": request.headers["Authorization"], "body": body})
        return httpx.Response(200, json={
            "model": body["model"], "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0},
            "choices": [{"message": {"content": '{"questions": []}'}}],
        })

    real_client = httpx.AsyncClient
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    for key, value in {
        "AI_HOSTED_BASE_URL": "https://text.example/v1", "AI_HOSTED_API_KEY": "sk-text",
        "AI_HOSTED_TEXT_MODEL": "cheap-text", "AI_HOSTED_VISION_MODEL": "cheap-vision",
        "AI_HOSTED_JSON_MODE": "json_object", "AI_HOSTED_EXTRA_BODY": {"thinking": {"type": "disabled"}},
        "AI_HOSTED_INPUT_USD_PER_MTOK": 0.25,
        "AI_HOSTED_VISION_BASE_URL": "https://vision.example/v1", "AI_HOSTED_VISION_API_KEY": "sk-vision",
        "AI_HOSTED_VISION_JSON_MODE": "json_schema", "AI_HOSTED_VISION_INPUT_USD_PER_MTOK": 0.1,
    }.items():
        monkeypatch.setattr(settings, key, value)

    backend = providers.OpenAICompatibleBackend()
    photo = await backend.complete_json(prompt="read", schema={"type": "object"}, images=[b"jpg"],
                                        temperature=0, seed=None)
    text = await backend.complete_json(prompt="split", schema={"type": "object"}, images=None,
                                       temperature=0, seed=None)

    vision_call, text_call = sent
    assert vision_call["url"] == "https://vision.example/v1/chat/completions"
    assert vision_call["auth"] == "Bearer sk-vision"
    assert "thinking" not in vision_call["body"]  # DeepSeek options stay with DeepSeek
    assert vision_call["body"]["response_format"]["type"] == "json_schema"
    assert text_call["url"] == "https://text.example/v1/chat/completions"
    assert text_call["auth"] == "Bearer sk-text"
    assert text_call["body"]["thinking"] == {"type": "disabled"}
    assert text_call["body"]["response_format"] == {"type": "json_object"}
    assert (photo.cost_usd, text.cost_usd) == (0.1, 0.25)


def test_blank_vision_prices_in_an_env_file_mean_unset():
    s = Settings(_env_file=None, AI_HOSTED_VISION_INPUT_USD_PER_MTOK="", AI_HOSTED_VISION_OUTPUT_USD_PER_MTOK=" ")
    assert (s.AI_HOSTED_VISION_INPUT_USD_PER_MTOK, s.AI_HOSTED_VISION_OUTPUT_USD_PER_MTOK) == (None, None)
