from datetime import datetime

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_conversation_and_message_lifecycle(
    client: AsyncClient, auth_headers: dict[str, str]
):
    created = await client.post(
        "/api/v1/copilot/conversations",
        headers=auth_headers,
        json={"title": "Review CSE 321", "context": {"course_id": "course-321"}},
    )
    assert created.status_code == 201
    conversation = created.json()
    conversation_id = conversation["id"]
    assert conversation["title"] == "Review CSE 321"

    message = await client.post(
        f"/api/v1/copilot/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"content": "Check the Course Outcomes."},
    )
    assert message.status_code == 201
    assert message.json()["role"] == "user"

    messages = await client.get(
        f"/api/v1/copilot/conversations/{conversation_id}/messages",
        headers=auth_headers,
    )
    assert messages.status_code == 200
    assert [item["content"] for item in messages.json()] == ["Check the Course Outcomes."]

    renamed = await client.patch(
        f"/api/v1/copilot/conversations/{conversation_id}",
        headers=auth_headers,
        json={"title": "CSE 321 outcomes"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "CSE 321 outcomes"

    deleted = await client.delete(
        f"/api/v1/copilot/conversations/{conversation_id}", headers=auth_headers
    )
    assert deleted.status_code == 204

    missing = await client.get(
        f"/api/v1/copilot/conversations/{conversation_id}", headers=auth_headers
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_conversation_is_private_to_its_owner(
    client: AsyncClient,
    auth_headers: dict[str, str],
    teacher_auth_headers: dict[str, str],
):
    created = await client.post(
        "/api/v1/copilot/conversations",
        headers=auth_headers,
        json={"title": "Admin private chat"},
    )
    conversation_id = created.json()["id"]

    response = await client.get(
        f"/api/v1/copilot/conversations/{conversation_id}",
        headers=teacher_auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_user_message_precedes_assistant_when_timestamps_match(
    client: AsyncClient, auth_headers: dict[str, str], db_session
):
    from app.modules.copilot.models import CopilotMessage

    created = await client.post(
        "/api/v1/copilot/conversations",
        headers=auth_headers,
        json={"title": "Ordering test"},
    )
    conversation_id = created.json()["id"]

    user_message = await client.post(
        f"/api/v1/copilot/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"content": "My question"},
    )
    user_data = user_message.json()

    assistant = CopilotMessage(
        conversation_id=conversation_id,
        role="assistant",
        content="The answer",
        status="COMPLETE",
        created_at=datetime.fromisoformat(user_data["created_at"]),
    )
    db_session.add(assistant)
    await db_session.flush()

    messages = await client.get(
        f"/api/v1/copilot/conversations/{conversation_id}/messages",
        headers=auth_headers,
    )
    assert [message["role"] for message in messages.json()] == ["user", "assistant"]
