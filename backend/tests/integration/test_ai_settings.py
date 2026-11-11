"""AI settings and usage endpoints, and the copilot going through the gateway."""
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AICall, OrganizationAISettings
from tests.ai_fakes import FakeBackend, use_fake_ai
from tests.conftest import TEST_ORG_ID

BASE = "/api/v1/ai"


async def test_settings_show_defaults_and_can_be_changed(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    await db_session.execute(delete(OrganizationAISettings).where(
        OrganizationAISettings.organization_id == TEST_ORG_ID))
    await db_session.commit()

    resp = await client.get(f"{BASE}/settings", headers=auth_headers)
    assert resp.status_code == 200
    features = {f["feature"]: f for f in resp.json()["features"]}
    assert features["integrity"]["chosen"] is None
    assert features["integrity"]["effective"] == features["integrity"]["default"]
    providers = {p["name"]: p for p in resp.json()["providers"]}
    assert providers["local"]["external"] is False
    assert set(providers["local"]["models"]) == {"text", "vision", "chat"}

    resp = await client.put(f"{BASE}/settings", json={"copilot_provider": "local"}, headers=auth_headers)
    assert resp.status_code == 200
    features = {f["feature"]: f for f in resp.json()["features"]}
    assert (features["copilot"]["chosen"], features["copilot"]["effective"]) == ("local", "local")
    assert features["integrity"]["chosen"] is None  # untouched

    resp = await client.put(f"{BASE}/settings", json={"copilot_provider": None}, headers=auth_headers)
    features = {f["feature"]: f for f in resp.json()["features"]}
    assert features["copilot"]["chosen"] is None


async def test_unknown_provider_is_rejected(client: AsyncClient, auth_headers: dict):
    resp = await client.put(f"{BASE}/settings", json={"integrity_provider": "openai"}, headers=auth_headers)
    assert resp.status_code == 422


async def test_teachers_cannot_change_ai_settings(client: AsyncClient, teacher_auth_headers: dict):
    assert (await client.get(f"{BASE}/settings", headers=teacher_auth_headers)).status_code == 403
    assert (await client.put(f"{BASE}/settings", json={"integrity_provider": "off"},
                             headers=teacher_auth_headers)).status_code == 403
    assert (await client.get(f"{BASE}/usage", headers=teacher_auth_headers)).status_code == 403


async def test_usage_is_summed_per_feature_and_model(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    await db_session.execute(delete(AICall).where(AICall.organization_id == TEST_ORG_ID))
    db_session.add_all([
        AICall(organization_id=TEST_ORG_ID, feature="integrity", purpose="audit_question",
               provider="hosted", model="m1", status="OK", input_tokens=100, output_tokens=10,
               latency_ms=200, cost_usd=0.001, redactions=1),
        AICall(organization_id=TEST_ORG_ID, feature="integrity", purpose="audit_question",
               provider="hosted", model="m1", status="ERROR", error="x", latency_ms=400, cost_usd=0),
        AICall(organization_id=TEST_ORG_ID, feature="copilot", purpose="chat", provider="local",
               model="m2", status="OK", input_tokens=50, output_tokens=5, latency_ms=100, cost_usd=0),
    ])
    await db_session.commit()

    body = (await client.get(f"{BASE}/usage", params={"days": 7}, headers=auth_headers)).json()
    assert (body["calls"], body["errors"], body["input_tokens"], body["redactions"]) == (3, 1, 150, 1)
    assert body["cost_usd"] == 0.001
    rows = {(r["feature"], r["model"]): r for r in body["rows"]}
    assert rows[("integrity", "m1")]["calls"] == 2
    assert rows[("integrity", "m1")]["avg_latency_ms"] == 300


async def test_copilot_streams_through_the_gateway(
    client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    backend = use_fake_ai(FakeBackend(external=True))
    conversation = (await client.post("/api/v1/copilot/conversations", json={"title": "New conversation"},
                                      headers=auth_headers)).json()
    resp = await client.post(f"/api/v1/copilot/conversations/{conversation['id']}/stream",
                             json={"content": "What is a CO?"}, headers=auth_headers)
    assert resp.status_code == 200
    assert '"content": "Hel"' in resp.text and "event: done" in resp.text
    # The system prompt names the user; an external provider gets it redacted.
    system = backend.messages[0]["content"]
    assert "User: [PERSON]" in system or "User: [EMAIL]" in system
    call = (await db_session.execute(select(AICall).where(
        AICall.feature == "copilot", AICall.organization_id == TEST_ORG_ID,
    ).order_by(AICall.created_at.desc()).limit(1))).scalar_one()
    assert (call.model, call.status, call.output_tokens, call.prompt_version) == ("fake-chat", "OK", 2, "copilot-v1")
    assert call.redactions >= 1
