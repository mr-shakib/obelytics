import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_permission_manifest
from app.modules.ai.gateway import AIGateway, BackendFactory, get_backend_factory
from app.modules.ai.providers import AIError
from app.modules.copilot.agent import COPILOT_PROMPT_VERSION, build_system_prompt
from app.modules.copilot.schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
)
from app.modules.copilot.service import CopilotConversationService
from app.modules.copilot.tools import build_read_only_obe_context
from app.modules.iam.models import User
from app.modules.iam.schemas import PermissionManifestResponse

router = APIRouter(prefix="/copilot", tags=["Copilot"])


def service_for(db: AsyncSession, user: User) -> CopilotConversationService:
    return CopilotConversationService(db, user.organization_id, user.id)


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    body: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await service_for(db, current_user).create_conversation(body)


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_archived: Annotated[bool, Query()] = False,
):
    return await service_for(db, current_user).list_conversations(include_archived)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await service_for(db, current_user).get_conversation(conversation_id)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    body: ConversationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await service_for(db, current_user).update_conversation(conversation_id, body)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await service_for(db, current_user).delete_conversation(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def list_messages(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await service_for(db, current_user).list_messages(conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    conversation_id: UUID,
    body: MessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await service_for(db, current_user).create_message(
        conversation_id, "user", body.content.strip()
    )


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/conversations/{conversation_id}/stream")
async def stream_message(
    conversation_id: UUID,
    body: MessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    manifest: Annotated[PermissionManifestResponse, Depends(get_permission_manifest)],
    db: Annotated[AsyncSession, Depends(get_db)],
    backend_factory: Annotated[BackendFactory, Depends(get_backend_factory)],
):
    gateway = await AIGateway.for_feature(
        db,
        feature="copilot",
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        backend_factory=backend_factory,
    )
    if not gateway.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Copilot is not available: {gateway.unavailable_reason()}.",
        )

    service = service_for(db, current_user)
    conversation = await service.get_conversation(conversation_id)
    await service.create_message(conversation_id, "user", body.content.strip())
    if conversation.title == "New conversation":
        conversation.title = body.content.strip()[:80]

    history = await service.list_messages(conversation_id)
    live_context = await build_read_only_obe_context(
        db, current_user, manifest, conversation.context
    )
    provider_messages = [
        {
            "role": "system",
            "content": build_system_prompt(current_user, manifest, live_context),
        }
    ]
    provider_messages.extend(
        {"role": message.role, "content": message.content}
        for message in history
        if message.role in {"user", "assistant"} and message.status == "COMPLETE"
    )
    assistant_message = await service.create_message(
        conversation_id,
        "assistant",
        "",
        message_status="STREAMING",
        model=gateway.model_for("chat"),
    )
    await db.commit()

    async def generate() -> AsyncIterator[str]:
        content = ""
        yield sse("message", {"id": str(assistant_message.id), "status": "STREAMING"})
        try:
            # Through the AI gateway: the user's name and email are redacted
            # before an external provider sees them, and usage is logged.
            async for token in gateway.stream_chat(
                purpose="chat",
                messages=provider_messages,
                prompt_version=COPILOT_PROMPT_VERSION,
                max_tokens=settings.COPILOT_MAX_OUTPUT_TOKENS,
                names=[current_user.full_name, current_user.email],
            ):
                content += token
                yield sse("delta", {"content": token})
            await service.update_message(
                assistant_message, content=content, message_status="COMPLETE"
            )
            gateway.record_usage(db)
            await db.commit()
            yield sse("done", {"id": str(assistant_message.id), "status": "COMPLETE"})
        except AIError as exc:
            await service.update_message(
                assistant_message, content=content, message_status="FAILED"
            )
            gateway.record_usage(db)
            await db.commit()
            yield sse("error", {"message": str(exc)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
