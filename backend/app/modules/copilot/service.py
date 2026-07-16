from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.copilot.models import CopilotConversation, CopilotMessage
from app.modules.copilot.schemas import ConversationCreate, ConversationUpdate


class CopilotConversationService:
    def __init__(self, db: AsyncSession, organization_id: UUID, user_id: UUID):
        self.db = db
        self.organization_id = organization_id
        self.user_id = user_id

    def _owned_conversation_query(self, conversation_id: UUID):
        return select(CopilotConversation).where(
            CopilotConversation.id == conversation_id,
            CopilotConversation.organization_id == self.organization_id,
            CopilotConversation.user_id == self.user_id,
        )

    async def list_conversations(self, include_archived: bool = False):
        query = select(CopilotConversation).where(
            CopilotConversation.organization_id == self.organization_id,
            CopilotConversation.user_id == self.user_id,
        )
        if not include_archived:
            query = query.where(CopilotConversation.status == "ACTIVE")
        query = query.order_by(
            CopilotConversation.last_message_at.desc().nullslast(),
            CopilotConversation.updated_at.desc(),
        )
        return list((await self.db.scalars(query)).all())

    async def get_conversation(self, conversation_id: UUID) -> CopilotConversation:
        conversation = await self.db.scalar(self._owned_conversation_query(conversation_id))
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        return conversation

    async def create_conversation(self, body: ConversationCreate) -> CopilotConversation:
        conversation = CopilotConversation(
            organization_id=self.organization_id,
            user_id=self.user_id,
            title=body.title.strip(),
            context=body.context,
        )
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def update_conversation(
        self, conversation_id: UUID, body: ConversationUpdate
    ) -> CopilotConversation:
        conversation = await self.get_conversation(conversation_id)
        values = body.model_dump(exclude_unset=True)
        if "title" in values:
            values["title"] = values["title"].strip()
        for key, value in values.items():
            setattr(conversation, key, value)
        conversation.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def delete_conversation(self, conversation_id: UUID) -> None:
        await self.get_conversation(conversation_id)
        await self.db.execute(
            delete(CopilotConversation).where(CopilotConversation.id == conversation_id)
        )

    async def list_messages(self, conversation_id: UUID):
        await self.get_conversation(conversation_id)
        query = (
            select(CopilotMessage)
            .where(CopilotMessage.conversation_id == conversation_id)
            .order_by(CopilotMessage.created_at.asc(), CopilotMessage.id.asc())
        )
        return list((await self.db.scalars(query)).all())

    async def create_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        *,
        message_status: str = "COMPLETE",
        model: str | None = None,
    ) -> CopilotMessage:
        conversation = await self.get_conversation(conversation_id)
        message = CopilotMessage(
            conversation_id=conversation.id,
            role=role,
            content=content,
            status=message_status,
            model=model,
        )
        now = datetime.now(timezone.utc)
        conversation.last_message_at = now
        conversation.updated_at = now
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def update_message(
        self,
        message: CopilotMessage,
        *,
        content: str,
        message_status: str,
    ) -> CopilotMessage:
        message.content = content
        message.status = message_status
        await self.db.flush()
        return message
