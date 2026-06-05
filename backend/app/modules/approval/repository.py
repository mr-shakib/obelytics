from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.approval.models import ReviewComment


class ReviewCommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, obj: ReviewComment) -> ReviewComment:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def list_for_entity(
        self, org_id: UUID, entity_type: str, entity_id: UUID
    ) -> list[ReviewComment]:
        result = await self._session.execute(
            select(ReviewComment)
            .where(
                and_(
                    ReviewComment.organization_id == org_id,
                    ReviewComment.entity_type == entity_type,
                    ReviewComment.entity_id == entity_id,
                )
            )
            .order_by(ReviewComment.created_at)
        )
        return list(result.scalars().all())
