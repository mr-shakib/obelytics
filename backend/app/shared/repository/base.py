from typing import Generic, TypeVar, Type, Sequence
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self._session = session

    async def get_by_id(self, id: UUID) -> ModelT | None:
        result = await self._session.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[ModelT]:
        result = await self._session.execute(select(self.model))
        return result.scalars().all()

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()

    async def save(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self._session.delete(entity)
